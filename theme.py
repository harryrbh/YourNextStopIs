"""
theme.py — the app's colours, in one place, so every page (and every
chart) matches.

Match .streamlit/config.toml if you change these — that file controls
Streamlit's own widgets (buttons, sliders); this file controls
everything we draw ourselves (Plotly charts, score badges, cards).
"""
import streamlit as st

GREEN = "#1E8E5A"
GREEN_DARK = "#166B45"
BLUE = "#2563EB"
BLUE_DARK = "#1D4ED8"
GRAY = "#94A3B8"
AMBER = "#F59E0B"
PURPLE = "#8B5CF6"

# Backgrounds — a very slight green/blue wash rather than flat white,
# so the app doesn't look like an unstyled default. Match these to
# .streamlit/config.toml's backgroundColor/secondaryBackgroundColor.
PAGE_TINT = "#F4F9F7"       # main background: faint green tint
CARD_TINT = "#EEF5FB"       # cards/metrics/chips: faint blue tint

# A blue-to-green gradient, used for every chart that shows a score:
# low scores lean blue, high scores lean green. Plotly wants a list
# of [position, colour] pairs, position from 0 to 1.
COLORSCALE = [[0.0, BLUE], [0.5, "#4F9E86"], [1.0, GREEN]]

# A handful of distinct colours for comparing several cities at once
# (radar charts, multi-city bar charts).
PALETTE = [GREEN, BLUE, AMBER, PURPLE, GRAY]


def score_color(score: float) -> str:
    """One colour per score, for badges and highlights: green for a
    strong score, blue for a middling one, gray for a weak one."""
    if score >= 70:
        return GREEN
    if score >= 40:
        return BLUE
    return GRAY


def score_badge_html(score: float, label: str = "") -> str:
    """A small rounded, coloured badge — e.g. "82/100" in green.
    Pass into st.markdown(..., unsafe_allow_html=True)."""
    color = score_color(score)
    text = f"{score:.0f}{label}"
    return (
        f'<span style="background-color:{color}; color:white; '
        f'padding:3px 10px; border-radius:12px; font-weight:600; '
        f'font-size:0.9rem; white-space:nowrap;">{text}</span>'
    )


def inject_css():
    """A small amount of shared CSS for a more polished, less
    'default Streamlit' look: a subtle green/blue background tint,
    a coloured accent bar under headings, rounded card corners,
    coloured stat chips. Call once near the top of every page.
    """
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {PAGE_TINT};
        }}
        section[data-testid="stSidebar"] {{
            background-color: {CARD_TINT};
        }}
        h1, h2, h3 {{
            border-bottom: 3px solid {GREEN};
            padding-bottom: 6px;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"] > div {{
            border-radius: 14px;
            background-color: white;
        }}
        div[data-testid="stMetric"] {{
            background-color: {CARD_TINT};
            padding: 12px 16px;
            border-radius: 10px;
            border-left: 4px solid {GREEN};
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
            background-color: {CARD_TINT};
            border: 1px solid #D6E6F5;
            border-radius: 8px;
            padding: 2px 9px;
            margin: 2px 4px 2px 0;
            font-size: 0.85rem;
            color: #1B4B6E;
        }}
        .stButton > button, .stDownloadButton > button {{
            border-color: {GREEN};
            color: {GREEN_DARK};
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            border-color: {GREEN_DARK};
            color: white;
            background-color: {GREEN};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
