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
from sklearn.model_selection import GroupKFold, cross_val_score
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
    # Depth/leaf limits stop trees memorising individual cities (with 200 trees and
    # no limits a forest scores ~100% on cities it has seen but ~55% on new ones).
    "Decision Tree": DecisionTreeClassifier(max_depth=3, min_samples_leaf=3, random_state=42),
    "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=3, min_samples_leaf=3, random_state=42),
}


def load_data() -> pd.DataFrame:
    engine = get_engine()
    other_features = [f for f in FEATURES if f != "population"]
    query = f"""
        SELECT cf.city_id, c.country_id, cf.gdp_per_capita, c.population, {', '.join(f'cf.{f}' for f in other_features)}
        FROM city_features cf
        JOIN cities c ON c.city_id = cf.city_id
    """
    df = pd.read_sql(query, engine)

    # Only gdp_per_capita is truly required here — it's what the label
    # itself is built from (see build_labels()), so a city genuinely
    # missing it can't get a label at all. But a missing PREDICTOR
    # value (say, avg_temperature_c because Open-Meteo rate-limited
    # that particular city) shouldn't disqualify a city from getting a
    # prediction anyway — a plain `.dropna()` here used to drop the
    # WHOLE row over a single missing predictor, which is why cities
    # could end up with no price_tier at all even though they had
    # perfectly good GDP data. Impute missing predictors with the
    # column median instead, the same "unknown → neutral" approach
    # build_features.py uses for the 0-100 scores.
    df = df.dropna(subset=["gdp_per_capita"])
    for col in FEATURES:
        df[col] = df[col].fillna(df[col].median())
    return df


def build_labels(df: pd.DataFrame) -> pd.Series:
    """Bottom/middle/top third of gdp_per_capita -> Budget/Mid-range/Luxury.
    See the module docstring for why this is a proxy, not ground truth.
    """
    if df["gdp_per_capita"].nunique() < 3:
        raise RuntimeError(
            "Can't build Budget/Mid-range/Luxury labels: there isn't enough "
            "GDP-per-person data loaded to split cities into three groups "
            f"(only {df['gdp_per_capita'].nunique()} distinct value(s) found, need at least 3).\n\n"
            "This almost always means gdp_per_capita is empty for most or all "
            "cities — which is expected right after running fetch_countries.py "
            "on its own, since that API doesn't provide GDP. Run "
            "fetch_tourism.py next (it fills gdp_per_capita in from the World "
            "Bank), then re-run src/build_features.py before this script."
        )
    # gdp_per_capita is a COUNTRY-level number, so many cities in the same
    # country share the exact same value — with real data, that can put
    # several cities exactly on a tercile boundary, which qcut refuses to
    # split ("bin edges must be unique") unless told to drop the tie. We
    # can't combine duplicates="drop" with fixed labels=[...] directly,
    # though — if a boundary does get dropped, there'd be fewer bins than
    # labels, and qcut would raise a *different* error about that
    # mismatch. So we bin first without names, then name whatever number
    # of bins actually came out the other side.
    bins = pd.qcut(df["gdp_per_capita"], q=3, duplicates="drop")
    tier_names = {3: ["Budget", "Mid-range", "Luxury"], 2: ["Budget", "Luxury"], 1: ["Mid-range"]}
    names = tier_names.get(len(bins.cat.categories), [f"Tier {i + 1}" for i in range(len(bins.cat.categories))])
    return bins.cat.codes.map(dict(enumerate(names)))


def compare_models(df: pd.DataFrame, labels: pd.Series, folds: int = 5) -> pd.DataFrame:
    """Honest accuracy for each model, plus the numbers that reveal overfitting.

    * cv_accuracy    : tested on cities the model was NOT trained on. Folds are split
                       BY COUNTRY (GroupKFold): GDP and visitor numbers are country-level,
                       so with ordinary folds a Paris-trained model "recognises" Lyon by its
                       country's identical numbers — that is leakage, not skill.
    * train_accuracy : on the cities it was trained on. A big gap to cv_accuracy = overfitting.
    * baseline       : accuracy of always guessing the most common tier. A model must beat this.
    """
    X = StandardScaler().fit_transform(df[FEATURES])
    groups = df["country_id"].to_numpy()
    n_splits = min(folds, len(set(groups)))
    baseline = labels.value_counts(normalize=True).max()
    results = []
    for name, model in MODELS.items():
        cv = cross_val_score(model, X, labels, cv=GroupKFold(n_splits=n_splits), groups=groups).mean()
        train = model.fit(X, labels).score(X, labels)
        results.append({"model": name, "cv_accuracy": cv, "train_accuracy": train,
                        "gap": train - cv, "baseline": baseline})
    return pd.DataFrame(results).sort_values("cv_accuracy", ascending=False)


def fit_best_model(df: pd.DataFrame, labels: pd.Series, comparison: pd.DataFrame):
    """Fit the model with the best cross-validated accuracy on all
    the data, ready to label every city."""
    best_name = comparison.iloc[0]["model"]  # best accuracy on unseen countries
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
    print("Model comparison (cv_accuracy = on unseen countries; gap = train - cv, large gap = overfitting):")
    print(comparison.round(2).to_string(index=False))
    if comparison.iloc[0]["cv_accuracy"] <= comparison.iloc[0]["baseline"] + 0.05:
        print("WARNING: the best model barely beats always guessing the most common tier — treat "
              "price_tier as a rough label, not a reliable prediction.")

    model, scaler, best_name = fit_best_model(df, labels, comparison)
    print(f"\nUsing {best_name} (best cross-validated accuracy) to label every city.")

    predictions = model.predict(scaler.transform(df[FEATURES]))
    persist(df, predictions)
    print(f"Labelled {len(df)} cities.")


if __name__ == "__main__":
    run()
