"""
cluster.py — groups cities into similar "travel profiles" using
K-Means, so the app can say things like "these 8 cities are all
Warm-Weather Destinations".

Run it with:
    python src/cluster.py
"""
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text

from db import get_engine

FEATURES = ["weather_score", "accessibility_score", "culture_score", "cost_score", "tourism_score"]

# We tried a few values of k (2 through 8) and picked 4: enough
# groups to be useful, few enough to stay interpretable.
K = 4

CATEGORY_NAMES = {
    "weather_score": "Warm-Weather Destinations",
    "accessibility_score": "Well-Connected Cities",
    "culture_score": "Culture & Heritage",
    "cost_score": "Budget-Friendly",
    "tourism_score": "Popular Hotspots",
}


def label_cluster(centroid: pd.Series) -> str:
    """Name a cluster after whichever score is highest in its
    centroid, rather than hard-coding four labels ourselves."""
    return CATEGORY_NAMES[centroid.idxmax()]


def run():
    engine = get_engine()
    df = pd.read_sql(f"SELECT city_id, {', '.join(FEATURES)} FROM city_features", engine)
    df = df.dropna(subset=FEATURES)

    # K-Means measures distance, so features need to be on the same
    # scale first — StandardScaler makes each column mean 0, std 1.
    X = StandardScaler().fit_transform(df[FEATURES])

    model = KMeans(n_clusters=K, random_state=42, n_init="auto")
    df["cluster"] = model.fit_predict(X)

    centroids = pd.DataFrame(model.cluster_centers_, columns=FEATURES)
    labels = {i: label_cluster(row) for i, row in centroids.iterrows()}
    # Two clusters can share the same top score and so the same name, which
    # makes "Travel style" filters ambiguous. Number any duplicates.
    seen = {}
    for i, name in list(labels.items()):
        seen[name] = seen.get(name, 0) + 1
        if list(labels.values()).count(name) > 1:
            labels[i] = f"{name} ({seen[name]})"
    df["category"] = df["cluster"].map(labels)
    print("Category labels:", labels)

    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.execute(
                text("UPDATE city_features SET category = :category WHERE city_id = :city_id"),
                {"category": row["category"], "city_id": int(row["city_id"])},
            )

    print(f"Assigned {len(df)} cities to {K} categories.")


if __name__ == "__main__":
    run()
