"""
Coordinator Agent
==================
Orchestrates the 5 independent agents for a given city and merges their
structured JSON output into one payload the dashboard (or any other
client) can consume. This is the ONLY module that knows about all 5
agents — each agent itself stays independent and unaware of the others,
which is what makes the system modular: any agent can be replaced,
re-trained, or run as a standalone microservice without touching the rest.

    Coordinator.run_all(city) -> {
        "city": ...,
        "generated_at": ...,
        "agents": {
            "forecast_agent": {...},
            "source_attribution_agent": {...},
            "enforcement_agent": {...},
            "citizen_advisory_agent": {...},
            "decision_agent": {...},          # final merged intervention report
        }
    }
"""
from __future__ import annotations

import datetime as dt
from typing import Dict

from agents.forecast_agent import ForecastAgent
from agents.attribution_agent import AttributionAgent
from agents.enforcement_agent import EnforcementAgent
from agents.advisory_agent import CitizenAdvisoryAgent
from agents.decision_agent import DecisionAgent


class Coordinator:
    def __init__(self):
        self.forecast_agent = ForecastAgent()
        self.attribution_agent = AttributionAgent()
        self.enforcement_agent = EnforcementAgent()
        self.advisory_agent = CitizenAdvisoryAgent()
        self.decision_agent = DecisionAgent()

    def run_all(self, city: str, *, city_data, latest, models, feature_cols, build_feature_row,
                attribution_df, enforcement_df, languages=None) -> Dict:

        forecast_msg = self.forecast_agent.run(
            city=city, city_data=city_data, latest=latest, models=models,
            feature_cols=feature_cols, build_feature_row=build_feature_row,
        )
        attribution_msg = self.attribution_agent.run(city=city, attribution_df=attribution_df)
        enforcement_msg = self.enforcement_agent.run(city=city, enforcement_df=enforcement_df)

        current_aqi = forecast_msg.payload.get("current_aqi", float(latest["AQI"])) \
            if forecast_msg.status == "ok" else float(latest["AQI"])
        advisory_msg = self.advisory_agent.run(city=city, aqi=current_aqi, languages=languages)

        decision_msg = self.decision_agent.run(
            city=city, forecast_msg=forecast_msg, attribution_msg=attribution_msg,
            enforcement_msg=enforcement_msg, advisory_msg=advisory_msg,
        )

        return {
            "city": city,
            "generated_at": dt.datetime.utcnow().isoformat() + "Z",
            "agents": {
                self.forecast_agent.name: forecast_msg.to_dict(),
                self.attribution_agent.name: attribution_msg.to_dict(),
                self.enforcement_agent.name: enforcement_msg.to_dict(),
                self.advisory_agent.name: advisory_msg.to_dict(),
                self.decision_agent.name: decision_msg.to_dict(),
            },
        }
