# 🌍 AI-Powered Urban Air Quality Intelligence Platform

An AI-powered multi-agent system for urban air quality analysis, forecasting, pollution source attribution, enforcement recommendations, and multilingual citizen health advisories using real-world air quality data from the Central Pollution Control Board (CPCB).

Developed as part of the **ET AI Hackathon 2026**.

---

## ✨ Features

- 📈 **1–3 Day AQI Forecasting**
- 🌫️ **Pollution Source Attribution**
- 🚔 **Evidence-Based Enforcement Recommendations**
- 🩺 **Multilingual Citizen Health Advisories (English, Hindi & Marathi)**
- 🗺️ **Interactive Streamlit Dashboard**
- 📍 **Ward-Level Visualization (Simulation for Demonstration)**

---

# 🏗️ System Architecture

> *(Add your architecture diagram here after uploading it.)*

```markdown
![Architecture](docs/architecture_diagram.png)
```

---

# 🤖 Multi-Agent Pipeline

## 1️⃣ Data Pipeline
**File:** `src/01_clean_data.py`

- Cleans and preprocesses real CPCB air quality data.
- Handles missing values and prepares features for downstream agents.

---

## 2️⃣ Forecasting Agent
**File:** `src/02_forecast_model.py`

- Predicts AQI for the next **1–3 days**.
- Evaluates performance against a naïve forecasting baseline.

---

## 3️⃣ Source Attribution Agent
**File:** `src/03_source_attribution.py`

- Estimates dominant pollution sources using pollutant chemistry.
- Produces explainable source contribution scores.

---

## 4️⃣ Geographic Layer
**File:** `src/06_add_geo.py`

- Adds ward-level geographic mapping for dashboard visualization.

---

## 5️⃣ Enforcement Agent
**File:** `src/04_enforcement_agent.py`

- Generates ranked enforcement recommendations.
- Prioritizes interventions based on predicted pollution severity.

---

## 6️⃣ Citizen Advisory Agent
**File:** `src/05_citizen_advisory.py`

- Produces multilingual health advisories.
- Supports English, Hindi, and Marathi.
- Generates recommendations for multiple communication channels.

---

## 📊 Dashboard
**File:** `src/dashboard.py`

An interactive Streamlit dashboard integrating all AI agents into a single user interface for visualization and decision support.

---

# 📂 Project Structure

```text
aqi_project/
│
├── data/
├── docs/
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
├── README.md
├── LICENSE
└── requirements.txt
```

---

# ⚙️ Installation

Clone the repository

```bash
git clone https://github.com/<your-username>/AI-Powered-Urban-Air-Quality-Intelligence-Platform.git
```

Move into the project directory

```bash
cd AI-Powered-Urban-Air-Quality-Intelligence-Platform
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# ▶️ Running the Project

Execute the pipeline in the following order:

```bash
python src/01_clean_data.py
python src/02_forecast_model.py
python src/03_source_attribution.py
python src/06_add_geo.py
python src/04_enforcement_agent.py
python src/05_citizen_advisory.py
streamlit run src/dashboard.py
```

Open the dashboard in your browser:

```
http://localhost:8501
```

---

# 🚀 Deployment

You can deploy this project for free using **Streamlit Community Cloud**.

1. Push the project to GitHub.
2. Sign in to Streamlit Community Cloud.
3. Create a new application.
4. Select your repository.
5. Set the entry file as:

```text
src/dashboard.py
```

6. Deploy the application.

---

# 📊 Dataset

This project uses the **Air Quality Data in India** dataset published by the **Central Pollution Control Board (CPCB)**.

**Source:**

https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india

---

# ⚠️ Limitations

- Ward-level visualization is simulated because public ward-level sensor data is unavailable.
- Pollution source attribution is estimated from pollutant chemistry rather than direct emissions inventories.
- AQI forecasts are generated at the city level and visualized uniformly across wards.
- High-resolution forecasting would require additional meteorological, satellite, and traffic datasets.
- Citizen health advisories are manually curated to reduce the risk of inaccurate machine-translated health guidance.
- Dataset coverage:
  - **Delhi:** 2015–2020
  - **Mumbai:** 2018–2020

---

# 🛠️ Tech Stack

- Python
- Pandas
- NumPy
- Scikit-learn
- Streamlit
- Plotly
- GeoPandas
- Machine Learning

---

# 🔮 Future Improvements

- Real-time AQI monitoring using live APIs.
- Integration with weather and traffic datasets.
- Deep learning-based forecasting models.
- Mobile application for citizen advisories.
- GIS-based high-resolution pollution heatmaps.
- IoT sensor integration for ward-level monitoring.

---

# 📜 License

This project is licensed under the **Apache License 2.0**.

See the [LICENSE](LICENSE) file for details.

---

# 👨‍💻 Author

**Aryan Baranwal**

MCA (Artificial Intelligence & Machine Learning)  
Galgotias University, Greater Noida

---

⭐ If you found this project useful, consider giving it a star!