"""
recommend.py — given a traveller's preferences, finds the cities
whose feature scores are closest to what they asked for.

We represent both "what the user wants" and "what each city offers"
as points in the same 5-dimensional space (one dimension per score),
then use K-Nearest-Neighbours with cosine similarity to find the
closest cities. Cosine similarity cares about the *shape* of the
preference (e.g. "warm and cheap") rather than raw magnitude, which
suits 0-100 scores well.

This file is meant to be imported (by the Streamlit app), but you can
also run it directly to see an example:
    python src/recommend.py
"""
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from db import get_engine

FEATURES = ["weather_score", "accessibility_score", "culture_score", "cost_score", "tourism_score"]


def load_cities_with_scores() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT cf.*, c.name AS city_name, co.name AS country_name
        FROM city_features cf
        JOIN cities c ON c.city_id = cf.city_id
        JOIN countries co ON co.country_id = c.country_id
    """
    df = pd.read_sql(query, engine)
    return df.dropna(subset=FEATURES)


def recommend(preferences: dict, top_n: int = 10, cities: pd.DataFrame | None = None) -> pd.DataFrame:
    """preferences is a dict like:
        {"weather_score": 80, "accessibility_score": 50, "culture_score": 60,
         "cost_score": 70, "tourism_score": 30}
    Any score you leave out defaults to 50 (neutral).
    """
    cities = cities if cities is not None else load_cities_with_scores()
    # Whether `cities` was just loaded above or handed to us by the
    # caller (the Streamlit pages all pass in their own already-loaded
    # DataFrame), NearestNeighbors cannot handle any NaN at all — so
    # we drop incomplete rows here too, rather than trusting every
    # caller to have done it already.
    cities = cities.dropna(subset=FEATURES)

    pref_row = [preferences.get(f, 50) for f in FEATURES]

    scaler = StandardScaler()
    X = scaler.fit_transform(cities[FEATURES])
    pref_scaled = scaler.transform(pd.DataFrame([pref_row], columns=FEATURES))

    model = NearestNeighbors(n_neighbors=min(top_n, len(cities)), metric="cosine")
    model.fit(X)
    distances, indices = model.kneighbors(pref_scaled)

    result = cities.iloc[indices[0]].copy()
    result["similarity"] = 1 - distances[0]
    return result.sort_values("similarity", ascending=False)


def most_similar_cities(city_id: int, n: int = 3, cities: pd.DataFrame | None = None) -> pd.DataFrame:
    """The n cities whose own scores are closest to a GIVEN city's
    scores — not a user's preferences this time, but one city
    compared to every other. Same technique as recommend(): scale
    the five scores, then use cosine-similarity nearest neighbours.
    """
    cities = cities if cities is not None else load_cities_with_scores()
    cities = cities.dropna(subset=FEATURES)
    target = cities[cities["city_id"] == city_id]
    if target.empty:
        return cities.iloc[0:0]

    others = cities[cities["city_id"] != city_id].reset_index(drop=True)
    scaler = StandardScaler()
    X = scaler.fit_transform(others[FEATURES])
    target_scaled = scaler.transform(target[FEATURES])

    model = NearestNeighbors(n_neighbors=min(n, len(others)), metric="cosine")
    model.fit(X)
    distances, indices = model.kneighbors(target_scaled)

    result = others.iloc[indices[0]].copy()
    result["similarity"] = 1 - distances[0]
    return result.sort_values("similarity", ascending=False)


if __name__ == "__main__":
    example_prefs = {"weather_score": 85, "cost_score": 70, "culture_score": 60}
    top_cities = recommend(example_prefs, top_n=5)
    print(top_cities[["city_name", "country_name", "similarity"]].to_string(index=False))
