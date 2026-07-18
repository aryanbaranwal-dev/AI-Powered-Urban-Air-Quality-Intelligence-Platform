# Demo Video Script & Storyboard
**Target length: 3 minutes** (standard hackathon demo length — adjust timings if your event allows more/less)

---

## Prep before recording
1. Have the Streamlit dashboard running (`streamlit run src/dashboard.py`) in your browser, full-screen
2. Have the architecture diagram image open in a second tab/window
3. Practice the click-path once before recording so there's no fumbling
4. Record screen + voiceover together (OBS Studio, or Zoom's "record yourself sharing screen" both work free)

---

## SCRIPT

### [0:00 – 0:20] Hook + Problem (Slide/visual: none needed, just talk, or show slide 2 of deck)
> "India's air quality crisis isn't just a Delhi problem — it's a national one. The Lancet estimates 1.67 million premature deaths a year from air pollution. India has over 900 monitoring stations under NCAP — but a 2024 CAG audit found only 31% of cities can actually turn that data into action. The data exists. The intelligence layer to act on it doesn't. That's what we built."

**[SHOT: Talking head or slide 2 — the 4 stat callouts]**

---

### [0:20 – 0:40] Solution Overview (Slide 3 of deck, or dashboard sidebar)
> "We built a chained multi-agent AI platform — four agents, each feeding the next — running on real CPCB air quality data for Delhi and Mumbai. Not four disconnected tools: one pipeline, from forecast, to source attribution, to enforcement action, to citizen alert."

**[SHOT: Slide 3, or dashboard opening screen with sidebar visible]**

---

### [0:40 – 1:10] Live Demo: Forecasting (Dashboard Tab 1)
> "Here's the live dashboard. This is Delhi's current AQI and pollutant readings, pulled from real historical CPCB data. Switch to the Forecast tab — this Random Forest model predicts AQI 1 to 3 days ahead, and we validated it against the simplest possible baseline: 'tomorrow will be like today.' In Mumbai, our model beats that baseline by up to 16%. In Delhi, the gain is smaller — and that's a real finding, not a weakness: Delhi's winter smog is so persistently high that even a naive guess is already accurate."

**[SHOT: Click through Tab 1 — show the forecast chart, then the RMSE comparison table]**

---

### [1:10 – 1:40] Live Demo: Source Attribution (Dashboard Tab 2)
> "Now — where is this pollution actually coming from? Our attribution agent doesn't guess. It reads real pollutant chemistry: NO2 and CO signal traffic, the PM10-to-PM2.5 ratio signals construction dust, SO2 signals industry, and a seasonal PM2.5 spike in mid-October to mid-November signals crop burning. Here's the ward-level map — click any zone to see its exact source breakdown and confidence score."

**[SHOT: Tab 2 — show the map, click a ward (e.g. Anand Vihar), show the pie chart update]**

---

### [1:40 – 2:05] Live Demo: Enforcement Intelligence (Dashboard Tab 3)
> "This feeds directly into enforcement. Here's a ranked, evidence-backed action list — priority score combines severity, source confidence, and forecast trend. Notice it also knows what's actually enforceable: industrial and construction sources get a site inspection recommendation; weather-driven photochemical pollution gets a public advisory instead, because there's no site to raid."

**[SHOT: Tab 3 — expand the #1 ranked ward, show the recommended action]**

---

### [2:05 – 2:30] Live Demo: Citizen Advisory (Dashboard Tab 4)
> "And it closes the loop with citizens. Health advisories in plain language, hand-translated into Hindi for Delhi and Marathi for Mumbai — not machine-translated, because getting health guidance wrong has real consequences. Formatted for three channels: mobile app, public display boards, and IVR phone scripts for citizens without smartphones."

**[SHOT: Tab 4 — switch language toggle from English to Hindi/Marathi live, switch channel dropdown]**

---

### [2:30 – 2:50] Multi-City + Close (Dashboard Tab 5)
> "Because the whole pipeline is city-agnostic, Delhi and Mumbai run side-by-side automatically — this comparison view is architectural, not bolted on. Adding a third city is adding one CSV file, not rebuilding the system."

**[SHOT: Tab 5 — show the comparison chart]**

---

### [2:50 – 3:00] Final Close
> "One platform. Four working agents. Real data, real validation, and an honest account of what's simulated and what's next. Thank you."

**[SHOT: Back to slide 13 — the closing slide]**

---

## Storyboard Summary Table

| Time | Visual | Key Point |
|---|---|---|
| 0:00-0:20 | Talking head / Slide 2 | The crisis, in numbers |
| 0:20-0:40 | Slide 3 / Dashboard home | 4-agent chained architecture |
| 0:40-1:10 | Dashboard Tab 1 | Forecast beats baseline, real RMSE |
| 1:10-1:40 | Dashboard Tab 2 | Chemistry-based attribution + map |
| 1:40-2:05 | Dashboard Tab 3 | Ranked enforcement action list |
| 2:05-2:30 | Dashboard Tab 4 | Multilingual, multi-channel advisory |
| 2:30-2:50 | Dashboard Tab 5 | Multi-city comparison |
| 2:50-3:00 | Slide 13 | Close |

## Tips
- Practice the click-path 2-3 times before recording so transitions feel smooth, not hesitant
- If a judge Q&A follows, have the "honest limitations" slide (12) ready to reference — proactively naming your own limitations builds more credibility than hiding them
- Keep energy up on the numbers (RMSE improvements, 1.67M deaths, 72 alert records) — specific numbers land better than vague claims
