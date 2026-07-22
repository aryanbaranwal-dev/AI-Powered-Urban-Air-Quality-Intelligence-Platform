import streamlit.components.v1 as components

from app.theme import get_theme


def live_clock_html(height: int = 46):
    """A tiny self-contained HTML/JS widget that ticks the current
    date + time client-side, independent of Streamlit reruns.

    Rendered via components.html, i.e. inside its own iframe -- it can't
    see our page-level CSS variables, so the active theme's colors are
    passed in directly to keep it in sync with the rest of the app.
    """
    t = get_theme()
    pill_bg = t["fill1"]
    pill_border = t["border"]
    label_color = t["text3"]
    value_color = t["text1"]
    success = t["success"]

    components.html(
        f"""
        <style>
          html, body {{ background:transparent !important; margin:0; padding:0; }}
        </style>
        <div style="font-family:Inter,sans-serif; display:flex; gap:16px; background:transparent;">
          <div style="display:flex;align-items:center;gap:8px;padding:8px 14px;border-radius:12px;
                      background:{pill_bg}; border:1px solid {pill_border};
                      font-size:12.5px; color:{label_color}; white-space:nowrap;">
            <span>📅</span><b id="dt" style="color:{value_color};font-weight:600;">--</b>
          </div>
          <div style="display:flex;align-items:center;gap:8px;padding:8px 14px;border-radius:12px;
                      background:{pill_bg}; border:1px solid {pill_border};
                      font-size:12.5px; color:{label_color}; white-space:nowrap;">
            <span style="width:7px;height:7px;border-radius:50%;background:{success};display:inline-block;
                         box-shadow:0 0 8px {success};"></span>
            <b id="tm" style="color:{value_color};font-weight:600;">--</b>
          </div>
        </div>
        <script>
          function tick(){{
            const now = new Date();
            const dOpts = {{ weekday:'short', year:'numeric', month:'short', day:'numeric' }};
            const tOpts = {{ hour:'2-digit', minute:'2-digit', second:'2-digit' }};
            document.getElementById('dt').innerText = now.toLocaleDateString(undefined, dOpts);
            document.getElementById('tm').innerText = now.toLocaleTimeString(undefined, tOpts);
          }}
          tick();
          setInterval(tick, 1000);
        </script>
        """,
        height=height,
    )
