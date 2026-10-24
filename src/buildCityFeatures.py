import networkx as nx
import numpy as np
import pandas as pd
from geopy.distance import geodesic

from database import getEngine

# How much each score counts towards the final overall_score
weights = {
    "weather_score": 0.30,
    "accessibility_score": 0.25,
    "culture_score": 0.20,
    "cost_score": 0.15,
    "tourism_score": 0.10,
}


# HOW RAW NUMBERS BECOME 0-100 SCORES
defaultClipPercent = 5
defaultUseLogScale = True


def normaliseToScore(series: pd.Series, invert: bool = False, useLogScale: bool = False, clipPercent: float = 0) -> pd.Series:
    """Rescale any column so the lowest value becomes 0 and the highest becomes 100."""
    values = series.astype(float)
    if useLogScale:
        values = np.log1p(values.clip(lower=0))
    if clipPercent > 0 and values.notna().sum() > 2:
        lowerBound, upperBound = values.quantile(clipPercent / 100), values.quantile(1 - clipPercent / 100)
        if upperBound > lowerBound:
            values = values.clip(lower=lowerBound, upper=upperBound)
    if values.notna().sum() == 0:
        return pd.Series(50.0, index=values.index)  # No information at all -> neutral score
    if values.max() == values.min():
        return pd.Series(50.0, index=values.index)  # Everyone's equal -> neutral score
    scaled = (values - values.min()) / (values.max() - values.min()) * 100
    scaled = scaled.fillna(50.0)  # Individual missing values also become neutral
    return 100 - scaled if invert else scaled


def computeConnectivity(engine) -> pd.DataFrame:
    """Model the airport route network as a graph and measure how 'central' each city's airport(s) are."""
    routes = pd.read_sql("SELECT source_airport_id, destination_airport_id FROM routes", engine)
    airports = pd.read_sql("SELECT airport_id, city_id FROM airports", engine)

    graph = nx.DiGraph()
    graph.add_edges_from(routes.itertuples(index=False, name=None))
    centrality = nx.degree_centrality(graph)  # 0-1, higher = more connected

    airports["centrality"] = airports["airport_id"].map(centrality).fillna(0)
    return airports.groupby("city_id")["centrality"].sum().reset_index(name="connectivity")


def nearestAirport(cities: pd.DataFrame, airports: pd.DataFrame) -> pd.DataFrame:
    """For every city, find the closest real airport BY DISTANCE."""
    airports = airports.dropna(subset=["latitude", "longitude"])

    nearestAirports = []
    for _, city in cities.iterrows():
        bestName, bestKm = None, None
        for _, airport in airports.iterrows():
            distanceKm = geodesic(
                (city["latitude"], city["longitude"]), (airport["latitude"], airport["longitude"])
            ).km
            if bestKm is None or distanceKm < bestKm:
                bestKm, bestName = distanceKm, airport["name"]
        nearestAirports.append({"city_id": city["city_id"], "nearest_airport_name": bestName, "nearest_airport_km": bestKm})
    return pd.DataFrame(nearestAirports)


def addTourismHistory(tourism: pd.DataFrame) -> pd.DataFrame:
    tourism = tourism.copy()
    if "tourism_growth_pct" not in tourism.columns:
        tourism["tourism_growth_pct"] = 0.0
    tourism["tourism_growth_pct"] = tourism["tourism_growth_pct"].fillna(0.0)
    tourism["previous_arrivals"] = tourism["arrivals"] / (1 + tourism["tourism_growth_pct"] / 100)
    return tourism


def build():
    engine = getEngine()

    cities = pd.read_sql("SELECT * FROM cities", engine)
    weather = pd.read_sql("SELECT * FROM weather", engine)
    airports = pd.read_sql("SELECT * FROM airports", engine)
    routes = pd.read_sql("SELECT * FROM routes", engine)
    countries = pd.read_sql("SELECT * FROM countries", engine)
    tourism = pd.read_sql("SELECT * FROM tourism", engine)
    connectivity = computeConnectivity(engine)
    nearest = nearestAirport(cities, airports)
    tourism = addTourismHistory(tourism)

    weatherAverage = weather.groupby("city_id").agg(
        avg_temperature_c=("temperature_c", "mean"),
        avg_precipitation_mm=("precipitation_mm", "mean"),
    ).reset_index()

    airportCounts = airports.groupby("city_id").size().reset_index(name="airport_count")
    routeCounts = (
        airports.merge(routes, left_on="airport_id", right_on="source_airport_id")
        .groupby("city_id").size().reset_index(name="route_count")
    )

    # Assemble everything into one table, one row per city
    cityTable = cities.merge(weatherAverage, on="city_id", how="left")
    cityTable = cityTable.merge(airportCounts, on="city_id", how="left")
    cityTable = cityTable.merge(routeCounts, on="city_id", how="left")
    cityTable = cityTable.merge(connectivity, on="city_id", how="left")
    cityTable = cityTable.merge(nearest, on="city_id", how="left")
    cityTable = cityTable.merge(countries[["country_id", "gdp_per_capita", "urban_population_pct"]], on="country_id", how="left")

    tourismByCountry = tourism.groupby("country_id").agg(
        arrivals=("arrivals", "mean"),
        previous_arrivals=("previous_arrivals", "mean"),
        tourism_growth_pct=("tourism_growth_pct", "mean"),
    ).reset_index()
    cityTable = cityTable.merge(tourismByCountry, on="country_id", how="left")

    for columnName in ["airport_count", "route_count", "connectivity", "arrivals", "previous_arrivals", "tourism_growth_pct"]:
        cityTable[columnName] = cityTable[columnName].fillna(0)

    # Weather comfort: closest to 22C with lower rainfall scores higher
    cityTable["weather_comfort"] = 100 - (abs(cityTable["avg_temperature_c"] - 22) * 4 + cityTable["avg_precipitation_mm"] / 20)
    cityTable["weather_comfort"] = cityTable["weather_comfort"].clip(lower=0)

    # Normalise every raw number to a 0-100 score
    cityTable["weather_score"] = normaliseToScore(cityTable["weather_comfort"], clipPercent=defaultClipPercent)  # Already roughly bell-shaped: no log
    cityTable["accessibility_score"] = normaliseToScore(
        cityTable["airport_count"] * 2 + cityTable["route_count"] * 0.1 + cityTable["connectivity"] * 100, useLogScale=defaultUseLogScale, clipPercent=defaultClipPercent
    )
    cityTable["culture_score"] = normaliseToScore(cityTable["heritage_sites"] * 3 + cityTable["attractions"] / 20, useLogScale=defaultUseLogScale, clipPercent=defaultClipPercent)
    cityTable["cost_score"] = normaliseToScore(cityTable["gdp_per_capita"].fillna(cityTable["gdp_per_capita"].median()), invert=True, useLogScale=defaultUseLogScale, clipPercent=defaultClipPercent)
    cityTable["tourism_score"] = normaliseToScore(cityTable["arrivals"], useLogScale=defaultUseLogScale, clipPercent=defaultClipPercent)

    # The transparent baseline: a weighted average, nothing hidden
    cityTable["overall_score"] = sum(cityTable[columnName] * weight for columnName, weight in weights.items())

    featureTable = cityTable[[
        "city_id", "avg_temperature_c", "avg_precipitation_mm", "airport_count",
        "route_count", "connectivity", "heritage_sites", "attractions",
        "gdp_per_capita", "urban_population_pct", "arrivals", "previous_arrivals",
        "tourism_growth_pct", "nearest_airport_name", "nearest_airport_km",
        "weather_score", "accessibility_score", "culture_score", "cost_score",
        "tourism_score", "overall_score",
    ]].rename(columns={"arrivals": "tourist_arrivals"})

    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM city_features")
        featureTable.to_sql("city_features", conn, if_exists="append", index=False)

    print(f"Built features for {len(featureTable)} cities.")


if __name__ == "__main__":
    build()
