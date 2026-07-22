"""
Agent 5 — Decision Agent
==========================
Consumes the structured JSON output of the Forecast, Attribution and
Enforcement agents and synthesizes a single, prioritized intervention
report — the thing an actual city control-room operator would read.
It does not talk to any data source directly; it only reasons over the
other agents' JSON, which keeps it swappable/testable in isolation.
"""
from __future__ import annotations

from typing import Dict

from agents.base_agent import BaseAgent, AgentMessage


def _severity_level(aqi: float) -> str:
    if aqi >= 400:
        return "CRITICAL"
    if aqi >= 300:
        return "SEVERE"
    if aqi >= 200:
        return "HIGH"
    if aqi >= 100:
        return "MODERATE"
    return "LOW"


class DecisionAgent(BaseAgent):
    name = "decision_agent"

    def run(self, city: str, forecast_msg: AgentMessage, attribution_msg: AgentMessage,
            enforcement_msg: AgentMessage, advisory_msg: AgentMessage) -> AgentMessage:
        try:
            if any(m.status == "error" for m in [forecast_msg, attribution_msg, enforcement_msg, advisory_msg]):
                failed = [m.agent for m in [forecast_msg, attribution_msg, enforcement_msg, advisory_msg] if m.status == "error"]
                return self._error(city, f"upstream agent(s) failed: {', '.join(failed)}")

            fc = forecast_msg.payload
            attr = attribution_msg.payload
            enf = enforcement_msg.payload
            adv = advisory_msg.payload

            current_aqi = fc["current_aqi"]
            tomorrow = fc["predictions"][0]
            severity = _severity_level(max(current_aqi, tomorrow["prediction_aqi"]))

            dominant_source = attr["dominant_source"]
            source_confidence = attr["confidence_by_source"].get(dominant_source, attr["overall_confidence"])

            top_wards = [p["ward"] for p in enf["inspection_priorities"][:3]]

            actions = []
            actions.append(tomorrow["recommended_intervention"])
            for p in enf["inspection_priorities"][:3]:
                actions.append(f"{p['ward']}: {p['recommended_action']}")
            # de-duplicate while preserving order
            seen = set()
            deduped_actions = []
            for a in actions:
                if a not in seen:
                    deduped_actions.append(a)
                    seen.add(a)

            summary = (
                f"{city} is currently at AQI {current_aqi} and trending toward "
                f"{tomorrow['prediction_aqi']} within {tomorrow['horizon']} "
                f"({tomorrow['expected_trend'].lower()}). "
                f"The dominant pollution source is {dominant_source} "
                f"({attr['contributions_pct'][dominant_source]}% share, "
                f"{source_confidence*100:.0f}% confidence). "
                f"Highest-priority wards for enforcement: {', '.join(top_wards) if top_wards else 'none flagged'}."
            )

            return self._ok(city, {
                "severity_level": severity,
                "current_aqi": current_aqi,
                "forecast_next_horizon": tomorrow,
                "dominant_source": dominant_source,
                "dominant_source_share_pct": attr["contributions_pct"][dominant_source],
                "dominant_source_confidence": source_confidence,
                "priority_wards": top_wards,
                "citizen_advisory_category": adv["category"],
                "executive_summary": summary,
                "intervention_actions": deduped_actions,
                "contributing_agents": [
                    forecast_msg.agent, attribution_msg.agent, enforcement_msg.agent, advisory_msg.agent,
                ],
            })
        except Exception as exc:
            return self._error(city, str(exc))
