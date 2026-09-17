"""
labels.py — plain-English names for every column, so nothing shown on
screen is a raw database/code name like `cost_score` or
`avg_temperature_c`. Also handles rounding (so users see "72" and
"18.4°C", never "71.83333333") and country flags.

Use `friendly(df)` right before displaying a DataFrame (in a table, a
chart, a download button) — never rename columns this way earlier in
the pipeline, or the rest of the code has to work with the renamed
(and less predictable) versions.

A note on flags: emoji flags (built from Unicode "regional indicator"
characters) depend entirely on the browser/operating system having a
font that renders them as flags — some systems instead show the raw
two-letter code or a blank box. That isn't something this app's code
can fix directly, so for anywhere the flag needs to reliably show up
(city cards, headings), we use a real flag ICON IMAGE instead, from
flagcdn.com (a free, keyless flag-icon service) — see
`flag_image_html()`. The plain emoji character (`flag_emoji()`) is
kept for places an image can't go, like a CSV export or dataframe
cell.
"""
import pandas as pd

FRIENDLY_NAMES = {
    "city_name": "City",
    "country_name": "Country",
    "region": "Region",
    "population": "Population",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "overall_score": "Overall Score",
    "weather_score": "Weather",
    "accessibility_score": "Ease of Travel",
    "culture_score": "Culture & Sights",
    "cost_score": "Affordability",
    "tourism_score": "Popularity",
    "avg_temperature_c": "Avg. Temperature (°C)",
    "avg_precipitation_mm": "Avg. Rainfall (mm)",
    "airport_count": "Airports Nearby",
    "route_count": "Flight Routes",
    "connectivity": "Flight Network Score",
    "nearest_airport_name": "Nearest Airport",
    "nearest_airport_km": "Distance to Nearest Airport (km)",
    "heritage_sites": "Heritage Sites",
    "attractions": "Attractions",
    "attraction_1": "Top Attraction",
    "attraction_2": "2nd Attraction",
    "attraction_3": "3rd Attraction",
    "gdp_per_capita": "GDP per Person",
    "urban_population_pct": "Urban Population (%)",
    "tourist_arrivals": "Yearly Visitors",
    "previous_arrivals": "Previous Year's Visitors",
    "tourism_growth_pct": "Visitor Growth (%)",
    "category": "Travel Style",
    "similarity": "Match",
    "distance_km": "Distance (km)",
}

# Short, plain-English names for the five 0-100 scores — reused
# wherever we list just the scores (radar charts, sliders, etc.)
SCORE_LABELS = {
    "weather_score": "Weather",
    "accessibility_score": "Ease of Travel",
    "culture_score": "Culture & Sights",
    "cost_score": "Affordability",
    "tourism_score": "Popularity",
}

# How many decimal places each column should show, by column name.
# Anything not listed defaults to 0 decimal places — whole numbers
# are almost always easier for a user to scan than "71.83333333".
DECIMAL_PLACES = {
    "avg_temperature_c": 1,
    "latitude": 2,
    "longitude": 2,
    "similarity": 0,
    "urban_population_pct": 0,
    "tourism_growth_pct": 1,
}


def round_for_display(df: pd.DataFrame) -> pd.DataFrame:
    """Round every numeric column to a sensible number of decimal
    places for showing to a user."""
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_float_dtype(df[col]):
            df[col] = df[col].round(DECIMAL_PLACES.get(col, 0))
    return df


def friendly(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df, rounded and with every recognised column
    renamed to a plain-English label. Unrecognised columns are left
    as-is (rounded, but with their original name)."""
    return round_for_display(df).rename(columns=FRIENDLY_NAMES)


def flag_emoji(iso2: str) -> str:
    """Turn a two-letter country code ('FR') into its flag emoji
    character ('🇫🇷'), for contexts that only accept plain text (a
    dataframe cell, a CSV). See the module docstring for why the
    visual card display uses flag_image_html() instead.
    """
    if not isinstance(iso2, str) or len(iso2) != 2:
        return ""
    return "".join(chr(0x1F1E6 + ord(c.upper()) - ord("A")) for c in iso2)


def flag_image_html(iso2: str, height: int = 16) -> str:
    """A real flag icon (an <img> tag), which renders reliably in
    every browser regardless of emoji font support. Source:
    flagcdn.com — free, no key required. Pass into
    st.markdown(..., unsafe_allow_html=True).
    """
    if not isinstance(iso2, str) or len(iso2) != 2:
        return ""
    code = iso2.lower()
    return (
        f'<img src="https://flagcdn.com/{code}.svg" alt="{iso2}" '
        f'height="{height}" style="vertical-align:middle; border-radius:2px; '
        f'box-shadow: 0 0 1px rgba(0,0,0,0.3);">'
    )
