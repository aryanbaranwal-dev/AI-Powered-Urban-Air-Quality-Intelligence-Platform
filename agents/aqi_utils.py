"""
Pure-Python AQI helpers with NO Streamlit / UI dependency, so every agent
in this package can be imported and run standalone (CLI, tests, or as a
microservice) without needing the dashboard installed.
"""
from app.config import AQI_BANDS


def get_aqi_meta(aqi: float) -> dict:
    if aqi is None:
        aqi = 0
    for lo, hi, label, color in AQI_BANDS:
        if lo <= aqi <= hi:
            return {"label": label, "color": color, "band": (lo, hi)}
    lo, hi, label, color = AQI_BANDS[-1]
    return {"label": label, "color": color, "band": (lo, hi)}
