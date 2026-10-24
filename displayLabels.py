import pandas as pd

friendlyNames = {
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
    "price_tier": "Price Tier",
    "similarity": "Match",
    "distance_km": "Distance (km)",
}

# Short, plain-English names for the five 0-100 scores
scoreLabels = {
    "weather_score": "Weather",
    "accessibility_score": "Ease of Travel",
    "culture_score": "Culture & Sights",
    "cost_score": "Affordability",
    "tourism_score": "Popularity",
}

# How many decimal places each column should show, by column name
decimalPlaces = {
    "avg_temperature_c": 1,
    "latitude": 2,
    "longitude": 2,
    "similarity": 0,
    "urban_population_pct": 0,
    "tourism_growth_pct": 1,
}


def roundForDisplay(dataFrame: pd.DataFrame) -> pd.DataFrame:
    """Round every numeric column to a sensible number of decimal places for showing to a user."""
    dataFrame = dataFrame.copy()
    for columnName in dataFrame.columns:
        if pd.api.types.is_float_dtype(dataFrame[columnName]):
            dataFrame[columnName] = dataFrame[columnName].round(decimalPlaces.get(columnName, 0))
    return dataFrame


def friendly(dataFrame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df, rounded and with every recognised column renamed to a plain-English label."""
    return roundForDisplay(dataFrame).rename(columns=friendlyNames)


def flagEmoji(countryCode: str) -> str:
    if not isinstance(countryCode, str) or len(countryCode) != 2:
        return ""
    return "".join(chr(0x1F1E6 + ord(letter.upper()) - ord("A")) for letter in countryCode)


def flagImageHtml(countryCode: str, height: int = 16) -> str:
    """A real flag icon (an <img> tag), which renders reliably in every browser regardless of emoji font support."""
    if not isinstance(countryCode, str) or len(countryCode) != 2:
        return ""
    code = countryCode.lower()
    return (
        f'<img src="https://flagcdn.com/{code}.svg" alt="{countryCode}" '
        f'height="{height}" style="vertical-align:middle; border-radius:2px; '
        f'box-shadow: 0 0 1px rgba(0,0,0,0.3);">'
    )
