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
6. **Dashboard** (`src/dashboard.py`) - interactive Streamlit UI tying everything together

## How to run locally
```bash
pip install -r requirements.txt
python src/01_clean_data.py
python src/02_forecast_model.py
python src/03_source_attribution.py
python src/06_add_geo.py
python src/04_enforcement_agent.py
python src/05_citizen_advisory.py
streamlit run src/dashboard.py
```
Then open the URL it prints (usually http://localhost:8501).

## How to deploy for free (so you have a live link for your submission)
1. Push this folder to a public GitHub repo
2. Go to https://share.streamlit.io/ and sign in with GitHub
3. Click "New app" → select your repo → set main file path to `src/dashboard.py`
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
