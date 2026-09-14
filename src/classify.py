"""
classify.py — predicts a "price tier" (Budget / Mid-range / Luxury)
for every city using supervised learning: Logistic Regression,
Decision Tree, and Random Forest, compared against each other.

HOW THE LABELS WERE CONSTRUCTED (read this before trusting the output)
------------------------------------------------------------------
We do not have real price-tier labels — no dataset of "this city is
officially Luxury" exists for our 46 sample cities. Presenting
invented labels as if they were ground truth would be misleading. So
instead, the label is built with one clear, disclosed rule:

    Split all 46 cities into three equal-sized groups (terciles) by
    their COUNTRY's GDP per person. Bottom third = "Budget", middle
    third = "Mid-range", top third = "Luxury".

This is a proxy for price level, not a measurement of actual hotel or
travel costs — a country's average income level correlates with
prices tourists pay there, but it's not the same thing, and it says
nothing about a specific city (a country can have both budget and
luxury cities). Treat "price tier" throughout this app as an
estimated proxy, not a verified fact.

AVOIDING A TRIVIAL MODEL
------------------------------------------------------------------
Because the label is built FROM gdp_per_capita, a model that's allowed
to see gdp_per_capita as an input would trivially "predict" the label
perfectly — that wouldn't demonstrate anything. So the classifier is
deliberately trained on a DIFFERENT set of features: things you could
plausibly know about a destination without knowing its exact GDP
figure (population, heritage sites, airport connectivity, weather,
visitor numbers). This makes it a genuine predictive question: "can
we guess a destination's rough price tier from what kind of place it
is, without being told the answer directly?"

Run it with:
    python src/classify.py
"""
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy import text

from db import get_engine

# Deliberately excludes gdp_per_capita — see the module docstring.
FEATURES = [
    "population", "heritage_sites", "connectivity", "airport_count",
    "avg_temperature_c", "tourist_arrivals",
]

MODELS = {
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Decision Tree": DecisionTreeClassifier(max_depth=4, random_state=42),
    "Random Forest": RandomForestClassifier(n_estimators=200, random_state=42),
}


def load_data() -> pd.DataFrame:
    engine = get_engine()
    other_features = [f for f in FEATURES if f != "population"]
    query = f"""
        SELECT cf.city_id, cf.gdp_per_capita, c.population, {', '.join(f'cf.{f}' for f in other_features)}
        FROM city_features cf
        JOIN cities c ON c.city_id = cf.city_id
    """
    df = pd.read_sql(query, engine)
    return df.dropna()


def build_labels(df: pd.DataFrame) -> pd.Series:
    """Bottom/middle/top third of gdp_per_capita -> Budget/Mid-range/Luxury.
    See the module docstring for why this is a proxy, not ground truth."""
    return pd.qcut(df["gdp_per_capita"], q=3, labels=["Budget", "Mid-range", "Luxury"])


def compare_models(df: pd.DataFrame, labels: pd.Series, folds: int = 5) -> pd.DataFrame:
    """Cross-validated accuracy for each candidate model, so the
    comparison is fair (each model is tested on cities it wasn't
    trained on) rather than just reporting whichever model happened
    to memorise the training data best.
    """
    X = StandardScaler().fit_transform(df[FEATURES])
    results = []
    for name, model in MODELS.items():
        scores = cross_val_score(model, X, labels, cv=min(folds, labels.value_counts().min()))
        results.append({"model": name, "accuracy": scores.mean()})
    return pd.DataFrame(results).sort_values("accuracy", ascending=False)


def fit_best_model(df: pd.DataFrame, labels: pd.Series, comparison: pd.DataFrame):
    """Fit the model with the best cross-validated accuracy on all
    the data, ready to label every city."""
    best_name = comparison.iloc[0]["model"]
    model = MODELS[best_name]
    scaler = StandardScaler()
    X = scaler.fit_transform(df[FEATURES])
    model.fit(X, labels)
    return model, scaler, best_name


def persist(df: pd.DataFrame, predictions: pd.Series):
    engine = get_engine()
    with engine.begin() as conn:
        for city_id, tier in zip(df["city_id"], predictions):
            conn.execute(
                text("UPDATE city_features SET price_tier = :tier WHERE city_id = :city_id"),
                {"tier": str(tier), "city_id": int(city_id)},
            )


def run():
    df = load_data()
    labels = build_labels(df)

    comparison = compare_models(df, labels)
    print("Model comparison (cross-validated accuracy — small sample, treat as illustrative):")
    print(comparison.to_string(index=False))

    model, scaler, best_name = fit_best_model(df, labels, comparison)
    print(f"\nUsing {best_name} (best cross-validated accuracy) to label every city.")

    predictions = model.predict(scaler.transform(df[FEATURES]))
    persist(df, predictions)
    print(f"Labelled {len(df)} cities.")


if __name__ == "__main__":
    run()
