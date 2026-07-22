"""
Explainable-AI card: renders one prediction with its full explanation
(confidence, top contributing factors, reason, expected trend, and the
recommended intervention) as a single glass card — the visual language
used everywhere else in the app.
"""
import streamlit as st

from app.theme import get_aqi_meta, get_status_text_color, get_theme


def _confidence_color(conf: float) -> str:
    if conf >= 0.8:
        return get_status_text_color("good")
    if conf >= 0.6:
        return get_status_text_color("warn")
    return get_status_text_color("bad")


def xai_forecast_card(horizon_label: str, prediction: dict, delay: float = 0.0):
    """prediction: one item from ForecastAgent payload['predictions']"""
    aqi = prediction["prediction_aqi"]
    conf = prediction["confidence_score"]
    meta = get_aqi_meta(aqi)
    conf_color = _confidence_color(conf)
    t = get_theme()
    # Dots sit on a tinted swatch background so the vivid brand hue stays
    # fine at AA there; the adjacent text sits directly on the card
    # surface, so it needs the theme-adjusted AA-safe variant instead.
    up_dot, down_dot = t["danger"], t["success"]
    up_text, down_text = get_status_text_color("bad"), get_status_text_color("good")

    factor_rows = "".join(
        f"""
        <div class="xai-factor-row">
          <span class="xai-factor-dot" style="background:{up_dot if f['impact_score']>0 else down_dot};"></span>
          <span class="xai-factor-name">{f['feature']}</span>
          <span class="xai-factor-impact" style="color:{up_text if f['impact_score']>0 else down_text};">
            {'+' if f['impact_score']>0 else ''}{f['impact_score']:.2f}
          </span>
        </div>"""
        for f in prediction["top_factors"]
    )

    reason_items = "".join(f"<li>{r}</li>" for r in prediction["reason"])

    st.markdown(
        f"""
        <div class="xai-card" style="animation-delay:{delay}s;">
          <div class="xai-card-head">
            <div>
              <div class="xai-card-label">AQI · {horizon_label}</div>
              <div class="xai-card-value" style="color:{meta['color']};">{aqi:.0f}</div>
              <div class="xai-card-band" style="color:{meta['color']};">{meta['label']}</div>
            </div>
            <div class="xai-conf-ring" style="border-color:{conf_color};">
              <div class="xai-conf-pct" style="color:{conf_color};">{conf*100:.0f}%</div>
              <div class="xai-conf-label">Confidence</div>
            </div>
          </div>

          <div class="xai-section-label">Top Factors (SHAP-like attribution)</div>
          <div class="xai-factors">{factor_rows}</div>

          <div class="xai-section-label">Reason</div>
          <ul class="xai-reason-list">{reason_items}</ul>

          <div class="xai-trend-row">
            <span class="xai-trend-label">Expected Trend</span>
            <span class="xai-trend-value">{prediction['expected_trend']}</span>
          </div>

          <div class="xai-intervention">
            <b>🎯 Recommended Intervention</b><br/>{prediction['recommended_intervention']}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def health_advisory_card(payload: dict, lang: str, delay: float = 0.0):
    """Colorful personalized health card for the Personal Advisory Agent:
    risk score ring + the 5 requested recommendation fields, in the
    chosen language."""
    band = payload["risk_band"]
    color = payload["risk_band_color"]
    icon = payload["risk_band_icon"]
    reco = payload["recommendations"].get(lang, payload["recommendations"]["English"])

    factor_chips = "".join(
        f"<span class='badge' style='background:{color}1c; color:{color}; border:1px solid {color}55; "
        f"margin-right:6px; margin-bottom:6px;'>⚠️ {f['label'].get(lang, f['label']['English'])}</span>"
        for f in payload["risk_factors"]
    )

    rows = [
        ("🏥", "Health Alert", reco["health_alert"]),
        ("🚶", "Outdoor Recommendation", reco["outdoor_recommendation"]),
        ("😷", "Mask Recommendation", reco["mask_recommendation"]),
        ("🏃", "Exercise Recommendation", reco["exercise_recommendation"]),
        ("💊", "Medicine Reminder", reco["medicine_reminder"]),
        ("🚑", "Hospital Recommendation", reco["hospital_recommendation"]),
    ]
    row_html = "".join(
        f"""
        <div class="xai-factor-row" style="align-items:flex-start; gap:10px;">
          <span style="font-size:16px;">{ic}</span>
          <div style="flex:1;">
            <div style="font-size:10.5px; font-weight:700; color:var(--text-3); text-transform:uppercase; letter-spacing:.03em;">{label}</div>
            <div style="font-size:13px; color:var(--text-1); line-height:1.5; margin-top:2px;">{text}</div>
          </div>
        </div>"""
        for ic, label, text in rows
    )

    st.markdown(
        f"""
        <div class="xai-card" style="animation-delay:{delay}s; border-color:{color}44; box-shadow:0 6px 24px {color}1a;">
          <div class="xai-card-head">
            <div>
              <div class="xai-card-label">Risk Band</div>
              <div class="xai-card-value" style="color:{color};">{icon} {band}</div>
              <div class="xai-card-band" style="color:{color};">AQI {payload['forecast_aqi']:.0f} · {payload['aqi_band']}</div>
            </div>
            <div class="xai-conf-ring" style="border-color:{color};">
              <div class="xai-conf-pct" style="color:{color};">{payload['risk_score']:.0f}</div>
              <div class="xai-conf-label">Risk Score</div>
            </div>
          </div>
          {f"<div style='margin:4px 0 10px 0;'>{factor_chips}</div>" if factor_chips else ""}
          <div class="xai-factors" style="gap:9px;">{row_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def xai_attribution_card(explanation: dict, delay: float = 0.0):
    """Renders one ward's explainable source-attribution result:
    dominant source + overall confidence, the geospatial evidence that
    grounds it, and a plain-language reason per source category.

    `explanation`: the payload dict returned by
    AttributionAgent.explain_ward(...).payload
    """
    from app.theme import get_source_color, get_source_icon

    dominant = explanation["dominant_source"]
    contributions = explanation["contributions_pct"]
    confidence = explanation["confidence_by_source"]
    evidence = explanation["evidence"]
    reasoning = explanation["reasoning"]

    dom_conf = confidence.get(dominant, 0.5)
    conf_color = _confidence_color(dom_conf)
    dom_color = get_source_color(dominant)

    evidence_rows = "".join(
        f"""
        <div class="xai-factor-row">
          <span class="xai-factor-dot" style="background:{dom_color};"></span>
          <span class="xai-factor-name">{k}</span>
          <span class="xai-factor-impact" style="color:var(--text-1);">{v}</span>
        </div>"""
        for k, v in evidence.items()
    )

    ordered_sources = sorted(contributions, key=contributions.get, reverse=True)
    reason_items = "".join(
        f"<li><b style='color:{get_source_color(s)};'>{get_source_icon(s)} {s} "
        f"({confidence.get(s, 0)*100:.0f}% conf.)</b> — {reasoning[s]}</li>"
        for s in ordered_sources if s in reasoning
    )

    st.markdown(
        f"""
        <div class="xai-card" style="animation-delay:{delay}s;">
          <div class="xai-card-head">
            <div>
              <div class="xai-card-label">{explanation['ward']} · Dominant Source</div>
              <div class="xai-card-value" style="color:{dom_color};">{get_source_icon(dominant)} {dominant}</div>
              <div class="xai-card-band" style="color:{dom_color};">{contributions[dominant]:.0f}% of pollution load</div>
            </div>
            <div class="xai-conf-ring" style="border-color:{conf_color};">
              <div class="xai-conf-pct" style="color:{conf_color};">{dom_conf*100:.0f}%</div>
              <div class="xai-conf-label">Confidence</div>
            </div>
          </div>

          <div class="xai-section-label">Evidence (geospatial + meteorological)</div>
          <div class="xai-factors">{evidence_rows}</div>

          <div class="xai-section-label">AI Reasoning — Why this split?</div>
          <ul class="xai-reason-list">{reason_items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
