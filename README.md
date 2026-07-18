# 🌍 AI-Powered Urban Air Quality Intelligence Platform

An AI-powered multi-agent system that analyzes urban air quality, forecasts AQI, identifies pollution sources, recommends enforcement actions, and generates multilingual health advisories using real-world CPCB air quality data.

Built for the ET AI Hackathon 2026.

---

## 🚀 Features

- 📊 AQI Forecasting (1–3 days ahead)
- 🌫️ Pollution Source Attribution
- 🚔 AI-based Enforcement Recommendations
- 🩺 Multilingual Citizen Health Advisories
- 🗺️ Interactive Streamlit Dashboard
- 📍 Ward-level visualization (simulated for demonstration)

---

# 🧠 Multi-Agent Pipeline

The project consists of six interconnected AI agents:

### 1️⃣ Data Pipeline
`src/01_clean_data.py`

- Cleans and preprocesses CPCB air quality data.
- Handles missing values and feature preparation.

---

### 2️⃣ Forecasting Agent
`src/02_forecast_model.py`

- Predicts AQI for the next 1–3 days.
- Outperforms a naive forecasting baseline.

---

### 3️⃣ Source Attribution Agent
`src/03_source_attribution.py`

- Estimates dominant pollution sources using pollutant chemistry.
- Generates explainable source contribution scores.

---

### 4️⃣ Geographic Layer
`src/06_add_geo.py`

- Adds ward-level geographic information for visualization.

---

### 5️⃣ Enforcement Agent
`src/04_enforcement_agent.py`

- Produces ranked enforcement recommendations.
- Prioritizes interventions based on forecast severity.

---

### 6️⃣ Citizen Advisory Agent
`src/05_citizen_advisory.py`

- Generates health advisories.
- Supports English, Hindi, and Marathi.
- Provides recommendations for multiple communication channels.

---

### Dashboard
`src/dashboard.py`

Interactive Streamlit dashboard integrating all agents into a single user interface.

---

# 📁 Project Structure

```
aqi_project/
│
├── data/
├── models/
├── outputs/
├── src/
│   ├── 01_clean_data.py
│   ├── 02_forecast_model.py
│   ├── 03_source_attribution.py
│   ├── 04_enforcement_agent.py
│   ├── 05_citizen_advisory.py
│   ├── 06_add_geo.py
│   └── dashboard.py
│
├── requirements.txt
└── README.md
```

---

# ⚙️ Installation

Clone the repository

```bash
git clone https://github.com/yourusername/AI-Powered-Urban-Air-Quality-Intelligence-Platform.git
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# ▶️ Run the Project

```bash
python src/01_clean_data.py
python src/02_forecast_model.py
python src/03_source_attribution.py
python src/06_add_geo.py
python src/04_enforcement_agent.py
python src/05_citizen_advisory.py
streamlit run src/dashboard.py
```

The dashboard will be available at:

```
http://localhost:8501
```

---

# ☁️ Deployment

Deploy the project for free using Streamlit Community Cloud.

1. Push the project to GitHub.
2. Sign in to Streamlit Community Cloud.
3. Create a new app.
4. Select your GitHub repository.
5. Set the main file to:

```
src/dashboard.py
```

6. Deploy and obtain a public URL.

---

# 📊 Dataset

This project uses the **Air Quality Data in India** dataset published by the Central Pollution Control Board (CPCB).

Source:

https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india

---

# ⚠️ Limitations

- Ward-level visualization is simulated because public ward-level sensor data is unavailable.
- Source attribution is estimated using pollutant chemistry rather than direct emissions inventories.
- Forecasts are generated at the city level and mapped uniformly across wards.
- Fine-grained forecasting would require high-resolution meteorological and traffic datasets.
- Health advisory translations are manually curated to reduce the risk of inaccurate medical guidance.
- Dataset coverage:
  - Delhi: 2015–2020
  - Mumbai: 2018–2020

---

# 🛠️ Technologies Used

- Python
- Pandas
- NumPy
- Scikit-learn
- XGBoost
- Streamlit
- Plotly
- GeoPandas

---

# 👨‍💻 Author

Aryan Baranwal

MCA (AI & ML), Galgotias University

---

## ⭐ If you found this project useful, consider giving it a star!
