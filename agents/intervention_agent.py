"""
Agent 6 — Intervention Simulator Agent
=======================================
Lets an administrator pick one or more policy interventions (diesel
truck ban, odd-even, construction shutdown, ...) and get a projected
before/after AQI, expected reduction, an illustrative health-benefit
read, an indicative cost, and a composite effectiveness score.

Modeling approach (transparent, not a black box)
-------------------------------------------------
1. Each intervention has a documented "affects" map: which of the 5
   source-attribution categories it suppresses, and by what fraction.
   These fractions are informed, order-of-magnitude estimates from
   published Indian air-quality intervention studies (e.g. odd-even
   scheme evaluations, CPCB construction dust-control guidance) — they
   are illustrative, not measured outcomes, and are labeled as such
   everywhere they're shown.
2. Multiple simultaneous interventions combine multiplicatively per
   source (not additively), so stacking two partial fixes for the same
   source can't imply more than 100% of that source is removed.
3. AQI is assumed roughly proportional to total remaining pollution
   load — i.e. if the attributed sources' shares shrink by X% in
   aggregate, AQI shrinks by ~X% off its distance above a clean-air
   floor (AQI 15, roughly CPCB's "Good" floor), not off zero. This
   avoids the unrealistic implication that pollution could be forced
   to literal zero.
4. Health benefit and cost are both simplified, clearly-labeled
   indices for administrator decision support — not epidemiological or
   procurement-grade figures.
"""
from __future__ import annotations

from typing import Dict, List

from agents.base_agent import BaseAgent, AgentMessage

CLEAN_AIR_FLOOR_AQI = 15.0

# affects: {source_category: fractional reduction applied to that
# source's share when this intervention is active}
INTERVENTION_CATALOG: Dict[str, dict] = {
    "Ban Diesel Trucks": {
        "icon": "🚛",
        "affects": {"Traffic": 0.35},
        "cost_tier": "Medium",
        "cost_inr_per_day": (200_000, 500_000),
        "lead_time_days": 2,
        "description": "Restricts diesel freight trucks from city limits during peak pollution hours.",
    },
    "Close Construction Sites": {
        "icon": "🏗️",
        "affects": {"Construction/Dust": 0.55},
        "cost_tier": "High",
        "cost_inr_per_day": (800_000, 2_000_000),
        "lead_time_days": 1,
        "description": "Halts active construction and demolition work city-wide or in flagged wards.",
    },
    "Increase Water Sprinkling": {
        "icon": "💧",
        "affects": {"Construction/Dust": 0.20},
        "cost_tier": "Low",
        "cost_inr_per_day": (50_000, 150_000),
        "lead_time_days": 0,
        "description": "Anti-smog gun / water tanker deployment on arterial roads and dust hotspots.",
    },
    "Traffic Diversion": {
        "icon": "🚦",
        "affects": {"Traffic": 0.18},
        "cost_tier": "Low",
        "cost_inr_per_day": (100_000, 250_000),
        "lead_time_days": 1,
        "description": "Reroutes through-traffic away from the most congested/polluted corridors.",
    },
    "Odd Even": {
        "icon": "🔢",
        "affects": {"Traffic": 0.22},
        "cost_tier": "Low",
        "cost_inr_per_day": (150_000, 300_000),
        "lead_time_days": 3,
        "description": "Odd/even license-plate vehicle rationing scheme (Delhi 2016/2017 model).",
    },
    "Industrial Shutdown": {
        "icon": "🏭",
        "affects": {"Industrial": 0.60},
        "cost_tier": "High",
        "cost_inr_per_day": (1_500_000, 4_000_000),
        "lead_time_days": 2,
        "description": "Temporary closure of non-essential polluting industrial units.",
    },
    "Burning Ban": {
        "icon": "🔥",
        "affects": {"Crop/Biomass Burning": 0.45},
        "cost_tier": "Medium",
        "cost_inr_per_day": (300_000, 700_000),
        "lead_time_days": 5,
        "description": "Enforcement + subsidy push against crop residue / open biomass burning.",
    },
}

COST_TIER_WEIGHT = {"Low": 1.0, "Medium": 1.6, "High": 2.4}


class InterventionAgent(BaseAgent):
    name = "intervention_simulator_agent"

    def catalog(self) -> Dict[str, dict]:
        return INTERVENTION_CATALOG

    def simulate(
        self,
        city: str,
        current_aqi: float,
        contributions_pct: Dict[str, float],
        selected_interventions: List[str],
        ward_type: str | None = None,
    ) -> AgentMessage:
        try:
            if not selected_interventions:
                return self._error(city, "no interventions selected")

            unknown = [i for i in selected_interventions if i not in INTERVENTION_CATALOG]
            if unknown:
                return self._error(city, f"unknown intervention(s): {unknown}")

            # 1. Combine per-source suppression multiplicatively.
            remaining_fraction = {src: 1.0 for src in contributions_pct}
            per_intervention_effect = {}
            for name in selected_interventions:
                spec = INTERVENTION_CATALOG[name]
                affected_here = {}
                for src, cut in spec["affects"].items():
                    if src in remaining_fraction:
                        remaining_fraction[src] *= (1 - cut)
                        affected_here[src] = f"-{cut*100:.0f}%"
                per_intervention_effect[name] = affected_here

            new_contributions = {
                src: round(val * remaining_fraction[src], 1) for src, val in contributions_pct.items()
            }

            old_total = sum(contributions_pct.values()) or 1.0
            new_total = sum(new_contributions.values())
            load_reduction_fraction = max(0.0, 1 - (new_total / old_total))

            # 2. Map fractional load reduction onto AQI, relative to a
            # clean-air floor rather than zero.
            reducible_range = max(current_aqi - CLEAN_AIR_FLOOR_AQI, 0.0)
            aqi_after = current_aqi - reducible_range * load_reduction_fraction
            aqi_after = round(max(aqi_after, CLEAN_AIR_FLOOR_AQI), 1)
            expected_reduction_pts = round(current_aqi - aqi_after, 1)
            expected_reduction_pct = round((expected_reduction_pts / current_aqi) * 100, 1) if current_aqi else 0.0

            # 3. Illustrative health benefit: scales with AQI points
            # avoided; residential/traffic-hub wards get a slightly
            # higher weight since they're typically more densely
            # populated / exposure-sensitive than industrial buffer zones.
            ward_weight = {"residential": 1.15, "traffic_hub": 1.10, "mixed": 1.0,
                           "industrial": 0.9, "construction": 0.95, "green_belt": 0.85}.get(ward_type, 1.0)
            health_benefit_index = round(min(100.0, expected_reduction_pct * 1.4 * ward_weight), 1)
            if health_benefit_index >= 60:
                health_band = "High"
            elif health_benefit_index >= 30:
                health_band = "Moderate"
            else:
                health_band = "Low"

            # 4. Cost: sum indicative daily cost ranges across selected
            # interventions; tier = the single highest tier among them.
            lo = sum(INTERVENTION_CATALOG[n]["cost_inr_per_day"][0] for n in selected_interventions)
            hi = sum(INTERVENTION_CATALOG[n]["cost_inr_per_day"][1] for n in selected_interventions)
            worst_tier = max((INTERVENTION_CATALOG[n]["cost_tier"] for n in selected_interventions),
                              key=lambda t: COST_TIER_WEIGHT[t])
            max_lead_time = max(INTERVENTION_CATALOG[n]["lead_time_days"] for n in selected_interventions)

            # 5. Composite effectiveness: reduction & health benefit per
            # unit of cost-tier weight, scaled 0-100. Divisor chosen so a
            # strong single cheap intervention lands ~70-85, not pinned
            # at the ceiling, leaving room for genuinely best-in-class combos.
            cost_weight = sum(COST_TIER_WEIGHT[INTERVENTION_CATALOG[n]["cost_tier"]] for n in selected_interventions)
            raw_score = (expected_reduction_pct * 0.6 + health_benefit_index * 0.4) / max(cost_weight, 1.0)
            effectiveness_score = round(min(100.0, raw_score * 6.5), 1)

            return self._ok(city, {
                "selected_interventions": selected_interventions,
                "per_intervention_effect": per_intervention_effect,
                "aqi_before": round(current_aqi, 1),
                "aqi_after": aqi_after,
                "expected_reduction_points": expected_reduction_pts,
                "expected_reduction_pct": expected_reduction_pct,
                "contributions_before": {k: round(v, 1) for k, v in contributions_pct.items()},
                "contributions_after": new_contributions,
                "estimated_health_benefit_index": health_benefit_index,
                "estimated_health_benefit_band": health_band,
                "estimated_cost_inr_per_day_range": [int(lo), int(hi)],
                "estimated_cost_tier": worst_tier,
                "estimated_lead_time_days": max_lead_time,
                "estimated_effectiveness_score": effectiveness_score,
                "method": "AQI impact modeled as load-reduction fraction (multiplicative per-source suppression) "
                          "applied against the AQI range above a clean-air floor. Health/cost/effectiveness are "
                          "illustrative decision-support indices, not measured or procurement-grade figures.",
            })
        except Exception as exc:
            return self._error(city, str(exc))
