import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text

from database import getEngine

featureColumns = ["weather_score", "accessibility_score", "culture_score", "cost_score", "tourism_score"]

clusterCount = 4

categoryNames = {
    "weather_score": "Warm-Weather Destinations",
    "accessibility_score": "Well-Connected Cities",
    "culture_score": "Culture & Heritage",
    "cost_score": "Budget-Friendly",
    "tourism_score": "Popular Hotspots",
}


def labelCluster(centroid: pd.Series) -> str:
    return categoryNames[centroid.idxmax()]


def run():
    engine = getEngine()
    cityTable = pd.read_sql(f"SELECT city_id, {', '.join(featureColumns)} FROM city_features", engine)
    cityTable = cityTable.dropna(subset=featureColumns)

    # K-Means measures distance, so features need to be on the same scale first
    featureMatrix = StandardScaler().fit_transform(cityTable[featureColumns])

    model = KMeans(n_clusters=clusterCount, random_state=42, n_init="auto")
    cityTable["cluster"] = model.fit_predict(featureMatrix)

    centroids = pd.DataFrame(model.cluster_centers_, columns=featureColumns)
    labels = {clusterId: labelCluster(row) for clusterId, row in centroids.iterrows()}
    seen = {}
    for clusterId, name in list(labels.items()):
        seen[name] = seen.get(name, 0) + 1
        if list(labels.values()).count(name) > 1:
            labels[clusterId] = f"{name} ({seen[name]})"
    cityTable["category"] = cityTable["cluster"].map(labels)
    print("Category labels:", labels)

    with engine.begin() as conn:
        for _, row in cityTable.iterrows():
            conn.execute(
                text("UPDATE city_features SET category = :category WHERE city_id = :city_id"),
                {"category": row["category"], "city_id": int(row["city_id"])},
            )

    print(f"Assigned {len(cityTable)} cities to {clusterCount} categories.")


if __name__ == "__main__":
    run()
