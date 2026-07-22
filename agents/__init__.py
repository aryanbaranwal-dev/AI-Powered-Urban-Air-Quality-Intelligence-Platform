"""
Multi-agent AI architecture for the AQI Intelligence Platform.

5 independent agents + 1 coordinator:
  1. ForecastAgent            — agents/forecast_agent.py
  2. AttributionAgent         — agents/attribution_agent.py
  3. EnforcementAgent         — agents/enforcement_agent.py
  4. CitizenAdvisoryAgent     — agents/advisory_agent.py
  5. DecisionAgent            — agents/decision_agent.py
  •  Coordinator              — agents/coordinator.py (merges all of the above)

Every agent communicates via the shared `AgentMessage` JSON envelope
defined in agents/base_agent.py.
"""
