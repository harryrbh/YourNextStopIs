"""
labels.py — plain-English names for every column, so nothing shown on
screen is a raw database/code name like `cost_score` or
`avg_temperature_c`. Also handles rounding (so users see "72" and
"18.4°C", never "71.83333333") and country flag emoji.

Use `friendly(df)` right before displaying a DataFrame (in a table, a
chart, a download button) — never rename columns this way earlier in
the pipeline, or the rest of the code has to work with the renamed
(and less predictable) versions.
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
    "heritage_sites": "Heritage Sites",
    "attractions": "Attractions",
    "top_attraction": "Top Attraction",
    "gdp_per_capita": "GDP per Person",
    "tourist_arrivals": "Yearly Visitors",
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
    ('🇫🇷'). Works by shifting each letter into the Unicode "regional
    indicator symbol" range — no image file or lookup table needed.
    Renders as a real flag on most systems; a couple of older/Windows
    setups show the two letters instead, which still reads fine.
    """
    if not isinstance(iso2, str) or len(iso2) != 2:
        return ""
    return "".join(chr(0x1F1E6 + ord(c.upper()) - ord("A")) for c in iso2)

