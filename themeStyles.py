"""The app's colours, in one place, so every page (and every chart) matches."""
import streamlit as st

greenColor = "#1E8E5A"
greenDark = "#166B45"
blueColor = "#2563EB"
blueDark = "#1D4ED8"
grayColor = "#94A3B8"
amber = "#F59E0B"
purple = "#8B5CF6"

pageTint = "#F4F9F7"  # Main background: faint green tint
cardTint = "#EEF5FB"  # Cards/metrics/chips: faint blue tint

colorscale = [[0.0, blueColor], [0.5, "#4F9E86"], [1.0, greenColor]]

palette = [greenColor, blueColor, amber, purple, grayColor]


def scoreColor(score: float) -> str:
    if score >= 70:
        return greenColor
    if score >= 40:
        return blueColor
    return grayColor


def scoreBadgeHtml(score: float, label: str = "") -> str:
    """A small rounded, coloured badge."""
    color = scoreColor(score)
    text = f"{score:.0f}{label}"
    return (
        f'<span style="background-color:{color}; color:white; '
        f'padding:3px 10px; border-radius:12px; font-weight:600; '
        f'font-size:0.9rem; white-space:nowrap;">{text}</span>'
    )


def injectCss():
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {pageTint};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {cardTint};
        }}
        h1, h2, h3 {{
            border-bottom: 3px solid {greenColor};
            padding-bottom: 6px;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{
            border-radius: 14px;
            background-color: white;
        }}
        div[data-testid="stMetric"] {{
            background-color: {cardTint};
            padding: 12px 16px;
            border-radius: 10px;
            border-left: 4px solid {greenColor};
        }}
        .city-card-title {{
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 2px;
        }}
        .city-card-subtitle {{
            color: #64748B;
            font-size: 0.9rem;
            margin-bottom: 8px;
        }}
        .stat-chip {{
            display: inline-block;
            background-color: {cardTint};
            border: 1px solid #D6E6F5;
            border-radius: 8px;
            padding: 2px 9px;
            margin: 2px 4px 2px 0;
            font-size: 0.85rem;
            color: #1B4B6E;
        }}
        .stButton > button, .stDownloadButton > button {{
            border-color: {greenColor};
            color: {greenDark};
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            border-color: {greenDark};
            color: white;
            background-color: {greenColor};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
