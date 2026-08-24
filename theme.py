"""
theme.py — the app's colours, in one place, so every page (and every
matplotlib chart) matches.

Match .streamlit/config.toml if you change these — that file controls
Streamlit's own widgets (buttons, sliders); this file controls
everything we draw ourselves (matplotlib charts, score badges).
"""
from matplotlib.colors import LinearSegmentedColormap

GREEN = "#1E8E5A"
BLUE = "#2563EB"
GRAY = "#94A3B8"
LIGHT_BLUE = "#EAF2F8"

# A blue-to-green gradient, used for every chart that shows a score:
# low scores lean blue, high scores lean green.
CMAP = LinearSegmentedColormap.from_list("app_theme", [BLUE, GREEN])


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
        f'font-size:0.9rem;">{text}</span>'
    )
