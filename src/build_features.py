"""
build_features.py — turns the raw tables into one row per city with
every score the app needs, saved into city_features.

Five feature "groups", each computed with plain pandas:
    1. weather      -> weather_score
    2. accessibility -> accessibility_score  (uses NetworkX — see below)
    3. culture       -> culture_score
    4. cost          -> cost_score
    5. tourism       -> tourism_score

Then one transparent line combines them into overall_score.

Run it with:
    python src/build_features.py
"""
import networkx as nx
import pandas as pd

from db import get_engine

# How much each score counts towards the final overall_score.
# Change these numbers to change what the recommender prioritises.
WEIGHTS = {
    "weather_score": 0.30,
    "accessibility_score": 0.25,
    "culture_score": 0.20,
    "cost_score": 0.15,
    "tourism_score": 0.10,
}


def normalise_0_100(series: pd.Series, invert: bool = False) -> pd.Series:
    """Rescale any column so the lowest value becomes 0 and the
    highest becomes 100. `invert=True` for columns where *lower* is
    better (like cost), so the resulting score still means 'better'.
    """
    s = series.astype(float)
    if s.max() == s.min():
        return pd.Series(50.0, index=s.index)  # everyone's equal -> neutral score
    scaled = (s - s.min()) / (s.max() - s.min()) * 100
    return 100 - scaled if invert else scaled


def compute_connectivity(engine) -> pd.DataFrame:
    """Model the airport route network as a graph and measure how
    'central' each city's airport(s) are. This is the one bit of
    network science in the project — everything else here is just
    pandas — because airport connectivity genuinely is a network
    problem: a city with one route to a huge hub can be more
    accessible than a city with five routes to nowhere.
    """
    routes = pd.read_sql("SELECT source_airport_id, destination_airport_id FROM routes", engine)
    airports = pd.read_sql("SELECT airport_id, city_id FROM airports", engine)

    graph = nx.DiGraph()
    graph.add_edges_from(routes.itertuples(index=False, name=None))
    centrality = nx.degree_centrality(graph)  # 0-1, higher = more connected

    airports["centrality"] = airports["airport_id"].map(centrality).fillna(0)
    return airports.groupby("city_id")["centrality"].sum().reset_index(name="connectivity")


def build():
    engine = get_engine()

    cities = pd.read_sql("SELECT * FROM cities", engine)
    weather = pd.read_sql("SELECT * FROM weather", engine)
    airports = pd.read_sql("SELECT * FROM airports", engine)
    routes = pd.read_sql("SELECT * FROM routes", engine)
    countries = pd.read_sql("SELECT * FROM countries", engine)
    tourism = pd.read_sql("SELECT * FROM tourism", engine)
    connectivity = compute_connectivity(engine)

    # --- 1. weather: average temperature/rain across all 12 months ---
    weather_avg = weather.groupby("city_id").agg(
        avg_temperature_c=("temperature_c", "mean"),
        avg_precipitation_mm=("precipitation_mm", "mean"),
    ).reset_index()

    # --- 2. accessibility: airports + routes + network connectivity ---
    airport_counts = airports.groupby("city_id").size().reset_index(name="airport_count")
    route_counts = (
        airports.merge(routes, left_on="airport_id", right_on="source_airport_id")
        .groupby("city_id").size().reset_index(name="route_count")
    )

    # --- assemble everything into one table, one row per city ---
    df = cities.merge(weather_avg, on="city_id", how="left")
    df = df.merge(airport_counts, on="city_id", how="left")
    df = df.merge(route_counts, on="city_id", how="left")
    df = df.merge(connectivity, on="city_id", how="left")
    df = df.merge(countries[["country_id", "gdp_per_capita"]], on="country_id", how="left")

    tourism_by_country = tourism.groupby("country_id")["arrivals"].mean().reset_index()
    df = df.merge(tourism_by_country, left_on="country_id", right_on="country_id", how="left")

    for col in ["airport_count", "route_count", "connectivity", "arrivals"]:
        df[col] = df[col].fillna(0)

    # weather comfort: closest to 22C with lower rainfall scores higher
    df["weather_comfort"] = 100 - (abs(df["avg_temperature_c"] - 22) * 4 + df["avg_precipitation_mm"] / 20)
    df["weather_comfort"] = df["weather_comfort"].clip(lower=0)

    # --- normalise every raw number to a 0-100 score ---
    df["weather_score"] = normalise_0_100(df["weather_comfort"])
    df["accessibility_score"] = normalise_0_100(
        df["airport_count"] * 2 + df["route_count"] * 0.1 + df["connectivity"] * 100
    )
    df["culture_score"] = normalise_0_100(df["heritage_sites"] * 3 + df["attractions"] / 20)
    df["cost_score"] = normalise_0_100(df["gdp_per_capita"].fillna(df["gdp_per_capita"].median()), invert=True)
    df["tourism_score"] = normalise_0_100(df["arrivals"])

    # --- the transparent baseline: a weighted average, nothing hidden ---
    df["overall_score"] = sum(df[col] * weight for col, weight in WEIGHTS.items())

    out = df[[
        "city_id", "avg_temperature_c", "avg_precipitation_mm", "airport_count",
        "route_count", "connectivity", "heritage_sites", "attractions",
        "gdp_per_capita", "arrivals", "weather_score", "accessibility_score",
        "culture_score", "cost_score", "tourism_score", "overall_score",
    ]].rename(columns={"arrivals": "tourist_arrivals"})

    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM city_features")
        out.to_sql("city_features", conn, if_exists="append", index=False)

    print(f"Built features for {len(out)} cities.")


if __name__ == "__main__":
    build()
