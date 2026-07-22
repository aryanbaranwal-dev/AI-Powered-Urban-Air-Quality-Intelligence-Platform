"""
Agent 3 — Enforcement Agent
============================
Turns hotspot + source-attribution data into a ranked, actionable
inspection priority list for ground enforcement teams.
"""
from __future__ import annotations

from typing import Dict

import pandas as pd

from agents.base_agent import BaseAgent, AgentMessage


class EnforcementAgent(BaseAgent):
    name = "enforcement_agent"

    def run(self, city: str, enforcement_df: pd.DataFrame, top_n: int = 5) -> AgentMessage:
        try:
            city_rows = enforcement_df[enforcement_df["City"] == city].sort_values("Priority_Score", ascending=False)
            if not len(city_rows):
                return self._error(city, "no enforcement data for city")

            priorities = []
            for _, r in city_rows.head(top_n).iterrows():
                priorities.append({
                    "rank": int(r["Rank"]),
                    "ward": r["Ward"],
                    "ward_type": r["Ward_Type"],
                    "current_aqi": round(float(r["Current_AQI"]), 1),
                    "forecast_tomorrow_aqi": round(float(r["Forecast_Tomorrow_AQI"]), 1),
                    "trend": r["Trend"],
                    "dominant_source": r["Dominant_Source"],
                    "source_confidence_pct": round(float(r["Source_Confidence_Pct"]), 1),
                    "enforceable": bool(r["Enforceable"]),
                    "recommended_action": r["Recommended_Action"],
                    "priority_score": round(float(r["Priority_Score"]), 1),
                })

            return self._ok(city, {
                "inspection_priorities": priorities,
                "total_wards_evaluated": int(len(city_rows)),
                "enforceable_count": int(city_rows["Enforceable"].sum()),
                "method": "Priority score = f(current + forecast AQI, worsening trend, source confidence, "
                          "enforceability of dominant source).",
            })
        except Exception as exc:
            return self._error(city, str(exc))
