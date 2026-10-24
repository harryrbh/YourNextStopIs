"""Given a traveller's preferences, finds the cities whose feature scores are closest to what they asked for."""
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from database import getEngine

featureColumns = ["weather_score", "accessibility_score", "culture_score", "cost_score", "tourism_score"]


def loadCitiesWithScores() -> pd.DataFrame:
    engine = getEngine()
    query = """
        SELECT cf.*, c.name AS city_name, co.name AS country_name
        FROM city_features cf
        JOIN cities c ON c.city_id = cf.city_id
        JOIN countries co ON co.country_id = c.country_id
    """
    cityTable = pd.read_sql(query, engine)
    return cityTable.dropna(subset=featureColumns)


def recommend(preferences: dict, topN: int = 10, cities: pd.DataFrame | None = None) -> pd.DataFrame:
    cities = cities if cities is not None else loadCitiesWithScores()
    cities = cities.dropna(subset=featureColumns)

    preferenceRow = [preferences.get(feature, 50) for feature in featureColumns]

    scaler = StandardScaler()
    featureMatrix = scaler.fit_transform(cities[featureColumns])
    preferenceScaled = scaler.transform(pd.DataFrame([preferenceRow], columns=featureColumns))

    model = NearestNeighbors(n_neighbors=min(topN, len(cities)), metric="cosine")
    model.fit(featureMatrix)
    distances, indices = model.kneighbors(preferenceScaled)

    recommendations = cities.iloc[indices[0]].copy()
    recommendations["similarity"] = 1 - distances[0]
    return recommendations.sort_values("similarity", ascending=False)


def mostSimilarCities(cityId: int, numberOfCities: int = 3, cities: pd.DataFrame | None = None) -> pd.DataFrame:
    """The n cities whose own scores are closest to a GIVEN city's scores."""
    cities = cities if cities is not None else loadCitiesWithScores()
    cities = cities.dropna(subset=featureColumns)
    target = cities[cities["city_id"] == cityId]
    if target.empty:
        return cities.iloc[0:0]

    others = cities[cities["city_id"] != cityId].reset_index(drop=True)
    scaler = StandardScaler()
    featureMatrix = scaler.fit_transform(others[featureColumns])
    targetScaled = scaler.transform(target[featureColumns])

    model = NearestNeighbors(n_neighbors=min(numberOfCities, len(others)), metric="cosine")
    model.fit(featureMatrix)
    distances, indices = model.kneighbors(targetScaled)

    recommendations = others.iloc[indices[0]].copy()
    recommendations["similarity"] = 1 - distances[0]
    return recommendations.sort_values("similarity", ascending=False)


if __name__ == "__main__":
    examplePreferences = {"weather_score": 85, "cost_score": 70, "culture_score": 60}
    topCities = recommend(examplePreferences, topN=5)
    print(topCities[["city_name", "country_name", "similarity"]].to_string(index=False))
