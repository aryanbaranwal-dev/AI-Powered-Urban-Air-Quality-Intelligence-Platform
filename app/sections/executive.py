"""
Executive Dashboard — Municipal Commissioner View
==================================================
A single-screen briefing built for a Commissioner, not an analyst: the
seven KPIs a decision-maker actually asks for, gauge/trend reads on
each, a live alert feed, AI-generated recommended actions, and a
compact "ask the platform" assistant grounded in the same agent
outputs used everywhere else in the app (see agents/query_agent.py for
the citation logic).

Every number here is derived from the same CSVs / models the rest of
the platform uses — nothing is invented for this page. Where a metric
has no ground-truth source in this dataset (e.g. "Inspection Success
Rate" — there is no logged outcome of past inspections), it is
computed as a clearly-labeled proxy and captioned as such rather than
presented as a measured figure.
"""
import pandas as pd
import streamlit as st

from agents.coordinator import Coordinator
from agents.query_agent import QueryAgent
from agents.intervention_agent import InterventionAgent, INTERVENTION_CATALOG
from app.components.metric_card import metric_card, section_title, badge, empty_state
from app.components.charts import kpi_gauge, aqi_trend_chart
from app.components.alerts import alert_row
from app.theme import get_aqi_meta, get_source_icon
from app.data_loader import get_forecasts, build_feature_row

SUGGESTED_QUESTIONS = [
    "Why did AQI increase?",
    "What's the best intervention right now?",
    "Which area is most polluted?",
    "What's the health risk today?",
    "What's the forecast for tomorrow?",
    "Explain the source attribution.",
]

_SOURCE_REMAP = {
    "Traffic": "Traffic",
    "Dust": "Construction/Dust",
    "Construction": "Construction/Dust",
    "Industry": "Industrial",
    "Biomass Burning": "Crop/Biomass Burning",
}


@st.cache_resource(show_spinner=False)
def _get_coordinator():
    return Coordinator()


@st.cache_resource(show_spinner=False)
def _get_query_agent():
    return QueryAgent()


@st.cache_resource(show_spinner=False)
def _get_intervention_agent():
    return InterventionAgent()


# --------------------------------------------------------------- helpers --
def _forecast_accuracy_pct(city: str, model_results: dict, city_mean_aqi: float) -> float:
    """Turn horizon RMSEs into a single 0-100 'accuracy' read: how small
    the average forecasting error is relative to the city's typical AQI.
    Not a substitute for RMSE/MAE in a model card — a briefing-friendly
    summary of it."""
    horizons = model_results.get(city, {}).get("horizons", {})
    if not horizons or not city_mean_aqi:
        return 0.0
    errs = [h["model_rmse"] for h in horizons.values()]
    avg_rmse = sum(errs) / len(errs)
    acc = 100.0 * (1.0 - (avg_rmse / city_mean_aqi))
    return max(0.0, min(100.0, acc))


def _inspection_success_rate(city_enf: pd.DataFrame) -> float:
    """Proxy metric: share of enforcement-flagged wards whose trend is
    NOT worsening. There is no logged inspection-outcome history in this
    dataset, so this is captioned as a proxy rather than a measured KPI."""
    flagged = city_enf[city_enf["Enforceable"]]
    if flagged.empty:
        return 0.0
    non_worsening = (flagged["Trend"] != "Worsening").sum()
    return 100.0 * non_worsening / len(flagged)


def _best_intervention(city: str, current_aqi: float, latest_att_row: pd.Series):
    pct_cols = [c for c in latest_att_row.index if str(c).startswith("pct_")]
    contributions = {c.replace("pct_", "").replace("_", " ").title(): latest_att_row[c] for c in pct_cols}
    mapped = {}
    for k, v in contributions.items():
        key = _SOURCE_REMAP.get(k, k)
        mapped[key] = mapped.get(key, 0.0) + v
    for cat in ["Traffic", "Construction/Dust", "Industrial", "Crop/Biomass Burning", "Secondary/Photochemical"]:
        mapped.setdefault(cat, 0.0)

    agent = _get_intervention_agent()
    best_name, best_score, best_payload = None, -1, None
    for name in INTERVENTION_CATALOG:
        msg = agent.simulate(city, current_aqi, mapped, [name])
        if msg.status == "ok" and msg.payload["estimated_effectiveness_score"] > best_score:
            best_name, best_score, best_payload = name, msg.payload["estimated_effectiveness_score"], msg.payload
    return best_name, best_score, best_payload


def _citation_chips(citations):
    if not citations:
        return ""
    chips = "".join(
        f"<span class='badge' style='background:rgba(59,130,246,0.12); color:var(--primary); "
        f"border:1px solid rgba(59,130,246,0.3); margin-right:6px; margin-top:6px;' "
        f"title=\"{c['detail']}\">📎 {c['agent']} · {c['field']}</span>"
        for c in citations
    )
    return f"<div style='margin-top:8px;'>{chips}</div>"


# ------------------------------------------------------------------ render --
def render(ctx):
    city = ctx["city"]
    clean_df = ctx["clean"]
    ward_df = ctx["ward"]
    enforcement_df = ctx["enforcement"]
    attribution_df = ctx["attribution"]
    model_results = ctx["model_results"]
    models = ctx["models"]
    feature_cols = ctx["feature_cols"]

    city_data = clean_df[clean_df["City"] == city].sort_values("Date")
    latest = city_data.iloc[-1]

    dates_sorted = sorted(ward_df["Date"].unique())
    latest_date = dates_sorted[-1]
    prev_date = dates_sorted[-2] if len(dates_sorted) > 1 else latest_date

    city_wards_now = ward_df[(ward_df["City"] == city) & (ward_df["Date"] == latest_date)]
    city_wards_prev = ward_df[(ward_df["City"] == city) & (ward_df["Date"] == prev_date)]

    if city_wards_now.empty:
        st.warning(f"No ward-level data available for {city} yet.")
        return

    avg_aqi_now = city_wards_now["Simulated_AQI"].mean()
    avg_aqi_prev = city_wards_prev["Simulated_AQI"].mean() if not city_wards_prev.empty else avg_aqi_now
    avg_delta = avg_aqi_now - avg_aqi_prev

    worst_row = city_wards_now.loc[city_wards_now["Simulated_AQI"].idxmax()]
    best_row = city_wards_now.loc[city_wards_now["Simulated_AQI"].idxmin()]

    city_enf = enforcement_df[enforcement_df["City"] == city]
    high_priority = int(city_enf["Enforceable"].sum())

    forecast_accuracy = _forecast_accuracy_pct(city, model_results, city_data["AQI"].tail(90).mean())
    inspection_success = _inspection_success_rate(city_enf)

    latest_att_row = attribution_df[attribution_df["City"] == city].sort_values("Date").iloc[-1]
    best_name, best_score, best_payload = _best_intervention(city, latest["AQI"], latest_att_row)
    intervention_impact = best_payload["expected_reduction_pct"] if best_payload else 0.0

    aqi_meta = get_aqi_meta(avg_aqi_now)

    # ================================================================ hero banner
    st.markdown(
        f"""
        <div class="exec-hero" style="--hero-accent:{aqi_meta['color']};">
          <div class="exec-hero-glow"></div>
          <div class="exec-hero-row">
            <div>
              <div class="exec-hero-eyebrow">🏛️ EXECUTIVE BRIEFING</div>
              <div class="exec-hero-title">{city} <span style="color:var(--text-3); font-weight:600;">— Air Quality Status</span></div>
              <div class="exec-hero-sub">Snapshot as of {pd.Timestamp(latest_date).strftime('%A, %d %b %Y')} · for Municipal Commissioner review</div>
            </div>
            <div class="exec-hero-readout">
              <div class="exec-hero-aqi" style="color:{aqi_meta['color']};">{avg_aqi_now:.0f}</div>
              <div>{badge(aqi_meta['label'], aqi_meta['color'], icon='🌫️')}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    # ================================================================ KPI row 1
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        metric_card("Average AQI", f"{avg_aqi_now:.0f}", icon="🌫️", accent="blue",
                    delta=f"{avg_delta:+.0f}", sub=f"{aqi_meta['label']} · citywide, all wards", value_color=aqi_meta["color"], delay=0.00,
                    trend=city_data["AQI"].tail(14).tolist())
    with k2:
        metric_card("Worst Ward", worst_row["Ward"], icon="🔴", accent="red",
                     sub=f"AQI {worst_row['Simulated_AQI']:.0f} · {worst_row['Top_Source']}", delay=0.05)
    with k3:
        metric_card("Best Ward", best_row["Ward"], icon="🟢", accent="green",
                     sub=f"AQI {best_row['Simulated_AQI']:.0f} · cleanest today", delay=0.10)
    with k4:
        metric_card("High-Priority Areas", f"{high_priority}", icon="🚨", accent="amber",
                     sub=f"of {city_wards_now['Ward'].nunique()} wards flagged for enforcement", delay=0.15)

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    # ================================================================ KPI row 2
    k5, k6, k7, k8 = st.columns(4)
    with k5:
        metric_card("Forecast Accuracy", f"{forecast_accuracy:.0f}%", icon="🧠", accent="purple",
                     sub="avg. across 1–3 day horizons", progress_pct=forecast_accuracy, delay=0.00)
    with k6:
        metric_card("Inspection Success Rate", f"{inspection_success:.0f}%", icon="✅", accent="cyan",
                     sub="flagged wards trending non-worse (proxy)", progress_pct=inspection_success, delay=0.05)
    with k7:
        metric_card("Intervention Impact", f"-{intervention_impact:.1f}%", icon="🧪", accent="green",
                     sub=f"best option: {best_name}" if best_name else "no simulation available",
                     progress_pct=intervention_impact, delay=0.10)
    with k8:
        live_alert_count = int((city_wards_now["Simulated_AQI"] > 200).sum())
        metric_card("Live Alerts", f"{live_alert_count}", icon="🔔", accent="red",
                     sub="wards currently above 'Poor' (AQI 200)", delay=0.15)

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # ================================================================ Gauges + trend
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        with st.container(key="exec_gauge_aqi"):
            st.plotly_chart(
                kpi_gauge(avg_aqi_now, "Average AQI", max_value=500,
                          bands=[(0, 100, "rgba(34,197,94,0.20)"), (100, 200, "rgba(250,204,21,0.20)"),
                                 (200, 500, "rgba(248,113,113,0.20)")],
                          height=190),
                use_container_width=True, config={"displayModeBar": False},
            )
    with g2:
        with st.container(key="exec_gauge_acc"):
            st.plotly_chart(kpi_gauge(forecast_accuracy, "Forecast Accuracy", max_value=100, suffix="%", height=190),
                             use_container_width=True, config={"displayModeBar": False})
    with g3:
        with st.container(key="exec_gauge_insp"):
            st.plotly_chart(kpi_gauge(inspection_success, "Inspection Success", max_value=100, suffix="%", height=190),
                             use_container_width=True, config={"displayModeBar": False})
    with g4:
        with st.container(key="exec_gauge_int"):
            st.plotly_chart(kpi_gauge(intervention_impact, "Intervention Impact", max_value=100, suffix="%", height=190),
                             use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        "<div class='card-caption'>Forecast Accuracy and Inspection Success Rate are model-derived / proxy "
        "indicators (see caption on each card) — they summarize existing agent outputs for a briefing view, "
        "not new ground-truth measurements.</div>",
        unsafe_allow_html=True,
    )

    # ================================================================ trend + alerts + recommendations
    tcol, acol = st.columns([1.4, 1])
    with tcol:
        with st.container(key="exec_trend_card"):
            section_title(f"{city} — AQI Trend (60 days)", "📈",
                          trailing_html=badge(f"Now: {avg_aqi_now:.0f}", aqi_meta["color"]))
            st.plotly_chart(aqi_trend_chart(city_data), use_container_width=True, config={"displayModeBar": False})

    with acol:
        with st.container(key="exec_alerts_card"):
            section_title("Live Alerts", "🔔")
            risky = city_wards_now.sort_values("Simulated_AQI", ascending=False).head(5)
            if risky.empty:
                empty_state("No active alerts", icon="✅", sub="All monitored wards are within normal range.")
            for i, (_, r) in enumerate(risky.iterrows()):
                m = get_aqi_meta(r["Simulated_AQI"])
                alert_row(
                    "🚨" if r["Simulated_AQI"] > 200 else "⚠️",
                    f"{r['Ward']} — AQI {r['Simulated_AQI']:.0f} ({m['label']})",
                    f"Dominant source: {r['Top_Source']} {get_source_icon(r['Top_Source'])}",
                    delay=i * 0.05,
                )

    rcol1, rcol2 = st.columns([1, 1])
    with rcol1:
        with st.container(key="exec_reco_card"):
            section_title("AI Recommendations", "🤖")
            if best_payload:
                alert_row(
                    "🧪",
                    f"{best_name} — {best_score:.0f}/100 effectiveness",
                    f"Projected AQI {best_payload['aqi_before']:.0f} → {best_payload['aqi_after']:.0f} "
                    f"({intervention_impact:.1f}% reduction) · {best_payload['estimated_cost_tier']} cost tier",
                )
            top_actions = city_enf.sort_values("Priority_Score", ascending=False).head(3)
            for i, (_, r) in enumerate(top_actions.iterrows()):
                alert_row("🛠️", f"{r['Ward']} — Priority {r['Priority_Score']:.0f}", r["Recommended_Action"], delay=(i + 1) * 0.05)
            st.markdown(
                "<div class='card-caption'>Ranked by the Enforcement Agent's priority score plus the "
                "Intervention Simulator's effectiveness score across the full catalog.</div>",
                unsafe_allow_html=True,
            )

    with rcol2:
        _render_assistant_panel(ctx, city, city_data, latest, models, feature_cols, attribution_df, enforcement_df)


def _render_assistant_panel(ctx, city, city_data, latest, models, feature_cols, attribution_df, enforcement_df):
    with st.container(key="exec_assistant_card"):
        section_title("Ask the Platform", "💬")
        st.markdown(
            "<div class='card-caption' style='margin-top:-6px;'>Grounded in this session's live agent outputs — "
            "answers cite the exact agent + field behind each claim.</div>",
            unsafe_allow_html=True,
        )

        if city.lower() not in {"delhi", "mumbai"}:
            st.info("The AI Assistant needs the Forecast Agent (Delhi/Mumbai only in this prototype).")
            return

        coordinator = _get_coordinator()
        with st.spinner("Refreshing agent context…"):
            result = coordinator.run_all(
                city=city, city_data=city_data, latest=latest, models=models,
                feature_cols=feature_cols, build_feature_row=build_feature_row,
                attribution_df=attribution_df, enforcement_df=enforcement_df,
            )

        history_key = f"exec_chat_history_{city}"
        if history_key not in st.session_state:
            st.session_state[history_key] = []

        sc = st.columns(2)
        for i, q in enumerate(SUGGESTED_QUESTIONS[:4]):
            if sc[i % 2].button(q, key=f"exec_suggest_{city}_{i}", use_container_width=True):
                st.session_state[f"exec_pending_question_{city}"] = q

        for turn in st.session_state[history_key][-4:]:
            with st.chat_message("user"):
                st.markdown(turn["question"])
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(turn["answer"])
                st.markdown(_citation_chips(turn["citations"]), unsafe_allow_html=True)

        pending = st.session_state.pop(f"exec_pending_question_{city}", None)
        typed = st.chat_input(f"Ask about {city}'s air quality…", key=f"exec_chat_input_{city}")
        question = pending or typed

        if question:
            with st.chat_message("user"):
                st.markdown(question)
            qa = _get_query_agent()
            msg = qa.run(city, question, result)
            with st.chat_message("assistant", avatar="🤖"):
                if msg.status == "ok":
                    answer = msg.payload["answer"]
                    citations = msg.payload["citations"]
                    st.markdown(answer)
                    st.markdown(_citation_chips(citations), unsafe_allow_html=True)
                else:
                    answer = f"Sorry, I couldn't answer that: {msg.payload.get('error')}"
                    citations = []
                    st.error(answer)
            st.session_state[history_key].append({"question": question, "answer": answer, "citations": citations})
