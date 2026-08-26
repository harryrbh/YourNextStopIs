"""
theme.py — the app's colours, in one place, so every page (and every
chart) matches.

Match .streamlit/config.toml if you change these — that file controls
Streamlit's own widgets (buttons, sliders); this file controls
everything we draw ourselves (Plotly charts, score badges, cards).
"""
import streamlit as st

GREEN = "#1E8E5A"
BLUE = "#2563EB"
GRAY = "#94A3B8"
LIGHT_BLUE = "#EAF2F8"
AMBER = "#F59E0B"
PURPLE = "#8B5CF6"

# A blue-to-green gradient, used for every chart that shows a score:
# low scores lean blue, high scores lean green. Plotly wants a list
# of [position, colour] pairs, position from 0 to 1.
COLORSCALE = [[0.0, BLUE], [1.0, GREEN]]

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
    'default Streamlit' look: rounded card corners, subtle shadows,
    tighter spacing. Call once near the top of every page.
    """
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            border-radius: 14px;
        }
        div[data-testid="stMetric"] {
            background-color: #F7FAFC;
            padding: 12px 16px;
            border-radius: 10px;
        }
        .city-card-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 2px;
        }
        .city-card-subtitle {
            color: #64748B;
            font-size: 0.9rem;
            margin-bottom: 8px;
        }
        .stat-chip {
            display: inline-block;
            background-color: #F1F5F9;
            border-radius: 8px;
            padding: 2px 9px;
            margin: 2px 4px 2px 0;
            font-size: 0.85rem;
            color: #334155;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

