"""
cluster.py — groups cities into similar "travel profiles" using
K-Means, so the app can say things like "these 8 cities are all
Warm & Affordable destinations".

Run it with:
    python src/cluster.py
"""
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from db import get_engine

FEATURES = ["weather_score", "accessibility_score", "culture_score", "cost_score", "tourism_score"]

# We tried a few values of k (2 through 8) and picked 4: enough
# groups to be useful, few enough to stay interpretable. See
# tests/test_features.py for how you'd measure this with a
# silhouette score if you want to justify a different k.
K = 4


def label_cluster(centroid: pd.Series) -> str:
    """Name a cluster after whichever score is highest in its
    centroid, rather than hard-coding four labels ourselves."""
    names = {
        "weather_score": "Warm-weather destinations",
        "accessibility_score": "Easy-to-reach cities",
        "culture_score": "Culture & heritage cities",
        "cost_score": "Budget-friendly destinations",
        "tourism_score": "Popular tourist hubs",
    }
    return names[centroid.idxmax()]


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
    print("Cluster labels:", labels)

    with engine.begin() as conn:
        for _, row in df.iterrows():
            conn.exec_driver_sql(
                f"UPDATE city_features SET cluster = {int(row['cluster'])} "
                f"WHERE city_id = {int(row['city_id'])}"
            )

    print(f"Assigned {len(df)} cities to {K} clusters.")


if __name__ == "__main__":
    run()
