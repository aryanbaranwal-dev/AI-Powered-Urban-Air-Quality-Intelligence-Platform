"""
Agent 8 — Personal Advisory Agent
===================================
Takes an individual citizen's profile (age, medical condition,
location/ward, occupation) plus the forecast AQI for their area and
returns a personalized risk score with 5 concrete recommendations
(outdoor activity, mask, exercise, medicine reminder, hospital), in
English, Hindi, Tamil, Kannada, and Bengali.

This sits alongside (not replacing) the existing city/ward-broadcast
CitizenAdvisoryAgent — that one is "what should this AQI band tell
everyone"; this one is "what should this specific person do".

Translation note (same policy as advisory_agent.py): English and Hindi
text below was written directly for this project. Tamil, Kannada, and
Bengali text was AI-assisted to extend coverage and has NOT been
reviewed by a native speaker or public-health translator — flag for
professional review before any real deployment.

This agent gives general, non-prescriptive guidance only (e.g. "keep
your prescribed inhaler accessible") — it never specifies medication
names, doses, or timing, which stays with the person's own doctor.
"""
from __future__ import annotations

from typing import Dict, Optional

import pandas as pd

from agents.base_agent import BaseAgent, AgentMessage
from agents.aqi_utils import get_aqi_meta
from agents.evidence_engine import _haversine_km

SUPPORTED_LANGUAGES = ["English", "Hindi", "Tamil", "Kannada", "Bengali"]

MEDICAL_CONDITIONS = ["None", "Asthma", "Heart Disease", "COPD / Lung Disease", "Pregnancy", "Diabetes"]
OCCUPATIONS = ["Indoor / Office", "Outdoor Worker", "Delivery / Traffic Duty", "Construction Worker", "Student", "Homemaker / Retired"]

HIGH_EXPOSURE_OCCUPATIONS = {"Outdoor Worker", "Delivery / Traffic Duty", "Construction Worker"}

RISK_BANDS = [
    (0, 24, "Low", "#22c55e", "🟢"),
    (25, 49, "Moderate", "#facc15", "🟡"),
    (50, 69, "High", "#fb923c", "🟠"),
    (70, 89, "Severe", "#f87171", "🔴"),
    (90, 101, "Critical", "#c026d3", "⚫"),
]


def _risk_band(score: float) -> tuple:
    for lo, hi, label, color, icon in RISK_BANDS:
        if lo <= score < hi:
            return label, color, icon
    return RISK_BANDS[-1][2], RISK_BANDS[-1][3], RISK_BANDS[-1][4]


# band -> language -> (health_alert, outdoor, mask, exercise)
_BAND_TEXT: Dict[str, Dict[str, tuple]] = {
    "Low": {
        "English": ("Air quality poses minimal risk for you today.", "Normal outdoor activity is fine.", "No mask needed.", "Full outdoor exercise is fine."),
        "Hindi": ("आज की वायु गुणवत्ता आपके लिए न्यूनतम जोखिम है।", "सामान्य बाहरी गतिविधि ठीक है।", "मास्क की आवश्यकता नहीं।", "पूरी बाहरी एक्सरसाइज़ ठीक है।"),
        "Tamil": ("இன்றைய காற்றின் தரம் உங்களுக்கு குறைந்த ஆபத்தை மட்டுமே தருகிறது.", "வழக்கமான வெளிப்புற செயல்பாடு பரவாயில்லை.", "மாஸ்க் தேவையில்லை.", "முழு வெளிப்புற உடற்பயிற்சி பரவாயில்லை."),
        "Kannada": ("ಇಂದಿನ ಗಾಳಿಯ ಗುಣಮಟ್ಟ ನಿಮಗೆ ಕನಿಷ್ಠ ಅಪಾಯವನ್ನು ಹೊಂದಿದೆ.", "ಸಾಮಾನ್ಯ ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆ ಸರಿ.", "ಮಾಸ್ಕ್ ಅಗತ್ಯವಿಲ್ಲ.", "ಪೂರ್ಣ ಹೊರಾಂಗಣ ವ್ಯಾಯಾಮ ಸರಿ."),
        "Bengali": ("আজকের বায়ুর গুণমান আপনার জন্য ন্যূনতম ঝুঁকিপূর্ণ।", "স্বাভাবিক বহিরঙ্গন কার্যকলাপ ঠিক আছে।", "মাস্কের প্রয়োজন নেই।", "সম্পূর্ণ বহিরঙ্গন ব্যায়াম করা যেতে পারে।"),
    },
    "Moderate": {
        "English": ("Air quality may cause mild discomfort for you.", "Reduce prolonged outdoor exposure during peak traffic hours.", "A surgical mask is advisable outdoors.", "Light outdoor exercise only; move intense workouts indoors."),
        "Hindi": ("वायु गुणवत्ता आपको हल्की परेशानी दे सकती है।", "व्यस्त यातायात समय में बाहर लंबे समय तक रहने से बचें।", "बाहर सर्जिकल मास्क पहनना उचित है।", "केवल हल्की बाहरी एक्सरसाइज़ करें; तेज़ वर्कआउट घर के अंदर करें।"),
        "Tamil": ("காற்றின் தரம் உங்களுக்கு சிறிது அசெளகரியத்தை ஏற்படுத்தலாம்.", "பரபரப்பான போக்குவரத்து நேரங்களில் நீண்ட நேர வெளிப்புற வெளிப்பாட்டைக் குறைக்கவும்.", "வெளியில் சர்ஜிகல் மாஸ்க் அணிவது நல்லது.", "இலகுவான வெளிப்புற உடற்பயிற்சி மட்டும்; தீவிர பயிற்சிகளை உள்ளே செய்யவும்."),
        "Kannada": ("ಗಾಳಿಯ ಗುಣಮಟ್ಟ ನಿಮಗೆ ಸ್ವಲ್ಪ ಅಸ್ವಸ್ಥತೆ ಉಂಟುಮಾಡಬಹುದು.", "ಗರಿಷ್ಠ ಸಂಚಾರ ಸಮಯದಲ್ಲಿ ದೀರ್ಘಕಾಲ ಹೊರಾಂಗಣ ಒಡ್ಡಿಕೊಳ್ಳುವಿಕೆಯನ್ನು ಕಡಿಮೆ ಮಾಡಿ.", "ಹೊರಗೆ ಸರ್ಜಿಕಲ್ ಮಾಸ್ಕ್ ಧರಿಸುವುದು ಸೂಕ್ತ.", "ಹಗುರವಾದ ಹೊರಾಂಗಣ ವ್ಯಾಯಾಮ ಮಾತ್ರ; ತೀವ್ರ ವ್ಯಾಯಾಮವನ್ನು ಒಳಾಂಗಣದಲ್ಲಿ ಮಾಡಿ."),
        "Bengali": ("বায়ুর গুণমান আপনার সামান্য অস্বস্তি সৃষ্টি করতে পারে।", "ব্যস্ত ট্রাফিক সময়ে দীর্ঘ বহিরঙ্গন সংস্পর্শ কমান।", "বাইরে সার্জিক্যাল মাস্ক পরা ভালো।", "শুধু হালকা বহিরঙ্গন ব্যায়াম করুন; তীব্র ওয়ার্কআউট ঘরের ভিতরে করুন।"),
    },
    "High": {
        "English": ("Air quality is likely to affect you today — take precautions.", "Limit outdoor time; avoid the busiest traffic hours entirely.", "Wear an N95 mask whenever outdoors.", "Avoid outdoor exercise; move workouts indoors."),
        "Hindi": ("आज वायु गुणवत्ता आपको प्रभावित कर सकती है — सावधानी बरतें।", "बाहर रहने का समय सीमित करें; व्यस्ततम यातायात समय से पूरी तरह बचें।", "बाहर जाते समय हमेशा N95 मास्क पहनें।", "बाहरी एक्सरसाइज़ से बचें; वर्कआउट घर के अंदर करें।"),
        "Tamil": ("இன்று காற்றின் தரம் உங்களை பாதிக்கக்கூடும் — முன்னெச்சரிக்கை எடுக்கவும்.", "வெளியில் இருக்கும் நேரத்தைக் குறைக்கவும்; பரபரப்பான போக்குவரத்து நேரங்களை முற்றிலும் தவிர்க்கவும்.", "வெளியில் செல்லும்போது எப்போதும் N95 மாஸ்க் அணியவும்.", "வெளிப்புற உடற்பயிற்சியைத் தவிர்க்கவும்; பயிற்சிகளை உள்ளே செய்யவும்."),
        "Kannada": ("ಇಂದು ಗಾಳಿಯ ಗುಣಮಟ್ಟ ನಿಮ್ಮ ಮೇಲೆ ಪರಿಣಾಮ ಬೀರುವ ಸಾಧ್ಯತೆಯಿದೆ — ಮುನ್ನೆಚ್ಚರಿಕೆ ವಹಿಸಿ.", "ಹೊರಗಿನ ಸಮಯವನ್ನು ಮಿತಿಗೊಳಿಸಿ; ಗರಿಷ್ಠ ಸಂಚಾರ ಸಮಯವನ್ನು ಸಂಪೂರ್ಣವಾಗಿ ತಪ್ಪಿಸಿ.", "ಹೊರಗೆ ಹೋಗುವಾಗ ಯಾವಾಗಲೂ N95 ಮಾಸ್ಕ್ ಧರಿಸಿ.", "ಹೊರಾಂಗಣ ವ್ಯಾಯಾಮವನ್ನು ತಪ್ಪಿಸಿ; ವ್ಯಾಯಾಮವನ್ನು ಒಳಾಂಗಣದಲ್ಲಿ ಮಾಡಿ."),
        "Bengali": ("আজ বায়ুর গুণমান আপনাকে প্রভাবিত করতে পারে — সতর্কতা অবলম্বন করুন।", "বাইরে থাকার সময় সীমিত করুন; ব্যস্ততম ট্রাফিক সময় সম্পূর্ণ এড়িয়ে চলুন।", "বাইরে গেলে সবসময় N95 মাস্ক পরুন।", "বহিরঙ্গন ব্যায়াম এড়িয়ে চলুন; ওয়ার্কআউট ঘরের ভিতরে করুন।"),
    },
    "Severe": {
        "English": ("Health warning: air quality is likely to seriously affect you today.", "Avoid outdoor exposure as much as possible.", "N95 mask is mandatory outdoors; consider an air purifier indoors.", "No outdoor exercise. Keep indoor activity light too."),
        "Hindi": ("स्वास्थ्य चेतावनी: आज वायु गुणवत्ता आपको गंभीर रूप से प्रभावित कर सकती है।", "जितना हो सके बाहरी संपर्क से बचें।", "बाहर N95 मास्क अनिवार्य है; घर के अंदर एयर प्यूरीफायर का उपयोग करें।", "कोई बाहरी एक्सरसाइज़ नहीं। घर के अंदर भी हल्की गतिविधि रखें।"),
        "Tamil": ("சுகாதார எச்சரிக்கை: இன்று காற்றின் தரம் உங்களை கடுமையாக பாதிக்கக்கூடும்.", "முடிந்தவரை வெளிப்புற வெளிப்பாட்டைத் தவிர்க்கவும்.", "வெளியில் N95 மாஸ்க் கட்டாயம்; வீட்டிற்குள் காற்று சுத்திகரிப்பியைப் பயன்படுத்தவும்.", "வெளிப்புற உடற்பயிற்சி வேண்டாம். வீட்டிற்குள்ளும் இலகுவான செயல்பாடு மட்டும்."),
        "Kannada": ("ಆರೋಗ್ಯ ಎಚ್ಚರಿಕೆ: ಇಂದು ಗಾಳಿಯ ಗುಣಮಟ್ಟ ನಿಮ್ಮನ್ನು ಗಂಭೀರವಾಗಿ ಬಾಧಿಸಬಹುದು.", "ಸಾಧ್ಯವಾದಷ್ಟು ಹೊರಾಂಗಣ ಒಡ್ಡಿಕೊಳ್ಳುವಿಕೆಯನ್ನು ತಪ್ಪಿಸಿ.", "ಹೊರಗೆ N95 ಮಾಸ್ಕ್ ಕಡ್ಡಾಯ; ಒಳಾಂಗಣದಲ್ಲಿ ಏರ್ ಪ್ಯೂರಿಫೈಯರ್ ಬಳಸಿ.", "ಹೊರಾಂಗಣ ವ್ಯಾಯಾಮ ಬೇಡ. ಒಳಾಂಗಣ ಚಟುವಟಿಕೆಯನ್ನೂ ಹಗುರವಾಗಿಡಿ."),
        "Bengali": ("স্বাস্থ্য সতর্কতা: আজ বায়ুর গুণমান আপনাকে গুরুতরভাবে প্রভাবিত করতে পারে।", "যতটা সম্ভব বহিরঙ্গন সংস্পর্শ এড়িয়ে চলুন।", "বাইরে N95 মাস্ক বাধ্যতামূলক; ঘরের ভিতরে এয়ার পিউরিফায়ার ব্যবহার করুন।", "কোনো বহিরঙ্গন ব্যায়াম নয়। ঘরের ভিতরেও হালকা কার্যকলাপ রাখুন।"),
    },
    "Critical": {
        "English": ("Health emergency for your profile: stay indoors and monitor symptoms closely.", "Avoid all outdoor exposure today.", "N95 mask mandatory for any essential outdoor trip; seal windows/doors, run an air purifier.", "No outdoor or strenuous indoor exercise."),
        "Hindi": ("आपकी प्रोफ़ाइल के लिए स्वास्थ्य आपातकाल: घर के अंदर रहें और लक्षणों पर बारीकी से नज़र रखें।", "आज पूरी तरह से बाहरी संपर्क से बचें।", "किसी भी आवश्यक बाहरी यात्रा के लिए N95 मास्क अनिवार्य है; खिड़की-दरवाज़े बंद रखें, एयर प्यूरीफायर चलाएं।", "कोई बाहरी या तेज़ इनडोर एक्सरसाइज़ नहीं।"),
        "Tamil": ("உங்கள் சுயவிவரத்திற்கு சுகாதார அவசரநிலை: வீட்டிற்குள் இருந்து அறிகுறிகளை உன்னிப்பாகக் கவனிக்கவும்.", "இன்று அனைத்து வெளிப்புற வெளிப்பாட்டையும் தவிர்க்கவும்.", "அத்தியாவசிய வெளிப்புற பயணத்திற்கு N95 மாஸ்க் கட்டாயம்; ஜன்னல்/கதவுகளை மூடி, காற்று சுத்திகரிப்பியை இயக்கவும்.", "வெளிப்புற அல்லது கடுமையான உள்ளக உடற்பயிற்சி வேண்டாம்."),
        "Kannada": ("ನಿಮ್ಮ ಪ್ರೊಫೈಲ್‌ಗೆ ಆರೋಗ್ಯ ತುರ್ತುಸ್ಥಿತಿ: ಮನೆಯೊಳಗೆ ಇರಿ ಮತ್ತು ಲಕ್ಷಣಗಳನ್ನು ಸೂಕ್ಷ್ಮವಾಗಿ ಗಮನಿಸಿ.", "ಇಂದು ಎಲ್ಲಾ ಹೊರಾಂಗಣ ಒಡ್ಡಿಕೊಳ್ಳುವಿಕೆಯನ್ನು ತಪ್ಪಿಸಿ.", "ಅಗತ್ಯ ಹೊರಾಂಗಣ ಪ್ರಯಾಣಕ್ಕೆ N95 ಮಾಸ್ಕ್ ಕಡ್ಡಾಯ; ಕಿಟಕಿ/ಬಾಗಿಲುಗಳನ್ನು ಮುಚ್ಚಿ, ಏರ್ ಪ್ಯೂರಿಫೈಯರ್ ಚಲಾಯಿಸಿ.", "ಹೊರಾಂಗಣ ಅಥವಾ ತೀವ್ರ ಒಳಾಂಗಣ ವ್ಯಾಯಾಮ ಬೇಡ."),
        "Bengali": ("আপনার প্রোফাইলের জন্য স্বাস্থ্য জরুরি অবস্থা: ঘরের ভিতরে থাকুন এবং উপসর্গ নিবিড়ভাবে পর্যবেক্ষণ করুন।", "আজ সমস্ত বহিরঙ্গন সংস্পর্শ এড়িয়ে চলুন।", "যেকোনো প্রয়োজনীয় বহিরঙ্গন ভ্রমণের জন্য N95 মাস্ক বাধ্যতামূলক; জানালা/দরজা বন্ধ রাখুন, এয়ার পিউরিফায়ার চালান।", "কোনো বহিরঙ্গন বা তীব্র ঘরোয়া ব্যায়াম নয়।"),
    },
}

# condition -> language -> medicine reminder (general, non-prescriptive)
_MEDICINE_TEXT: Dict[str, Dict[str, str]] = {
    "None": {
        "English": "No regular medication flagged. Monitor for cough, breathlessness, or eye irritation.",
        "Hindi": "कोई नियमित दवा चिह्नित नहीं। खांसी, सांस फूलने या आंखों में जलन पर ध्यान दें।",
        "Tamil": "வழக்கமான மருந்து எதுவும் குறிக்கப்படவில்லை. இருமல், மூச்சு விடுவதில் சிரமம் அல்லது கண் எரிச்சலைக் கவனிக்கவும்.",
        "Kannada": "ನಿಯಮಿತ ಔಷಧಿ ಗುರುತಿಸಿಲ್ಲ. ಕೆಮ್ಮು, ಉಸಿರಾಟದ ತೊಂದರೆ ಅಥವಾ ಕಣ್ಣಿನ ಕಿರಿಕಿರಿಯನ್ನು ಗಮನಿಸಿ.",
        "Bengali": "কোনো নিয়মিত ওষুধ চিহ্নিত করা হয়নি। কাশি, শ্বাসকষ্ট বা চোখ জ্বালা লক্ষ্য করুন।",
    },
    "Asthma": {
        "English": "Keep your prescribed rescue inhaler accessible at all times today.",
        "Hindi": "आज हर समय अपना निर्धारित रेस्क्यू इनहेलर पास रखें।",
        "Tamil": "இன்று எப்போதும் உங்கள் பரிந்துரைக்கப்பட்ட ரெஸ்க்யூ இன்ஹேலரை அருகில் வைத்திருங்கள்.",
        "Kannada": "ಇಂದು ಯಾವಾಗಲೂ ನಿಮ್ಮ ಸೂಚಿತ ರೆಸ್ಕ್ಯೂ ಇನ್ಹೇಲರ್ ಅನ್ನು ಹತ್ತಿರ ಇಟ್ಟುಕೊಳ್ಳಿ.",
        "Bengali": "আজ সবসময় আপনার নির্ধারিত রেসকিউ ইনহেলার কাছে রাখুন।",
    },
    "Heart Disease": {
        "English": "Take your prescribed heart medication as usual; avoid sudden exertion outdoors.",
        "Hindi": "अपनी निर्धारित हृदय दवा हमेशा की तरह लें; बाहर अचानक परिश्रम से बचें।",
        "Tamil": "உங்கள் பரிந்துரைக்கப்பட்ட இதய மருந்தை வழக்கம் போல் எடுத்துக் கொள்ளுங்கள்; வெளியில் திடீர் உழைப்பைத் தவிர்க்கவும்.",
        "Kannada": "ನಿಮ್ಮ ಸೂಚಿತ ಹೃದಯ ಔಷಧಿಯನ್ನು ಎಂದಿನಂತೆ ತೆಗೆದುಕೊಳ್ಳಿ; ಹೊರಗೆ ಹಠಾತ್ ಶ್ರಮವನ್ನು ತಪ್ಪಿಸಿ.",
        "Bengali": "আপনার নির্ধারিত হৃদরোগের ওষুধ যথারীতি নিন; বাইরে হঠাৎ পরিশ্রম এড়িয়ে চলুন।",
    },
    "COPD / Lung Disease": {
        "English": "Keep prescribed inhalers/nebulizer accessible; watch closely for increased breathlessness.",
        "Hindi": "निर्धारित इनहेलर/नेबुलाइज़र पास रखें; सांस फूलने में वृद्धि पर बारीकी से नज़र रखें।",
        "Tamil": "பரிந்துரைக்கப்பட்ட இன்ஹேலர்/நெபுலைசரை அருகில் வைத்திருங்கள்; மூச்சு விடுவதில் அதிக சிரமத்தை உன்னிப்பாகக் கவனிக்கவும்.",
        "Kannada": "ಸೂಚಿತ ಇನ್ಹೇಲರ್/ನೆಬ್ಯುಲೈಸರ್ ಹತ್ತಿರ ಇಟ್ಟುಕೊಳ್ಳಿ; ಉಸಿರಾಟದ ತೊಂದರೆ ಹೆಚ್ಚಳವನ್ನು ಸೂಕ್ಷ್ಮವಾಗಿ ಗಮನಿಸಿ.",
        "Bengali": "নির্ধারিত ইনহেলার/নেবুলাইজার কাছে রাখুন; শ্বাসকষ্ট বৃদ্ধি নিবিড়ভাবে লক্ষ্য করুন।",
    },
    "Pregnancy": {
        "English": "Continue prenatal vitamins as prescribed; discuss any breathing discomfort with your doctor promptly.",
        "Hindi": "निर्धारित प्रसवपूर्व विटामिन जारी रखें; सांस संबंधी किसी भी परेशानी पर तुरंत डॉक्टर से बात करें।",
        "Tamil": "பரிந்துரைக்கப்பட்ட பிரசவத்திற்கு முந்தைய வைட்டமின்களைத் தொடரவும்; சுவாசக் கோளாறு ஏதேனும் இருந்தால் உடனடியாக மருத்துவரிடம் பேசவும்.",
        "Kannada": "ಸೂಚಿತ ಪ್ರಸವಪೂರ್ವ ವಿಟಮಿನ್‌ಗಳನ್ನು ಮುಂದುವರಿಸಿ; ಯಾವುದೇ ಉಸಿರಾಟದ ಅಸ್ವಸ್ಥತೆಯನ್ನು ತಕ್ಷಣ ವೈದ್ಯರೊಂದಿಗೆ ಚರ್ಚಿಸಿ.",
        "Bengali": "নির্ধারিত প্রসবপূর্ব ভিটামিন চালিয়ে যান; শ্বাসকষ্ট হলে দ্রুত ডাক্তারের সাথে কথা বলুন।",
    },
    "Diabetes": {
        "English": "Continue your regular medication/insulin schedule; poor air days can add stress, so monitor sugar levels closely.",
        "Hindi": "अपनी नियमित दवा/इंसुलिन शेड्यूल जारी रखें; खराब वायु वाले दिनों में शुगर स्तर पर बारीकी से नज़र रखें।",
        "Tamil": "உங்கள் வழக்கமான மருந்து/இன்சுலின் அட்டவணையைத் தொடரவும்; மோசமான காற்று நாட்களில் சர்க்கரை அளவை உன்னிப்பாகக் கவனிக்கவும்.",
        "Kannada": "ನಿಮ್ಮ ನಿಯಮಿತ ಔಷಧಿ/ಇನ್ಸುಲಿನ್ ವೇಳಾಪಟ್ಟಿಯನ್ನು ಮುಂದುವರಿಸಿ; ಕಳಪೆ ಗಾಳಿಯ ದಿನಗಳಲ್ಲಿ ಸಕ್ಕರೆ ಮಟ್ಟವನ್ನು ಸೂಕ್ಷ್ಮವಾಗಿ ಗಮನಿಸಿ.",
        "Bengali": "আপনার নিয়মিত ওষুধ/ইনসুলিন সময়সূচী চালিয়ে যান; খারাপ বায়ুর দিনে সুগারের মাত্রা নিবিড়ভাবে লক্ষ্য করুন।",
    },
}

# whether a hospital visit is proactively recommended, per language
_HOSPITAL_TEXT: Dict[str, Dict[str, str]] = {
    "not_needed": {
        "English": "No hospital visit needed — just monitor symptoms.",
        "Hindi": "अस्पताल जाने की आवश्यकता नहीं — बस लक्षणों पर नज़र रखें।",
        "Tamil": "மருத்துவமனை செல்ல தேவையில்லை — அறிகுறிகளை மட்டும் கவனிக்கவும்.",
        "Kannada": "ಆಸ್ಪತ್ರೆಗೆ ಭೇಟಿ ನೀಡುವ ಅಗತ್ಯವಿಲ್ಲ — ಲಕ್ಷಣಗಳನ್ನು ಮಾತ್ರ ಗಮನಿಸಿ.",
        "Bengali": "হাসপাতালে যাওয়ার প্রয়োজন নেই — শুধু উপসর্গ লক্ষ্য করুন।",
    },
    "recommended": {
        "English": "If you notice breathlessness, chest discomfort, or persistent coughing, consult a doctor promptly. Nearest hospital: {hospital}.",
        "Hindi": "यदि सांस फूलना, सीने में परेशानी या लगातार खांसी महसूस हो, तो तुरंत डॉक्टर से मिलें। निकटतम अस्पताल: {hospital}।",
        "Tamil": "மூச்சுத் திணறல், மார்பு அசெளகரியம் அல்லது தொடர்ச்சியான இருமல் இருந்தால், உடனடியாக மருத்துவரை அணுகவும். அருகிலுள்ள மருத்துவமனை: {hospital}.",
        "Kannada": "ಉಸಿರಾಟದ ತೊಂದರೆ, ಎದೆ ಅಸ್ವಸ್ಥತೆ ಅಥವಾ ನಿರಂತರ ಕೆಮ್ಮು ಕಂಡುಬಂದರೆ, ತಕ್ಷಣ ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಿ. ಹತ್ತಿರದ ಆಸ್ಪತ್ರೆ: {hospital}.",
        "Bengali": "শ্বাসকষ্ট, বুকে অস্বস্তি বা ক্রমাগত কাশি লক্ষ্য করলে দ্রুত ডাক্তারের সাথে পরামর্শ করুন। নিকটতম হাসপাতাল: {hospital}।",
    },
}

_RISK_FACTOR_LABELS: Dict[str, Dict[str, str]] = {
    "age_child": {"English": "Age under 12 increases exposure sensitivity", "Hindi": "12 वर्ष से कम आयु में जोखिम अधिक होता है",
                  "Tamil": "12 வயதுக்குட்பட்டோருக்கு ஆபத்து அதிகம்", "Kannada": "12 ವರ್ಷಕ್ಕಿಂತ ಕಡಿಮೆ ವಯಸ್ಸು ಅಪಾಯವನ್ನು ಹೆಚ್ಚಿಸುತ್ತದೆ",
                  "Bengali": "১২ বছরের কম বয়সে ঝুঁকি বেশি"},
    "age_senior": {"English": "Age 60+ increases exposure sensitivity", "Hindi": "60+ आयु में जोखिम अधिक होता है",
                   "Tamil": "60+ வயதுக்கு ஆபத்து அதிகம்", "Kannada": "60+ ವಯಸ್ಸು ಅಪಾಯವನ್ನು ಹೆಚ್ಚಿಸುತ್ತದೆ",
                   "Bengali": "৬০+ বয়সে ঝুঁকি বেশি"},
    "condition": {"English": "Pre-existing condition increases risk", "Hindi": "पूर्व स्वास्थ्य स्थिति जोखिम बढ़ाती है",
                  "Tamil": "முன்பே உள்ள நோய் ஆபத்தை அதிகரிக்கிறது", "Kannada": "ಪೂರ್ವ-ಅಸ್ತಿತ್ವದ ಸ್ಥಿತಿ ಅಪಾಯವನ್ನು ಹೆಚ್ಚಿಸುತ್ತದೆ",
                  "Bengali": "পূর্ববর্তী স্বাস্থ্য অবস্থা ঝুঁকি বাড়ায়"},
    "occupation": {"English": "High-exposure occupation increases risk", "Hindi": "अधिक जोखिम वाला व्यवसाय जोखिम बढ़ाता है",
                   "Tamil": "அதிக வெளிப்பாடு தொழில் ஆபத்தை அதிகரிக்கிறது", "Kannada": "ಹೆಚ್ಚಿನ-ಒಡ್ಡಿಕೊಳ್ಳುವಿಕೆ ಉದ್ಯೋಗ ಅಪಾಯವನ್ನು ಹೆಚ್ಚಿಸುತ್ತದೆ",
                   "Bengali": "অধিক-এক্সপোজার পেশা ঝুঁকি বাড়ায়"},
    "high_aqi": {"English": "Forecast AQI itself is the dominant risk factor", "Hindi": "पूर्वानुमानित AQI ही सबसे बड़ा जोखिम कारक है",
                 "Tamil": "முன்னறிவிக்கப்பட்ட AQI-யே முதன்மை ஆபத்து காரணி", "Kannada": "ಮುನ್ಸೂಚಿತ AQI ಸ್ವತಃ ಪ್ರಮುಖ ಅಪಾಯಕಾರಿ ಅಂಶ",
                 "Bengali": "পূর্বাভাসিত AQI-ই প্রধান ঝুঁকির কারণ"},
}


class PersonalAdvisoryAgent(BaseAgent):
    name = "personal_advisory_agent"

    def run(
        self,
        city: str,
        age: int,
        medical_condition: str,
        occupation: str,
        forecast_aqi: float,
        ward: Optional[str] = None,
        ward_lat: Optional[float] = None,
        ward_lon: Optional[float] = None,
        geo_intel_df: Optional[pd.DataFrame] = None,
        languages=None,
    ) -> AgentMessage:
        try:
            languages = languages or SUPPORTED_LANGUAGES
            meta = get_aqi_meta(forecast_aqi)

            # ---- Risk score: AQI baseline (0-70) + demographic/occupational
            # risk add-ons (0-30), capped at 100. AQI baseline uses a
            # smooth curve so it doesn't jump discontinuously at band edges.
            aqi_component = min(70.0, (forecast_aqi / 500.0) * 70.0)
            factors = []
            addon = 0.0
            if age < 12:
                addon += 8; factors.append("age_child")
            elif age >= 60:
                addon += 8; factors.append("age_senior")
            if medical_condition and medical_condition != "None":
                addon += 12; factors.append("condition")
            if occupation in HIGH_EXPOSURE_OCCUPATIONS:
                addon += 10; factors.append("occupation")
            if forecast_aqi >= 300:
                factors.append("high_aqi")

            risk_score = round(min(100.0, aqi_component + addon), 1)
            band, band_color, band_icon = _risk_band(risk_score)

            # ---- Nearest hospital (real geospatial lookup, when we have
            # a ward location and the geo_intelligence point layer).
            hospital_name = None
            hospital_distance_km = None
            if geo_intel_df is not None and ward_lat is not None and ward_lon is not None:
                hospitals = geo_intel_df[(geo_intel_df["city"] == city) & (geo_intel_df["layer"] == "hospital")]
                if len(hospitals):
                    dists = hospitals.apply(lambda r: _haversine_km(ward_lat, ward_lon, r["lat"], r["lon"]), axis=1)
                    nearest_idx = dists.idxmin()
                    hospital_name = str(hospitals.loc[nearest_idx, "name"])
                    hospital_distance_km = round(float(dists.loc[nearest_idx]), 1)

            hospital_variant = "recommended" if band in ("High", "Severe", "Critical") else "not_needed"

            outputs = {}
            for lang in languages:
                health_alert, outdoor, mask, exercise = _BAND_TEXT.get(band, _BAND_TEXT["Moderate"]).get(
                    lang, _BAND_TEXT.get(band, _BAND_TEXT["Moderate"])["English"]
                )
                medicine = _MEDICINE_TEXT.get(medical_condition, _MEDICINE_TEXT["None"]).get(
                    lang, _MEDICINE_TEXT.get(medical_condition, _MEDICINE_TEXT["None"])["English"]
                )
                hospital_template = _HOSPITAL_TEXT[hospital_variant].get(lang, _HOSPITAL_TEXT[hospital_variant]["English"])
                if hospital_variant == "recommended":
                    hosp_display = f"{hospital_name} ({hospital_distance_km} km)" if hospital_name else (
                        "nearest hospital" if lang == "English" else "—")
                    hospital = hospital_template.format(hospital=hosp_display)
                else:
                    hospital = hospital_template

                outputs[lang] = {
                    "health_alert": health_alert,
                    "outdoor_recommendation": outdoor,
                    "mask_recommendation": mask,
                    "exercise_recommendation": exercise,
                    "medicine_reminder": medicine,
                    "hospital_recommendation": hospital,
                }

            return self._ok(city, {
                "profile": {
                    "age": age, "medical_condition": medical_condition,
                    "occupation": occupation, "ward": ward,
                },
                "forecast_aqi": round(float(forecast_aqi), 1),
                "aqi_band": meta["label"],
                "risk_score": risk_score,
                "risk_band": band,
                "risk_band_color": band_color,
                "risk_band_icon": band_icon,
                "risk_factors": [
                    {"key": f, "label": {lang: _RISK_FACTOR_LABELS[f].get(lang, _RISK_FACTOR_LABELS[f]["English"]) for lang in languages}}
                    for f in factors
                ],
                "nearest_hospital": {"name": hospital_name, "distance_km": hospital_distance_km} if hospital_name else None,
                "recommendations": outputs,
                "method": "Risk score = AQI-proportional baseline (0-70) + age/condition/occupation add-ons (0-30), "
                          "capped at 100. Recommendations are template-based per risk band + medical condition, "
                          "not AI-generated free text, so every phrase is reviewable ahead of deployment.",
            })
        except Exception as exc:
            return self._error(city, str(exc))
