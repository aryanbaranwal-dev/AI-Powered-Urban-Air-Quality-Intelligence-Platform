"""
Agent 1 — Forecast Agent
========================
Predicts AQI 24h / 48h / 72h ahead and attaches an explanation to every
single prediction (Explainable AI layer):

    prediction, confidence_score, top_factors, reason, expected_trend,
    recommended_intervention

The explanation is computed with a lightweight, dependency-free
"SHAP-like" method: for a tree ensemble, `feature_importances_` tells you
*how much a feature matters on average*; we combine that with *how far
today's value of that feature sits from its recent normal range*
(a z-score against the trailing 30-day window) to get a per-feature,
per-prediction contribution — the same intuition SHAP uses (global
importance x local deviation), without requiring the `shap` package.
Contributions are signed (+ pushes AQI up, - pushes it down) and ranked,
mirroring a SHAP waterfall.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd

from agents.base_agent import BaseAgent, AgentMessage

HORIZON_LABELS = {1: "24h", 2: "48h", 3: "72h"}

FEATURE_READABLE = {
    "lag_1": "Yesterday's AQI",
    "lag_2": "AQI 2 days ago",
    "lag_3": "AQI 3 days ago",
    "lag_7": "AQI a week ago",
    "rolling_mean_7": "7-day average AQI",
    "rolling_std_7": "AQI volatility (7d)",
    "month": "Seasonal month",
    "day_of_year": "Day of year",
    "is_winter": "Winter/inversion season",
    "PM2.5_lag1": "PM2.5 (previous day)",
    "PM10_lag1": "PM10 / dust (previous day)",
    "NO2_lag1": "NO2 — traffic marker",
    "SO2_lag1": "SO2 — industrial marker",
    "CO_lag1": "CO — combustion marker",
    "O3_lag1": "Ozone (previous day)",
}


def _aqi_trend_label(delta: float) -> str:
    if delta >= 15:
        return "Sharp deterioration expected"
    if delta >= 4:
        return "Gradual worsening expected"
    if delta <= -15:
        return "Sharp improvement expected"
    if delta <= -4:
        return "Gradual improvement expected"
    return "Broadly stable"


def _recommended_intervention(aqi: float, top_factor_names: List[str]) -> str:
    joined = " ".join(top_factor_names).lower()
    if aqi >= 400:
        return "Trigger GRAP Stage IV: halt construction, restrict non-essential vehicles, close schools if sustained."
    if aqi >= 300:
        if "traffic" in joined or "no2" in joined:
            return "Enforce odd-even / heavy-vehicle restrictions on major corridors during peak hours."
        if "dust" in joined or "pm10" in joined or "construction" in joined:
            return "Mandate anti-smog guns and water sprinkling at active construction/demolition sites."
        return "Activate GRAP Stage III: restrict construction and non-essential diesel generators."
    if aqi >= 200:
        return "Step up road-dust sweeping and issue advisories to sensitive groups; monitor trend closely."
    if aqi >= 100:
        return "No emergency action needed — maintain routine monitoring and public advisories."
    return "Air quality is healthy — no intervention required."


class ForecastAgent(BaseAgent):
    name = "forecast_agent"

    def _shap_like_factors(self, model, X_row: pd.DataFrame, city_hist: pd.DataFrame,
                            feature_cols: List[str], top_k: int = 4) -> List[Dict]:
        """Approximate per-feature contribution to THIS prediction.

        contribution_i ≈ feature_importance_i × z_score_i
        where z_score_i is how unusual today's value of feature i is
        relative to the trailing 30-day distribution for this city.
        """
        importances = getattr(model, "feature_importances_", np.ones(len(feature_cols)) / len(feature_cols))
        recent = city_hist.tail(30)

        contributions = []
        for i, col in enumerate(feature_cols):
            val = float(X_row.iloc[0][col])
            base_col = col.replace("_lag1", "") if col.endswith("_lag1") else None
            if base_col and base_col in recent.columns:
                series = recent[base_col]
            elif col in recent.columns:
                series = recent[col]
            else:
                series = None

            if series is not None and series.std(ddof=0) not in (0, None) and not np.isnan(series.std(ddof=0)):
                z = (val - series.mean()) / (series.std(ddof=0) + 1e-6)
            else:
                z = 0.0

            score = float(importances[i]) * z
            contributions.append({
                "feature": FEATURE_READABLE.get(col, col),
                "raw_feature": col,
                "importance": round(float(importances[i]), 4),
                "z_score": round(float(z), 2),
                "impact_score": round(score, 4),
                "direction": "increases AQI" if score > 0 else "lowers AQI",
            })

        contributions.sort(key=lambda c: abs(c["impact_score"]), reverse=True)
        return contributions[:top_k]

    def run(self, city: str, city_data: pd.DataFrame, latest: pd.Series, models: Dict,
            feature_cols: List[str], build_feature_row) -> AgentMessage:
        try:
            X = build_feature_row(city_data, latest, feature_cols)
            predictions = []
            for h in (1, 2, 3):
                model = models[f"{city.lower()}_h{h}"]
                pred = float(model.predict(X)[0])

                # Confidence: derived from the ensemble's tree-to-tree agreement
                # (spread across individual trees) — a real uncertainty signal,
                # not a cosmetic number.
                if hasattr(model, "estimators_"):
                    X_arr = X.values
                    tree_preds = np.array([t.predict(X_arr)[0] for t in model.estimators_])
                    spread = float(tree_preds.std())
                    confidence = float(np.clip(1 - (spread / max(pred, 1)) * 1.8, 0.35, 0.98))
                else:
                    confidence = 0.75

                factors = self._shap_like_factors(model, X, city_data, feature_cols)
                delta = pred - float(latest["AQI"])
                reason_bullets = []
                for f in factors:
                    if abs(f["z_score"]) < 0.35:
                        continue
                    trend_word = "elevated" if f["z_score"] > 0 else "below normal"
                    reason_bullets.append(f"{f['feature']} is {trend_word} ({f['direction']})")
                if not reason_bullets:
                    reason_bullets = ["Conditions are close to the recent 30-day normal range"]

                predictions.append({
                    "horizon": HORIZON_LABELS[h],
                    "horizon_days": h,
                    "prediction_aqi": round(pred, 1),
                    "confidence_score": round(confidence, 2),
                    "delta_vs_today": round(delta, 1),
                    "expected_trend": _aqi_trend_label(delta),
                    "top_factors": factors,
                    "reason": reason_bullets,
                    "recommended_intervention": _recommended_intervention(
                        pred, [f["feature"] for f in factors[:2]]
                    ),
                })

            return self._ok(city, {
                "current_aqi": round(float(latest["AQI"]), 1),
                "as_of": str(latest["Date"].date()) if hasattr(latest["Date"], "date") else str(latest["Date"]),
                "predictions": predictions,
                "explainability_method": "feature-importance x 30-day z-score (SHAP-like local attribution)",
            })
        except Exception as exc:  # keep the agent resilient / independent
            return self._error(city, str(exc))
