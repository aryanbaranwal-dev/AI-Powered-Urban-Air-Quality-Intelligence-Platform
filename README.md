# AI-Powered Urban Air Quality Intelligence Platform

## What this is
A multi-agent AI system for smart-city air quality intervention, built on real CPCB
(Central Pollution Control Board) air quality data for Delhi and Mumbai.

## The 6 chained agents
1. **Data pipeline** (`src/01_clean_data.py`) - cleans real CPCB data
2. **Forecasting Agent** (`src/02_forecast_model.py`) - 1-3 day AQI forecast, beats naive baseline
3. **Source Attribution Agent** (`src/03_source_attribution.py`) - chemistry-based pollution source scoring
4. **Enforcement Agent** (`src/04_enforcement_agent.py`) - ranked, evidence-backed action list
5. **Citizen Advisory Agent** (`src/05_citizen_advisory.py`) - multilingual health alerts (Hindi/Marathi), 3 channels
6. **Dashboard** (`app/`) - modern glassmorphic AI-SaaS Streamlit UI tying everything together

## Multi-agent architecture (`agents/`)
The pollution-intelligence logic is also packaged as **5 independent, structured-JSON agents**
plus a Coordinator that orchestrates them — separate from the original `src/0X_*.py` offline
pipeline scripts, so any single agent can be swapped, retrained or deployed standalone:
```
agents/
  base_agent.py         # shared AgentMessage JSON envelope every agent speaks
  aqi_utils.py           # pure-python (no Streamlit) AQI band helper
  forecast_agent.py      # 24h/48h/72h AQI + Explainable AI (SHAP-like) per prediction
  attribution_agent.py   # Traffic / Industry / Dust / Biomass Burning / Construction, with confidence
  enforcement_agent.py   # ranked inspection priorities
  advisory_agent.py      # multilingual (EN/HI/MR) health advisories, generated live for any AQI band
  decision_agent.py      # merges all of the above into one intervention report
  coordinator.py         # Coordinator.run_all(city) -> merged JSON from all 5 agents
```
Every prediction from the Forecast Agent includes: `prediction`, `confidence_score`, `top_factors`
(signed, ranked feature contributions), `reason`, `expected_trend`, `recommended_intervention` — 
rendered as glass "Explainable AI" cards on both the **AQI Forecast** page and the new
**Multi-Agent AI Console** page (`app/sections/ai_agents.py`), which also shows each agent's raw
JSON message and the Decision Agent's final report.

Quick standalone test (no Streamlit needed):
```bash
python -c "
from agents.coordinator import Coordinator
# see agents/coordinator.py docstring for the run_all() signature
"
```

## Dashboard architecture (`app/`)
The dashboard was redesigned as a modular, production-ready Streamlit app:
```
main.py                    # entry point — run this with `streamlit run main.py`
app/
  config.py                # nav items, AQI color bands, source colors
  theme.py                 # global CSS (dark glassmorphism) + shared Plotly dark template
  data_loader.py           # cached data/model loading + feature engineering
  components/              # navbar, sidebar, metric cards, charts, alerts, live clock
  sections/                # one file per page: overview, forecast, attribution,
                            # enforcement, advisory, geospatial, multi_city, settings
```
The original single-file `src/dashboard.py` is kept for reference but is superseded by `app/`.

## How to run locally
```bash
pip install -r requirements.txt
python src/01_clean_data.py
python src/02_forecast_model.py
python src/03_source_attribution.py
python src/06_add_geo.py
python src/04_enforcement_agent.py
python src/05_citizen_advisory.py
streamlit run main.py
```
Then open the URL it prints (usually http://localhost:8501).

## How to deploy for free (so you have a live link for your submission)
1. Push this folder to a public GitHub repo
2. Go to https://share.streamlit.io/ and sign in with GitHub
3. Click "New app" → select your repo → set main file path to `main.py`
4. Deploy - you'll get a public URL like `yourapp.streamlit.app`

## Important documented limitations (for judges)
- Ward/zone-level breakdown is a **simulated layer** (real ward-level sensor data isn't public);
  city-level source attribution is chemistry-derived from real pollutant readings.
- Forecast is **city-level**, applied uniformly across wards (true 1km-grid forecasting needs
  gridded meteorological/traffic data not available in this dataset).
- Citizen advisory translations are **hand-written**, not machine-translated, since mistranslated
  health guidance carries real risk.
- Data covers 2015-2020 (Delhi) / 2018-2020 (Mumbai) - the most recent public CPCB dataset available.

## Data source
Real Air Quality Data in India (CPCB), via Kaggle: rohanrao/air-quality-data-in-india
