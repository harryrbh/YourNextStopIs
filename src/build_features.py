"""
build_features.py — turns the raw tables into one row per city with
every score, and every extra fact (nearest airport, previous year's
visitor numbers...), saved into city_features.

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
import numpy as np
import pandas as pd
from geopy.distance import geodesic

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


# HOW RAW NUMBERS BECOME 0-100 SCORES — change these to make scores more/less generous.
#   CLIP_PERCENT : values below the Nth percentile score 0, above the (100-N)th score 100.
#                  Without this ONE outlier (a mega-hub airport, Paris's sight count, a
#                  country with 80M visitors) is the "100" and everyone else is squashed
#                  towards 0. 0 = plain min-max (the old behaviour).
#   LOG_SCALE    : take log(1 + x) first for counts/money that are hugely right-skewed, so
#                  "10x more routes" is worth the same step at the bottom as at the top.
CLIP_PERCENT = 5
LOG_SCALE = True


def normalise_0_100(series: pd.Series, invert: bool = False, log: bool = False, clip_percent: float = 0) -> pd.Series:
    """Rescale any column so the lowest value becomes 0 and the
    highest becomes 100. `invert=True` for columns where *lower* is
    better (like cost), so the resulting score still means 'better'.

    Missing values become a neutral 50 rather than staying blank —
    important because if a whole column happens to be missing (e.g.
    you've run fetch_countries.py but not fetch_tourism.py yet, so
    every gdp_per_capita is empty), a plain min-max scale would
    divide 0 by 0 and turn EVERY city's score into NaN, which then
    breaks every downstream model (clustering, classification,
    recommendations) rather than just one column looking bland.
    """
    s = series.astype(float)
    if log:
        s = np.log1p(s.clip(lower=0))
    if clip_percent > 0 and s.notna().sum() > 2:
        lo, hi = s.quantile(clip_percent / 100), s.quantile(1 - clip_percent / 100)
        if hi > lo:  # if clipping would flatten everyone, fall back to the full range
            s = s.clip(lower=lo, upper=hi)
    if s.notna().sum() == 0:
        return pd.Series(50.0, index=s.index)  # no information at all -> neutral score
    if s.max() == s.min():
        return pd.Series(50.0, index=s.index)  # everyone's equal -> neutral score
    scaled = (s - s.min()) / (s.max() - s.min()) * 100
    scaled = scaled.fillna(50.0)  # individual missing values also become neutral
    return 100 - scaled if invert else scaled


def compute_connectivity(engine) -> pd.DataFrame:
    """Model the airport route network as a graph and measure how
    'central' each city's airport(s) are. This is one of two bits of
    geo/network science in this file — the other is nearest_airport()
    below — because airport connectivity genuinely is a network
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


def nearest_airport(cities: pd.DataFrame, airports: pd.DataFrame) -> pd.DataFrame:
    """For every city, find the closest real airport BY DISTANCE —
    not just "whichever airport got matched to this city earlier" (a
    city and its nearest airport aren't always the same thing: think
    of a small town 20km from a regional airport that officially
    "belongs" to a bigger neighbouring city).

    Uses geopy's geodesic distance, which accounts for the Earth's
    curvature rather than treating latitude/longitude like flat x/y
    coordinates.
    """
    # geopy raises an error on missing coordinates rather than just
    # skipping them, so filter those out up front — cheap insurance
    # against a stray blank row in whatever airports data you're using.
    airports = airports.dropna(subset=["latitude", "longitude"])

    results = []
    for _, city in cities.iterrows():
        best_name, best_km = None, None
        for _, airport in airports.iterrows():
            km = geodesic(
                (city["latitude"], city["longitude"]), (airport["latitude"], airport["longitude"])
            ).km
            if best_km is None or km < best_km:
                best_km, best_name = km, airport["name"]
        results.append({"city_id": city["city_id"], "nearest_airport_name": best_name, "nearest_airport_km": best_km})
    return pd.DataFrame(results)


def add_tourism_history(tourism: pd.DataFrame) -> pd.DataFrame:
    """Our sample tourism data has one year's arrivals plus a growth
    percentage, rather than several years of history. We use that
    growth percentage to work out what LAST year's arrivals would
    have been: if arrivals grew by g% to reach this year's number,
    last year's number was this_year / (1 + g/100).

    If you've swapped in real data via fetch_tourism.py, there is no
    growth percentage (the World Bank endpoint we use there only
    returns one year), so previous_arrivals ends up equal to the
    current figure and tourism_growth_pct stays 0 — see API_GUIDE.md
    for how you'd extend fetch_tourism.py to pull two years instead.
    """
    tourism = tourism.copy()
    if "tourism_growth_pct" not in tourism.columns:
        tourism["tourism_growth_pct"] = 0.0
    tourism["tourism_growth_pct"] = tourism["tourism_growth_pct"].fillna(0.0)
    tourism["previous_arrivals"] = tourism["arrivals"] / (1 + tourism["tourism_growth_pct"] / 100)
    return tourism


def build():
    engine = get_engine()

    cities = pd.read_sql("SELECT * FROM cities", engine)
    weather = pd.read_sql("SELECT * FROM weather", engine)
    airports = pd.read_sql("SELECT * FROM airports", engine)
    routes = pd.read_sql("SELECT * FROM routes", engine)
    countries = pd.read_sql("SELECT * FROM countries", engine)
    tourism = pd.read_sql("SELECT * FROM tourism", engine)
    connectivity = compute_connectivity(engine)
    nearest = nearest_airport(cities, airports)
    tourism = add_tourism_history(tourism)

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
    df = df.merge(nearest, on="city_id", how="left")
    df = df.merge(countries[["country_id", "gdp_per_capita", "urban_population_pct"]], on="country_id", how="left")

    tourism_by_country = tourism.groupby("country_id").agg(
        arrivals=("arrivals", "mean"),
        previous_arrivals=("previous_arrivals", "mean"),
        tourism_growth_pct=("tourism_growth_pct", "mean"),
    ).reset_index()
    df = df.merge(tourism_by_country, on="country_id", how="left")

    for col in ["airport_count", "route_count", "connectivity", "arrivals", "previous_arrivals", "tourism_growth_pct"]:
        df[col] = df[col].fillna(0)

    # weather comfort: closest to 22C with lower rainfall scores higher
    df["weather_comfort"] = 100 - (abs(df["avg_temperature_c"] - 22) * 4 + df["avg_precipitation_mm"] / 20)
    df["weather_comfort"] = df["weather_comfort"].clip(lower=0)

    # --- normalise every raw number to a 0-100 score ---
    scale = dict(log=LOG_SCALE, clip_percent=CLIP_PERCENT)
    df["weather_score"] = normalise_0_100(df["weather_comfort"], clip_percent=CLIP_PERCENT)  # already roughly bell-shaped: no log
    df["accessibility_score"] = normalise_0_100(
        df["airport_count"] * 2 + df["route_count"] * 0.1 + df["connectivity"] * 100, **scale
    )
    df["culture_score"] = normalise_0_100(df["heritage_sites"] * 3 + df["attractions"] / 20, **scale)
    df["cost_score"] = normalise_0_100(df["gdp_per_capita"].fillna(df["gdp_per_capita"].median()), invert=True, **scale)
    df["tourism_score"] = normalise_0_100(df["arrivals"], **scale)

    # --- the transparent baseline: a weighted average, nothing hidden ---
    df["overall_score"] = sum(df[col] * weight for col, weight in WEIGHTS.items())

    out = df[[
        "city_id", "avg_temperature_c", "avg_precipitation_mm", "airport_count",
        "route_count", "connectivity", "heritage_sites", "attractions",
        "gdp_per_capita", "urban_population_pct", "arrivals", "previous_arrivals",
        "tourism_growth_pct", "nearest_airport_name", "nearest_airport_km",
        "weather_score", "accessibility_score", "culture_score", "cost_score",
        "tourism_score", "overall_score",
    ]].rename(columns={"arrivals": "tourist_arrivals"})

    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM city_features")
        out.to_sql("city_features", conn, if_exists="append", index=False)

    print(f"Built features for {len(out)} cities.")


if __name__ == "__main__":
    build()
