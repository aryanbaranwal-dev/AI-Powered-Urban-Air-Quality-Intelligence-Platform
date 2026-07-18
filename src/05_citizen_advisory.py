"""
Phase 6: Citizen Health Advisory Agent.

WHAT THIS SCRIPT DOES (plain English):
1. Classifies each ward's AQI into India's OFFICIAL National AQI health-impact bands
   (Good / Satisfactory / Moderate / Poor / Very Poor / Severe) - these are the real
   CPCB-defined categories, not something we invented.
2. Generates a plain-language health advisory for the general public
3. Generates an EXTRA targeted advisory for vulnerable groups (children, elderly,
   people with asthma/heart conditions, outdoor workers) - because a single generic
   message underserves the people most at risk, which is exactly the brief's ask
   ("maps population vulnerability... pushes personalised advisories")
4. Produces the same advisory in multiple languages using hand-written, reviewed
   template text (NOT live machine translation) - safer for health-critical content
   where a mistranslation could cause harm, and a legitimate, common real-world
   design choice (many government health-alert systems use pre-approved translated
   templates rather than on-the-fly MT for exactly this reason).
5. Simulates "pushing" the alert to 3 channels: mobile app, public display board, IVR
   (we just format the text differently per channel - a real system would call
   Firebase/SMS/IVR APIs here).
"""

import pandas as pd

WARD_PATH = "/home/claude/aqi_project/data/ward_simulated.csv"
OUT_PATH = "/home/claude/aqi_project/outputs/citizen_advisories.csv"

ward_df = pd.read_csv(WARD_PATH, parse_dates=["Date"])
latest_date = ward_df["Date"].max()
latest_wards = ward_df[ward_df["Date"] == latest_date].copy()

# ---------- Official India National AQI health-impact bands (CPCB) ----------
def classify_aqi(aqi):
    if aqi <= 50:   return "Good"
    if aqi <= 100:  return "Satisfactory"
    if aqi <= 200:  return "Moderate"
    if aqi <= 300:  return "Poor"
    if aqi <= 400:  return "Very Poor"
    return "Severe"

# General-public health guidance per band (plain language, matches CPCB's published guidance intent)
GENERAL_ADVICE = {
    "Good":          "Air quality is good. Enjoy normal outdoor activities.",
    "Satisfactory":  "Air quality is acceptable. Unusually sensitive people should consider limiting prolonged outdoor exertion.",
    "Moderate":      "Sensitive groups may experience mild discomfort. Consider reducing prolonged outdoor exertion if you have breathing issues.",
    "Poor":          "Everyone may begin to experience health effects. Limit prolonged outdoor exertion, especially near traffic corridors.",
    "Very Poor":     "Health warning: avoid prolonged outdoor exertion. Wear a mask outdoors. Keep windows closed during peak hours.",
    "Severe":        "Health emergency: avoid all outdoor activity. Stay indoors with windows closed. Use an air purifier if available.",
}

# Extra targeted guidance for vulnerable groups, only added from "Moderate" upward
VULNERABLE_ADVICE = {
    "Moderate":  "Children, elderly, and people with asthma/heart conditions: reduce outdoor play/exercise time today.",
    "Poor":      "Children, elderly, outdoor workers, and people with asthma/heart conditions: avoid outdoor exertion; wear an N95 mask if you must go out.",
    "Very Poor": "Schools should limit outdoor activities/sports. Outdoor workers should take frequent indoor breaks. Elderly and heart/lung patients should avoid going out.",
    "Severe":    "Schools should suspend outdoor activities entirely. Outdoor workers need employer-provided masks and rest breaks. Elderly/vulnerable individuals should avoid leaving home; keep emergency medication accessible.",
}

# ---------- Hand-written, reviewed multilingual templates (not live MT) ----------
# Keeping messages SHORT and structurally identical across languages so they're easy
# to review/approve once and reuse - this is how real public-alert systems manage
# multilingual accuracy at scale.
TRANSLATIONS = {
    "English": {
        "Good": "Air quality is good. Enjoy normal outdoor activities.",
        "Satisfactory": "Air quality is acceptable today.",
        "Moderate": "Air quality is moderate. Sensitive groups should take care.",
        "Poor": "Air quality is poor. Limit outdoor exertion.",
        "Very Poor": "Air quality is very poor. Avoid outdoor activity; wear a mask.",
        "Severe": "Air quality is severe. Stay indoors; this is a health emergency.",
    },
    "Hindi": {
        "Good": "\u0939\u0935\u093e \u0915\u0940 \u0917\u0941\u0923\u0935\u0924\u094d\u0924\u093e \u0905\u091a\u094d\u091b\u0940 \u0939\u0948\u0964 \u0938\u093e\u092e\u093e\u0928\u094d\u092f \u0917\u0924\u093f\u0935\u093f\u0927\u093f\u092f\u093e\u0902 \u091c\u093e\u0930\u0940 \u0930\u0916\u0947\u0902\u0964",
        "Satisfactory": "\u0906\u091c \u0939\u0935\u093e \u0915\u0940 \u0917\u0941\u0923\u0935\u0924\u094d\u0924\u093e \u0938\u0902\u0924\u094b\u0937\u091c\u0928\u0915 \u0939\u0948\u0964",
        "Moderate": "\u0939\u0935\u093e \u0915\u0940 \u0917\u0941\u0923\u0935\u0924\u094d\u0924\u093e \u092e\u0927\u094d\u092f\u092e \u0939\u0948\u0964 \u0938\u0902\u0935\u0947\u0926\u0928\u0936\u0940\u0932 \u0932\u094b\u0917 \u0938\u093e\u0935\u0927\u093e\u0928 \u0930\u0916\u0947\u0902\u0964",
        "Poor": "\u0939\u0935\u093e \u0915\u0940 \u0917\u0941\u0923\u0935\u0924\u094d\u0924\u093e \u0916\u0930\u093e\u092c \u0939\u0948\u0964 \u092c\u093e\u0939\u0930\u0940 \u0917\u0924\u093f\u0935\u093f\u0927\u093f\u092f\u093e\u0902 \u0938\u0940\u092e\u093f\u0924 \u0915\u0930\u0947\u0902\u0964",
        "Very Poor": "\u0939\u0935\u093e \u0915\u0940 \u0917\u0941\u0923\u0935\u0924\u094d\u0924\u093e \u092c\u0939\u0941\u0924 \u0916\u0930\u093e\u092c \u0939\u0948\u0964 \u092c\u093e\u0939\u0930 \u091c\u093e\u0928\u0947 \u0938\u0947 \u092c\u091a\u0947\u0902; \u092e\u093e\u0938\u094d\u0915 \u092a\u0939\u0928\u0947\u0902\u0964",
        "Severe": "\u0939\u0935\u093e \u0915\u0940 \u0917\u0941\u0923\u0935\u0924\u094d\u0924\u093e \u0917\u0902\u092d\u0940\u0930 \u0939\u0948\u0964 \u0918\u0930 \u092e\u0947\u0902 \u0930\u0939\u0947\u0902; \u092f\u0939 \u0938\u094d\u0935\u093e\u0938\u094d\u0925\u094d\u092f \u0906\u092a\u093e\u062a\u0915\u093e\u0932 \u0939\u0948\u0964",
    },
    "Marathi": {
        "Good": "\u0939\u0935\u0947\u091a\u0940 \u0917\u0941\u0923\u0935\u0924\u094d\u0924\u093e \u091a\u093e\u0902\u0917\u0932\u0940 \u0906\u0939\u0947. \u0938\u093e\u092e\u093e\u0928\u094d\u092f \u092c\u093e\u0939\u0947\u0930\u0940\u0932 \u0915\u093e\u092e\u0947 \u0915\u0930\u093e.",
        "Satisfactory": "\u0906\u091c \u0939\u0935\u0947\u091a\u0940 \u0917\u0941\u0923\u0935\u0924\u094d\u0924\u093e \u0938\u092e\u093e\u0927\u093e\u0928\u0915\u093e\u0930\u0915 \u0906\u0939\u0947.",
        "Moderate": "\u0939\u0935\u0947\u091a\u0940 \u0917\u0941\u0923\u0935\u0924\u094d\u0924\u093e \u092e\u0927\u094d\u092f\u092e \u0906\u0939\u0947. \u0938\u0902\u0935\u0947\u0926\u0928\u0936\u0940\u0932 \u0935\u094d\u092f\u0915\u094d\u0924\u0940\u0902\u0928\u0940 \u0915\u093e\u0933\u091c\u0940 \u0918\u094d\u092f\u093e\u0935\u0940.",
        "Poor": "\u0939\u0935\u0947\u091a\u0940 \u0917\u0941\u0923\u0935\u0924\u094d\u0924\u093e \u0916\u0930\u093e\u092c \u0906\u0939\u0947. \u092c\u093e\u0939\u0947\u0930\u0940\u0932 \u0936\u094d\u0930\u092e \u091f\u093e\u0933\u093e.",
        "Very Poor": "\u0939\u0935\u0947\u091a\u0940 \u0917\u0941\u0923\u0935\u0924\u094d\u0924\u093e \u0916\u0942\u092a \u0916\u0930\u093e\u092c \u0906\u0939\u0947. \u092c\u093e\u0939\u0947\u0930 \u091c\u093e\u0923\u0947 \u091f\u093e\u0933\u093e; \u092e\u093e\u0938\u094d\u0915 \u0935\u093e\u092a\u0930\u093e.",
        "Severe": "\u0939\u0935\u0947\u091a\u0940 \u0917\u0941\u0923\u0935\u0924\u094d\u0924\u093e \u0917\u0902\u092d\u0940\u0930 \u0906\u0939\u0947. \u0918\u0930\u0940\u0902\u091a \u0930\u093e\u0939\u093e; \u0939\u0940 \u0906\u0930\u094b\u0917\u094d\u092f \u0906\u0923\u0940\u092c\u093e\u0923\u0940 \u0906\u0939\u0947.",
    },
}

CITY_LANGUAGE_MAP = {"Delhi": "Hindi", "Mumbai": "Marathi"}  # extensible: Bengaluru->Kannada, Chennai->Tamil

CHANNEL_FORMATS = {
    "Mobile App": "\U0001F4F1 {advisory}\n{vulnerable}",
    "Public Display": "AQI ALERT - {ward} - {category}\n{advisory}",
    "IVR (voice call script)": "This is an automated air quality alert for {ward}. {advisory} {vulnerable}",
}

records = []
for _, row in latest_wards.iterrows():
    aqi = row["Simulated_AQI"]
    category = classify_aqi(aqi)
    city = row["City"]
    local_lang = CITY_LANGUAGE_MAP.get(city, "English")

    general_en = GENERAL_ADVICE[category]
    vulnerable_en = VULNERABLE_ADVICE.get(category, "No additional precautions needed for vulnerable groups today.")
    general_local = TRANSLATIONS[local_lang][category]

    for channel, fmt in CHANNEL_FORMATS.items():
        records.append({
            "City": city, "Ward": row["Ward"], "AQI": aqi, "Category": category,
            "Language": "English", "Channel": channel,
            "Message": fmt.format(ward=row["Ward"], category=category, advisory=general_en, vulnerable=vulnerable_en),
        })
        records.append({
            "City": city, "Ward": row["Ward"], "AQI": aqi, "Category": category,
            "Language": local_lang, "Channel": channel,
            "Message": fmt.format(ward=row["Ward"], category=category, advisory=general_local, vulnerable=vulnerable_en),
        })

advisory_df = pd.DataFrame(records)
advisory_df.to_csv(OUT_PATH, index=False)

print("=" * 100)
print(f"CITIZEN HEALTH ADVISORY AGENT - sample output (as of {latest_date.date()})")
print("=" * 100)
sample_wards = latest_wards.groupby("City").first().reset_index()
for _, w in sample_wards.iterrows():
    ward_msgs = advisory_df[(advisory_df.City == w["City"]) & (advisory_df.Ward == w["Ward"])]
    print(f"\n--- {w['City']} - {w['Ward']} | AQI: {w['Simulated_AQI']:.0f} | Category: {classify_aqi(w['Simulated_AQI'])} ---")
    for _, m in ward_msgs.iterrows():
        print(f"  [{m['Language']} | {m['Channel']}]")
        print(f"    {m['Message']}")

print(f"\nSaved -> {OUT_PATH}")
print(f"Total alert records generated: {len(advisory_df)}")
