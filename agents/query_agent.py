"""
Agent 7 — Query Agent (AI Assistant backend)
=============================================
Answers natural-language questions about the dashboard by reading the
Coordinator's merged agent output — NOT a general-purpose LLM call.
This keeps every answer traceable to a specific agent + field, which is
what makes the "citations" in the UI meaningful rather than decorative.

Design
------
1. Classify the question into one of a fixed set of intents via keyword
   matching (cheap, deterministic, no external API/network dependency —
   this project ships with pickled sklearn models and no API keys, so a
   rule-based NLU layer is the honest choice here rather than pretending
   to call a hosted LLM).
2. Route to a small handler per intent. Each handler reads specific
   fields out of the Coordinator result (and, for "best intervention",
   runs the InterventionAgent across the catalog) and returns:
     - `answer`: the natural-language response
     - `citations`: list of {"agent", "field", "detail"} — exactly which
       agent output backs each claim in the answer
3. Unrecognized questions fall back to the Decision Agent's executive
   summary rather than a canned "I don't understand" — it's still a
   grounded, useful answer to "what's going on right now".
"""
from __future__ import annotations

import re
from typing import Dict, List

from agents.base_agent import BaseAgent, AgentMessage
from agents.intervention_agent import InterventionAgent, INTERVENTION_CATALOG

_intervention_agent = InterventionAgent()


def _cite(agent: str, field: str, detail: str) -> dict:
    return {"agent": agent, "field": field, "detail": detail}


class QueryAgent(BaseAgent):
    name = "query_agent"

    INTENTS: List[tuple] = [
        ("why_increase", re.compile(r"why.*(increas|worse|rising|gone up|higher|spik)", re.I)),
        ("best_intervention", re.compile(r"(best|top|recommend|which).*(intervention|action|fix|policy)", re.I)),
        ("most_polluted", re.compile(r"(most polluted|worst (ward|area|zone)|highest aqi|dirtiest)", re.I)),
        ("health_risk", re.compile(r"health\s*risk|is it safe|should i go outside|mask|exercise", re.I)),
        ("forecast_tomorrow", re.compile(r"forecast|tomorrow|next\s*(day|24|48|72)|predict", re.I)),
        ("explain_attribution", re.compile(r"(explain|why).*(source|attribution|pollut)", re.I)),
    ]

    def run(self, city: str, question: str, coordinator_result: Dict) -> AgentMessage:
        try:
            intent = self._classify(question)
            handler = getattr(self, f"_handle_{intent}", self._handle_fallback)
            answer, citations = handler(city, coordinator_result)
            return self._ok(city, {
                "question": question,
                "intent": intent,
                "answer": answer,
                "citations": citations,
            })
        except Exception as exc:
            return self._error(city, str(exc))

    def _classify(self, question: str) -> str:
        for intent, pattern in self.INTENTS:
            if pattern.search(question):
                return intent
        return "fallback"

    # ------------------------------------------------------------ handlers --
    def _handle_why_increase(self, city, result):
        agents = result["agents"]
        fc = agents["forecast_agent"]["payload"]
        attr = agents["source_attribution_agent"]["payload"]
        tomorrow = fc["predictions"][0]
        dominant = attr["dominant_source"]

        answer = (
            f"{city}'s AQI is currently {fc['current_aqi']:.0f} and the model expects it to move to "
            f"{tomorrow['prediction_aqi']:.0f} within {tomorrow['horizon']} ({tomorrow['expected_trend'].lower()}). "
            f"The largest driver behind this is **{dominant}**, responsible for {attr['contributions_pct'][dominant]:.0f}% "
            f"of the current pollution load at {attr['confidence_by_source'][dominant]*100:.0f}% confidence. "
            + (tomorrow["reason"][0] if tomorrow.get("reason") else "")
        )
        citations = [
            _cite("Forecast Agent", "predictions[0]", f"{tomorrow['horizon']} forecast → {tomorrow['prediction_aqi']:.0f} AQI, {tomorrow['expected_trend']}"),
            _cite("Source Attribution Agent", "dominant_source", f"{dominant} at {attr['contributions_pct'][dominant]:.0f}% share"),
        ]
        return answer, citations

    def _handle_best_intervention(self, city, result):
        agents = result["agents"]
        attr = agents["source_attribution_agent"]["payload"]
        fc = agents["forecast_agent"]["payload"]
        contributions = attr["contributions_pct"]
        # Coordinator's Attribution Agent uses 5-key naming (Traffic/Dust/
        # Industry/Biomass Burning/Construction); remap onto the
        # InterventionAgent's catalog keys before simulating.
        remap = {
            "Traffic": "Traffic",
            "Dust": "Construction/Dust",
            "Construction": "Construction/Dust",
            "Industry": "Industrial",
            "Biomass Burning": "Crop/Biomass Burning",
        }
        mapped: Dict[str, float] = {}
        for k, v in contributions.items():
            mapped[remap.get(k, k)] = mapped.get(remap.get(k, k), 0.0) + v
        for cat in ["Traffic", "Construction/Dust", "Industrial", "Crop/Biomass Burning", "Secondary/Photochemical"]:
            mapped.setdefault(cat, 0.0)

        current_aqi = fc["current_aqi"]
        best_name, best_score, best_payload = None, -1, None
        for name in INTERVENTION_CATALOG:
            msg = _intervention_agent.simulate(city, current_aqi, mapped, [name])
            if msg.status == "ok" and msg.payload["estimated_effectiveness_score"] > best_score:
                best_name, best_score, best_payload = name, msg.payload["estimated_effectiveness_score"], msg.payload

        spec = INTERVENTION_CATALOG[best_name]
        answer = (
            f"For {city}'s current source mix, **{spec['icon']} {best_name}** scores highest on the "
            f"Intervention Simulator ({best_score:.0f}/100 effectiveness): projected AQI {best_payload['aqi_before']:.0f} → "
            f"{best_payload['aqi_after']:.0f} ({best_payload['expected_reduction_pct']:.1f}% reduction), "
            f"{best_payload['estimated_cost_tier']} cost tier, {best_payload['estimated_health_benefit_band']} health benefit. "
            f"Run it in the Intervention Simulator to combine it with other actions."
        )
        citations = [
            _cite("Intervention Simulator Agent", "estimated_effectiveness_score",
                  f"{best_name} → {best_score:.0f}/100, ranked against all {len(INTERVENTION_CATALOG)} catalog options"),
            _cite("Source Attribution Agent", "contributions_pct", f"baseline source mix used for the simulation"),
        ]
        return answer, citations

    def _handle_most_polluted(self, city, result):
        agents = result["agents"]
        enf = agents["enforcement_agent"]["payload"]
        priorities = enf["inspection_priorities"]
        if not priorities:
            return f"No enforcement-flagged wards are on record for {city} right now.", []
        top = priorities[0]
        answer = (
            f"**{top['ward']}** is currently the most polluted priority area in {city}, at AQI {top['current_aqi']:.0f} "
            f"({top['trend'].lower()}), dominated by **{top['dominant_source']}** at {top['source_confidence_pct']:.0f}% "
            f"confidence. Recommended action: {top['recommended_action']}"
        )
        citations = [
            _cite("Enforcement Agent", "inspection_priorities[0]", f"{top['ward']} ranked #1 by priority score {top['priority_score']:.1f}"),
        ]
        return answer, citations

    def _handle_health_risk(self, city, result):
        agents = result["agents"]
        adv = agents["citizen_advisory_agent"]["payload"]
        en_msg = adv["languages"].get("English", next(iter(adv["languages"].values())))
        answer = (
            f"{city} is currently in the **{adv['category']}** band (AQI {adv['aqi']:.0f}). "
            f"{en_msg['general_public']}"
        )
        citations = [
            _cite("Citizen Advisory Agent", "category", f"{adv['category']} at AQI {adv['aqi']:.0f}"),
        ]
        return answer, citations

    def _handle_forecast_tomorrow(self, city, result):
        agents = result["agents"]
        fc = agents["forecast_agent"]["payload"]
        tomorrow = fc["predictions"][0]
        answer = (
            f"{city}'s AQI is forecast to be **{tomorrow['prediction_aqi']:.0f}** within {tomorrow['horizon']} "
            f"({tomorrow['expected_trend']}), at {tomorrow['confidence_score']*100:.0f}% model confidence, "
            f"up from today's {fc['current_aqi']:.0f}."
        )
        citations = [
            _cite("Forecast Agent", "predictions[0]", f"{tomorrow['horizon']} → {tomorrow['prediction_aqi']:.0f} AQI"),
        ]
        return answer, citations

    def _handle_explain_attribution(self, city, result):
        agents = result["agents"]
        attr = agents["source_attribution_agent"]["payload"]
        ordered = sorted(attr["contributions_pct"], key=attr["contributions_pct"].get, reverse=True)
        parts = [f"{s} {attr['contributions_pct'][s]:.0f}% ({attr['confidence_by_source'][s]*100:.0f}% conf.)" for s in ordered]
        answer = (
            f"{city}'s current AQI of {attr['aqi']:.0f} breaks down as: " + ", ".join(parts) + ". "
            f"Method: {attr['method']} Open the **Pollution Source Attribution** page for the per-ward "
            f"evidence (nearby roads, construction counts, industrial distance) behind these numbers."
        )
        citations = [
            _cite("Source Attribution Agent", "contributions_pct", ", ".join(parts)),
        ]
        return answer, citations

    def _handle_fallback(self, city, result):
        dec = result["agents"]["decision_agent"]["payload"]
        if "executive_summary" not in dec:
            return (
                "I can answer questions about AQI trends, dominant pollution sources, the most polluted "
                "wards, health risk, forecasts, and recommended interventions — try rephrasing your question "
                "around one of those.", [],
            )
        answer = dec["executive_summary"] + " Ask me about the forecast, source attribution, health risk, or the best intervention for more detail."
        citations = [_cite("Decision Agent", "executive_summary", "merged summary across all agents")]
        return answer, citations
