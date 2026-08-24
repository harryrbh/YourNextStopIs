"""
labels.py — plain-English names for every column, so nothing shown on
screen is a raw database/code name like `cost_score` or
`avg_temperature_c`.

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
    "gdp_per_capita": "GDP per Person",
    "tourist_arrivals": "Yearly Visitors",
    "cluster": "Travel Style Group",
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


def friendly(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with every recognised column renamed to a
    plain-English label. Unrecognised columns are left as-is."""
    return df.rename(columns=FRIENDLY_NAMES)
