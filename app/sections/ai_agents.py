"""
Multi-Agent AI Console
=======================
Runs the 5 independent agents (Forecast → Attribution → Enforcement →
Citizen Advisory → Decision) through the Coordinator and renders:
  1. the agent pipeline / data-flow diagram
  2. an Explainable-AI card per forecast horizon (24h/48h/72h)
  3. one summary card per agent + a raw structured-JSON viewer
  4. the Decision Agent's final merged intervention report
"""
import streamlit as st

from agents.coordinator import Coordinator
from app.components.metric_card import metric_card, section_title, badge
from app.components.xai_card import xai_forecast_card
from app.data_loader import build_feature_row
from app.theme import get_aqi_meta, get_severity_text_color, get_theme
from app.config import SOURCE_ICONS_5

AGENT_META = {
    "forecast_agent": {"icon": "📈", "title": "Forecast Agent", "desc": "24h / 48h / 72h AQI prediction"},
    "source_attribution_agent": {"icon": "🛰️", "title": "Source Attribution Agent", "desc": "Traffic / Industry / Dust / Biomass / Construction"},
    "enforcement_agent": {"icon": "🚨", "title": "Enforcement Agent", "desc": "Ranked inspection priorities"},
    "citizen_advisory_agent": {"icon": "🏥", "title": "Citizen Advisory Agent", "desc": "Multilingual health advisories"},
    "decision_agent": {"icon": "🧠", "title": "Decision Agent", "desc": "Final merged intervention report"},
}


@st.cache_resource(show_spinner=False)
def _get_coordinator():
    return Coordinator()


def _agent_card_header(agent_key, status):
    meta = AGENT_META[agent_key]
    if status == "ok":
        status_html = '<span class="agent-status-ok">● ok</span>'
    else:
        danger = get_theme()["danger"]
        status_html = (
            f'<span class="agent-status-ok" style="background:{danger}22;'
            f'color:{danger};border-color:{danger}4d;">● error</span>'
        )
    st.markdown(
        f"""
        <div class="agent-card-head">
          <div class="agent-card-icon">{meta['icon']}</div>
          <div>
            <div class="agent-card-title">{meta['title']}</div>
            <div class="agent-card-sub">{agent_key}.py</div>
          </div>
          {status_html}
        </div>
        <div class="card-caption" style="margin-top:-4px;margin-bottom:10px;">{meta['desc']}</div>
        """,
        unsafe_allow_html=True,
    )


def render(ctx):
    city = ctx["city"]
    clean_df = ctx["clean"]
    models = ctx["models"]
    feature_cols = ctx["feature_cols"]
    attribution_df = ctx["attribution"]
    enforcement_df = ctx["enforcement"]

    city_data = clean_df[clean_df["City"] == city].sort_values("Date")
    latest = city_data.iloc[-1]

    section_title("Multi-Agent AI Architecture", "🤖")
    st.markdown(
        "<div class='card-caption' style='margin-top:-8px;'>Five independent agents communicate through a "
        "shared structured-JSON protocol. The Coordinator Agent calls each one, then the Decision Agent "
        "synthesizes their output into a single intervention report — swap, retrain, or redeploy any single "
        "agent without touching the others.</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="agent-flow">
          <span class="agent-flow-node">📈 Forecast Agent</span><span class="agent-flow-arrow">→</span>
          <span class="agent-flow-node">🛰️ Attribution Agent</span><span class="agent-flow-arrow">→</span>
          <span class="agent-flow-node">🚨 Enforcement Agent</span><span class="agent-flow-arrow">→</span>
          <span class="agent-flow-node">🏥 Advisory Agent</span><span class="agent-flow-arrow">→</span>
          <span class="agent-flow-node" style="background:rgba(168,85,247,.14);border-color:rgba(168,85,247,.35);">🧠 Coordinator → Decision Agent</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

    if models is None or city.lower() not in {"delhi", "mumbai"}:
        st.info("Live forecasting models are only trained for Delhi and Mumbai in this prototype — "
                "the Attribution / Enforcement / Advisory / Decision agents still run for every city, "
                "but the Forecast Agent needs a supported city.")
        run_forecast = city.lower() in {"delhi", "mumbai"}
    else:
        run_forecast = True

    coordinator = _get_coordinator()
    with st.spinner("Running agent pipeline…"):
        if run_forecast:
            result = coordinator.run_all(
                city=city, city_data=city_data, latest=latest, models=models,
                feature_cols=feature_cols, build_feature_row=build_feature_row,
                attribution_df=attribution_df, enforcement_df=enforcement_df,
            )
        else:
            result = None

    if result is None:
        return

    agents = result["agents"]

    # ---------------------------------------------------- Explainable AI --
    section_title("Explainable AI — Forecast Agent", "🔍")
    fc = agents["forecast_agent"]["payload"]
    if agents["forecast_agent"]["status"] == "ok":
        cols = st.columns(3)
        for i, pred in enumerate(fc["predictions"]):
            with cols[i]:
                xai_forecast_card(pred["horizon"], pred, delay=i * 0.07)
        st.markdown(
            f"<div class='card-caption' style='margin-top:10px;'>Method: {fc['explainability_method']}. "
            "Impact scores are signed contribution estimates (feature importance × local deviation from the "
            "trailing 30-day normal) — the same intuition SHAP uses, computed without external dependencies.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.error(f"Forecast Agent error: {fc.get('error')}")

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------- Agent cards -----
    section_title("Agent Outputs (Structured JSON)", "🗂️")
    order = ["forecast_agent", "source_attribution_agent", "enforcement_agent", "citizen_advisory_agent"]
    cols = st.columns(2)
    for i, key in enumerate(order):
        with cols[i % 2]:
            with st.container(key=f"agent_card_{key}"):
                _agent_card_header(key, agents[key]["status"])

                payload = agents[key]["payload"]
                if key == "source_attribution_agent" and agents[key]["status"] == "ok":
                    for src, pct in payload["contributions_pct"].items():
                        conf = payload["confidence_by_source"][src]
                        st.markdown(
                            f"<div class='xai-factor-row' style='margin-bottom:5px;'>"
                            f"<span class='xai-factor-name'>{SOURCE_ICONS_5.get(src,'')} {src}</span>"
                            f"<span class='xai-factor-impact'>{pct}%</span>"
                            f"<span style='font-size:10.5px;color:var(--text-3);margin-left:6px;'>({conf*100:.0f}% conf)</span>"
                            f"</div>", unsafe_allow_html=True,
                        )
                    st.markdown(
                        f"<div class='card-caption'>Dominant: <b>{payload['dominant_source']}</b> · "
                        f"AQI {payload['aqi']}</div>", unsafe_allow_html=True,
                    )
                elif key == "enforcement_agent" and agents[key]["status"] == "ok":
                    for p in payload["inspection_priorities"][:5]:
                        st.markdown(
                            f"<div class='xai-factor-row' style='margin-bottom:5px;'>"
                            f"<span class='xai-factor-name'>#{p['rank']} {p['ward']}</span>"
                            f"<span class='xai-factor-impact'>AQI {p['current_aqi']:.0f}</span>"
                            f"</div>", unsafe_allow_html=True,
                        )
                    st.markdown(
                        f"<div class='card-caption'>{payload['enforceable_count']} of "
                        f"{payload['total_wards_evaluated']} wards flagged as enforceable today.</div>",
                        unsafe_allow_html=True,
                    )
                elif key == "citizen_advisory_agent" and agents[key]["status"] == "ok":
                    meta = get_aqi_meta(payload["aqi"])
                    st.markdown(
                        f"<div class='xai-card-band' style='color:{meta['color']};margin-bottom:6px;'>"
                        f"{payload['category']} · AQI {payload['aqi']}</div>", unsafe_allow_html=True,
                    )
                    for lang, msg in payload["languages"].items():
                        st.markdown(
                            f"<div class='card-caption'><b>{msg['icon']} {lang}:</b> {msg['general_public']}</div>",
                            unsafe_allow_html=True,
                        )
                elif key == "forecast_agent" and agents[key]["status"] == "ok":
                    st.markdown(
                        f"<div class='card-caption'>Current AQI: <b>{payload['current_aqi']}</b> as of {payload['as_of']}. "
                        f"See Explainable AI cards above for the full per-horizon breakdown.</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.error(payload.get("error", "unknown error"))

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------- Decision Agent --
    section_title("Decision Agent — Final Intervention Report", "🧠")
    dec = agents["decision_agent"]["payload"]
    if agents["decision_agent"]["status"] == "ok":
        sev_color = get_severity_text_color(dec["severity_level"])

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Severity Level", dec["severity_level"], icon="🚦", value_color=sev_color)
        with c2:
            metric_card("Dominant Source", dec["dominant_source"], icon="🛰️", accent="purple",
                        sub=f"{dec['dominant_source_share_pct']}% share")
        with c3:
            metric_card("Priority Wards", str(len(dec["priority_wards"])), icon="📍", accent="red")
        with c4:
            metric_card("Advisory Category", dec["citizen_advisory_category"], icon="🏥", accent="cyan")

        with st.container(key="decision_summary_card"):
            st.markdown(
                f"<div class='glass-card'><div class='section-title'><span class='bar'></span>📋 Executive Summary</div>"
                f"<div style='font-size:13.5px;line-height:1.7;color:var(--text-1);'>{dec['executive_summary']}</div>"
                f"<div class='section-title' style='margin-top:16px;'><span class='bar'></span>✅ Intervention Actions</div>"
                + "".join(f"<div class='alert-row'><span class='alert-icon'>▸</span>"
                          f"<div><div class='alert-title'>{a}</div></div></div>" for a in dec["intervention_actions"])
                + "</div>",
                unsafe_allow_html=True,
            )

    else:
        st.error(f"Decision Agent error: {dec.get('error')}")
