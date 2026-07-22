"""
Agent 4 — Citizen Advisory Agent
==================================
Generates multilingual, AQI-band-appropriate public health advisories.
Generated live from the current AQI band (rather than only replaying the
static demo CSV) so it produces a sensible message for every band,
including Severe, in every supported language.

Translation note: English, Hindi, and Marathi text below was written
directly by a human reviewer for this project. The Tamil, Kannada, and
Bengali text was added by an AI assistant to extend language coverage
and has NOT been reviewed by a native speaker or public-health
translator — flag it for professional review before using it in any
real deployment, since mistranslated health guidance carries real risk.
"""
from __future__ import annotations

from typing import Dict

from agents.base_agent import BaseAgent, AgentMessage
from agents.aqi_utils import get_aqi_meta

# icon, general-public message, sensitive-group message — per AQI band, per language
_ADVISORY_TEXT = {
    "Good": {
        "English": ("🟢", "Air quality is good. Enjoy normal outdoor activities.",
                    "No precautions needed for sensitive groups today."),
        "Hindi": ("🟢", "वायु गुणवत्ता अच्छी है। सामान्य रूप से बाहरी गतिविधियाँ करें।",
                  "संवेदनशील समूहों के लिए आज कोई सावधानी आवश्यक नहीं है।"),
        "Marathi": ("🟢", "हवेची गुणवत्ता चांगली आहे. नेहमीप्रमाणे बाहेरील कामे करा.",
                    "संवेदनशील गटांसाठी आज कोणतीही खबरदारी आवश्यक नाही."),
        "Tamil": ("🟢", "காற்றின் தரம் நல்லதாக உள்ளது. வழக்கமான வெளிப்புற செயல்பாடுகளை மேற்கொள்ளலாம்.",
                  "இன்று உணர்திறன் கொண்ட குழுக்களுக்கு எச்சரிக்கைகள் தேவையில்லை."),
        "Kannada": ("🟢", "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಉತ್ತಮವಾಗಿದೆ. ಎಂದಿನಂತೆ ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಗಳನ್ನು ಮುಂದುವರಿಸಿ.",
                    "ಸೂಕ್ಷ್ಮ ಗುಂಪುಗಳಿಗೆ ಇಂದು ಯಾವುದೇ ಮುನ್ನೆಚ್ಚರಿಕೆ ಅಗತ್ಯವಿಲ್ಲ."),
        "Bengali": ("🟢", "বায়ুর গুণমান ভালো। স্বাভাবিক বহিরঙ্গন কার্যকলাপ চালিয়ে যেতে পারেন।",
                    "আজ সংবেদনশীল গোষ্ঠীর জন্য কোনো সতর্কতার প্রয়োজন নেই।"),
    },
    "Satisfactory": {
        "English": ("🟡", "Air quality is satisfactory. Minor breathing discomfort possible for unusually sensitive people.",
                    "People with asthma should keep rescue inhalers handy."),
        "Hindi": ("🟡", "वायु गुणवत्ता संतोषजनक है। अत्यधिक संवेदनशील लोगों को हल्की परेशानी हो सकती है।",
                  "अस्थमा रोगी अपना इनहेलर साथ रखें।"),
        "Marathi": ("🟡", "हवेची गुणवत्ता समाधानकारक आहे. अतिसंवेदनशील व्यक्तींना थोडा त्रास होऊ शकतो.",
                    "दम्याच्या रुग्णांनी इनहेलर सोबत ठेवावा."),
        "Tamil": ("🟡", "காற்றின் தரம் திருப்திகரமாக உள்ளது. மிகவும் உணர்திறன் கொண்டவர்களுக்கு சிறிய சுவாசக் கோளாறு ஏற்படலாம்.",
                  "ஆஸ்துமா நோயாளிகள் தங்கள் இன்ஹேலரை அருகில் வைத்திருக்கவும்."),
        "Kannada": ("🟡", "ಗಾಳಿಯ ಗುಣಮಟ್ಟ ತೃಪ್ತಿಕರವಾಗಿದೆ. ಅತಿ ಸೂಕ್ಷ್ಮ ವ್ಯಕ್ತಿಗಳಿಗೆ ಸ್ವಲ್ಪ ಉಸಿರಾಟದ ತೊಂದರೆ ಆಗಬಹುದು.",
                    "ಆಸ್ತಮಾ ರೋಗಿಗಳು ತಮ್ಮ ಇನ್ಹೇಲರ್ ಅನ್ನು ಹತ್ತಿರ ಇಟ್ಟುಕೊಳ್ಳಿ."),
        "Bengali": ("🟡", "বায়ুর গুণমান সন্তোষজনক। অতি সংবেদনশীল ব্যক্তিদের সামান্য শ্বাসকষ্ট হতে পারে।",
                    "হাঁপানি রোগীরা তাদের ইনহেলার কাছে রাখুন।"),
    },
    "Moderate": {
        "English": ("🟠", "Sensitive groups may feel mild discomfort. Reduce prolonged outdoor exertion if you have breathing issues.",
                    "Children, elderly, and people with asthma/heart conditions: cut outdoor exercise time today."),
        "Hindi": ("🟠", "संवेदनशील समूहों को हल्की परेशानी हो सकती है। सांस की समस्या हो तो बाहरी परिश्रम कम करें।",
                  "बच्चे, बुज़ुर्ग और अस्थमा/हृदय रोगी आज बाहरी व्यायाम कम करें।"),
        "Marathi": ("🟠", "संवेदनशील गटांना थोडा त्रास जाणवू शकतो. श्वसनाचा त्रास असल्यास बाहेरील श्रम कमी करा.",
                    "मुले, वृद्ध आणि दमा/हृदयरोगी आज बाहेरील व्यायाम कमी करा."),
        "Tamil": ("🟠", "உணர்திறன் கொண்ட குழுக்கள் சிறிது அசெளகரியம் உணரலாம். சுவாசப் பிரச்சனை இருந்தால் நீண்ட நேர வெளிப்புற உழைப்பைக் குறைக்கவும்.",
                  "குழந்தைகள், முதியோர், ஆஸ்துமா/இதய நோயாளிகள் இன்று வெளிப்புற உடற்பயிற்சியைக் குறைக்கவும்."),
        "Kannada": ("🟠", "ಸೂಕ್ಷ್ಮ ಗುಂಪುಗಳಿಗೆ ಸ್ವಲ್ಪ ಅಸ್ವಸ್ಥತೆ ಅನುಭವಾಗಬಹುದು. ಉಸಿರಾಟದ ತೊಂದರೆ ಇದ್ದರೆ ದೀರ್ಘಕಾಲ ಹೊರಾಂಗಣ ಶ್ರಮವನ್ನು ಕಡಿಮೆ ಮಾಡಿ.",
                    "ಮಕ್ಕಳು, ವೃದ್ಧರು, ಆಸ್ತಮಾ/ಹೃದಯ ರೋಗಿಗಳು ಇಂದು ಹೊರಾಂಗಣ ವ್ಯಾಯಾಮವನ್ನು ಕಡಿಮೆ ಮಾಡಿ."),
        "Bengali": ("🟠", "সংবেদনশীল গোষ্ঠীর সামান্য অস্বস্তি হতে পারে। শ্বাসকষ্ট থাকলে দীর্ঘ বহিরঙ্গন পরিশ্রম কমান।",
                    "শিশু, বয়স্ক এবং হাঁপানি/হৃদরোগীরা আজ বহিরঙ্গন ব্যায়াম কমান।"),
    },
    "Poor": {
        "English": ("🔴", "Breathing discomfort likely for most people on prolonged outdoor exposure. Limit outdoor activity.",
                    "Sensitive groups should avoid outdoor exertion entirely and wear an N95 mask outdoors."),
        "Hindi": ("🔴", "अधिक समय बाहर रहने पर अधिकांश लोगों को सांस लेने में परेशानी हो सकती है। बाहरी गतिविधि सीमित करें।",
                  "संवेदनशील समूह बाहरी परिश्रम से बचें और N95 मास्क पहनें।"),
        "Marathi": ("🔴", "जास्त वेळ बाहेर राहिल्यास बहुतेकांना श्वसनाचा त्रास होऊ शकतो. बाहेरील क्रियाकलाप मर्यादित करा.",
                    "संवेदनशील गटांनी बाहेरील श्रम टाळावेत आणि N95 मास्क वापरावा."),
        "Tamil": ("🔴", "நீண்ட நேரம் வெளியில் இருந்தால் பெரும்பாலானோருக்கு சுவாசக் கோளாறு ஏற்படலாம். வெளிப்புற செயல்பாட்டைக் குறைக்கவும்.",
                  "உணர்திறன் கொண்ட குழுக்கள் வெளிப்புற உழைப்பை முற்றிலும் தவிர்த்து N95 மாஸ்க் அணியவும்."),
        "Kannada": ("🔴", "ಹೆಚ್ಚು ಸಮಯ ಹೊರಗೆ ಇದ್ದರೆ ಹೆಚ್ಚಿನವರಿಗೆ ಉಸಿರಾಟದ ತೊಂದರೆ ಆಗಬಹುದು. ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಯನ್ನು ಮಿತಿಗೊಳಿಸಿ.",
                    "ಸೂಕ್ಷ್ಮ ಗುಂಪುಗಳು ಹೊರಾಂಗಣ ಶ್ರಮವನ್ನು ಸಂಪೂರ್ಣವಾಗಿ ತಪ್ಪಿಸಿ N95 ಮಾಸ್ಕ್ ಧರಿಸಿ."),
        "Bengali": ("🔴", "দীর্ঘ সময় বাইরে থাকলে বেশিরভাগ মানুষের শ্বাসকষ্ট হতে পারে। বহিরঙ্গন কার্যকলাপ সীমিত করুন।",
                    "সংবেদনশীল গোষ্ঠী বহিরঙ্গন পরিশ্রম সম্পূর্ণ এড়িয়ে চলুন এবং N95 মাস্ক পরুন।"),
    },
    "Very Poor": {
        "English": ("🟣", "Health warning: everyone may experience breathing discomfort on prolonged exposure. Avoid outdoor activity.",
                    "Sensitive groups should stay indoors with air purifiers running; seek medical help if symptoms appear."),
        "Hindi": ("🟣", "स्वास्थ्य चेतावनी: अधिक समय बाहर रहने पर सभी को सांस की समस्या हो सकती है। बाहरी गतिविधि से बचें।",
                  "संवेदनशील समूह घर के अंदर रहें, एयर प्यूरीफायर चलाएं; लक्षण दिखने पर डॉक्टर से मिलें।"),
        "Marathi": ("🟣", "आरोग्य इशारा: जास्त वेळ बाहेर राहिल्यास सर्वांना श्वसनाचा त्रास होऊ शकतो. बाहेरील क्रियाकलाप टाळा.",
                    "संवेदनशील गटांनी घरातच राहावे, एअर प्युरिफायर सुरू ठेवावा; लक्षणे आढळल्यास डॉक्टरांना भेटा."),
        "Tamil": ("🟣", "சுகாதார எச்சரிக்கை: நீண்ட நேரம் வெளியில் இருந்தால் அனைவருக்கும் சுவாசக் கோளாறு ஏற்படலாம். வெளிப்புற செயல்பாட்டைத் தவிர்க்கவும்.",
                  "உணர்திறன் கொண்ட குழுக்கள் காற்று சுத்திகரிப்பியுடன் வீட்டிற்குள் இருக்கவும்; அறிகுறிகள் தென்பட்டால் மருத்துவரை அணுகவும்."),
        "Kannada": ("🟣", "ಆರೋಗ್ಯ ಎಚ್ಚರಿಕೆ: ಹೆಚ್ಚು ಸಮಯ ಹೊರಗೆ ಇದ್ದರೆ ಎಲ್ಲರಿಗೂ ಉಸಿರಾಟದ ತೊಂದರೆ ಆಗಬಹುದು. ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಯನ್ನು ತಪ್ಪಿಸಿ.",
                    "ಸೂಕ್ಷ್ಮ ಗುಂಪುಗಳು ಏರ್ ಪ್ಯೂರಿಫೈಯರ್‌ನೊಂದಿಗೆ ಮನೆಯೊಳಗೆ ಇರಿ; ಲಕ್ಷಣಗಳು ಕಂಡುಬಂದರೆ ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಿ."),
        "Bengali": ("🟣", "স্বাস্থ্য সতর্কতা: দীর্ঘ সময় বাইরে থাকলে সবার শ্বাসকষ্ট হতে পারে। বহিরঙ্গন কার্যকলাপ এড়িয়ে চলুন।",
                    "সংবেদনশীল গোষ্ঠী এয়ার পিউরিফায়ার সহ ঘরের ভিতরে থাকুন; উপসর্গ দেখা দিলে চিকিৎসকের সাহায্য নিন।"),
    },
    "Severe": {
        "English": ("⚫", "Health emergency: air quality affects healthy people and seriously impacts those with existing disease. Stay indoors.",
                    "Sensitive groups: avoid all outdoor exposure. Schools should consider suspending outdoor activities/closure."),
        "Hindi": ("⚫", "स्वास्थ्य आपातकाल: वायु गुणवत्ता स्वस्थ लोगों को भी प्रभावित करती है और बीमार लोगों पर गंभीर असर डालती है। घर के अंदर रहें।",
                  "संवेदनशील समूह बाहर बिल्कुल न निकलें। स्कूलों में बाहरी गतिविधियाँ स्थगित करने पर विचार करें।"),
        "Marathi": ("⚫", "आरोग्य आणीबाणी: हवेच्या गुणवत्तेचा निरोगी लोकांवरही परिणाम होतो आणि आजारी व्यक्तींवर गंभीर परिणाम होतो. घरातच रहा.",
                    "संवेदनशील गटांनी अजिबात बाहेर पडू नये. शाळांनी बाहेरील उपक्रम स्थगित करण्याचा विचार करावा."),
        "Tamil": ("⚫", "சுகாதார அவசரநிலை: காற்றின் தரம் ஆரோக்கியமானவர்களையும் பாதிக்கிறது, ஏற்கனவே நோய் உள்ளவர்களை கடுமையாக பாதிக்கிறது. வீட்டிற்குள் இருக்கவும்.",
                  "உணர்திறன் கொண்ட குழுக்கள்: எந்த வெளிப்புற வெளிப்பாட்டையும் தவிர்க்கவும். பள்ளிகள் வெளிப்புற செயல்பாடுகளை நிறுத்த வேண்டும்."),
        "Kannada": ("⚫", "ಆರೋಗ್ಯ ತುರ್ತುಸ್ಥಿತಿ: ಗಾಳಿಯ ಗುಣಮಟ್ಟ ಆರೋಗ್ಯವಂತರ ಮೇಲೂ ಪರಿಣಾಮ ಬೀರುತ್ತದೆ ಮತ್ತು ಈಗಾಗಲೇ ಅನಾರೋಗ್ಯ ಇರುವವರ ಮೇಲೆ ಗಂಭೀರ ಪರಿಣಾಮ ಬೀರುತ್ತದೆ. ಮನೆಯೊಳಗೆ ಇರಿ.",
                    "ಸೂಕ್ಷ್ಮ ಗುಂಪುಗಳು: ಎಲ್ಲಾ ಹೊರಾಂಗಣ ಒಡ್ಡಿಕೊಳ್ಳುವಿಕೆಯನ್ನು ತಪ್ಪಿಸಿ. ಶಾಲೆಗಳು ಹೊರಾಂಗಣ ಚಟುವಟಿಕೆಗಳನ್ನು ಸ್ಥಗಿತಗೊಳಿಸುವುದನ್ನು ಪರಿಗಣಿಸಬೇಕು."),
        "Bengali": ("⚫", "স্বাস্থ্য জরুরি অবস্থা: বায়ুর গুণমান সুস্থ মানুষদেরও প্রভাবিত করে এবং বিদ্যমান রোগে আক্রান্তদের গুরুতরভাবে প্রভাবিত করে। ঘরের ভিতরে থাকুন।",
                    "সংবেদনশীল গোষ্ঠী: সমস্ত বহিরঙ্গন সংস্পর্শ এড়িয়ে চলুন। স্কুলগুলির বহিরঙ্গন কার্যক্রম স্থগিত করা বিবেচনা করা উচিত।"),
    },
}

SUPPORTED_LANGUAGES = ["English", "Hindi", "Marathi", "Tamil", "Kannada", "Bengali"]


class CitizenAdvisoryAgent(BaseAgent):
    name = "citizen_advisory_agent"

    def run(self, city: str, aqi: float, languages=None) -> AgentMessage:
        try:
            languages = languages or SUPPORTED_LANGUAGES
            meta = get_aqi_meta(aqi)
            band = meta["label"]
            band_text = _ADVISORY_TEXT.get(band, _ADVISORY_TEXT["Moderate"])

            advisories = {}
            for lang in languages:
                icon, general_msg, sensitive_msg = band_text.get(lang, band_text["English"])
                advisories[lang] = {
                    "icon": icon,
                    "general_public": general_msg,
                    "sensitive_groups": sensitive_msg,
                }

            return self._ok(city, {
                "aqi": round(float(aqi), 1),
                "category": band,
                "category_color": meta["color"],
                "languages": advisories,
                "channels": ["Mobile App", "SMS", "Public Display Boards", "Radio"],
            })
        except Exception as exc:
            return self._error(city, str(exc))
