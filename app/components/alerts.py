import streamlit as st


def alert_row(icon, title, meta, delay=0.0):
    st.markdown(
        f"""
        <div class="alert-row" style="animation-delay:{delay}s;">
          <div class="alert-icon">{icon}</div>
          <div>
            <div class="alert-title">{title}</div>
            <div class="alert-meta">{meta}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def glass_card_open(title=None, icon=""):
    if title:
        st.markdown(
            f'<div class="section-title"><span class="bar"></span>{icon} {title}</div>',
            unsafe_allow_html=True,
        )
