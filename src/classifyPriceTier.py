import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sqlalchemy import text

from database import getEngine

# Deliberately excludes gdp_per_capita
featureColumns = [
    "population", "heritage_sites", "connectivity", "airport_count",
    "avg_temperature_c", "tourist_arrivals",
]

models = {
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Decision Tree": DecisionTreeClassifier(max_depth=3, min_samples_leaf=3, random_state=42),
    "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=3, min_samples_leaf=3, random_state=42),
}


def loadData() -> pd.DataFrame:
    engine = getEngine()
    otherFeatures = [feature for feature in featureColumns if feature != "population"]
    query = f"""
        SELECT cf.city_id, c.country_id, cf.gdp_per_capita, c.population, {', '.join(f'cf.{feature}' for feature in otherFeatures)}
        FROM city_features cf
        JOIN cities c ON c.city_id = cf.city_id
    """
    cityTable = pd.read_sql(query, engine)

    # Only gdp_per_capita is truly required here
    cityTable = cityTable.dropna(subset=["gdp_per_capita"])
    for featureName in featureColumns:
        cityTable[featureName] = cityTable[featureName].fillna(cityTable[featureName].median())
    return cityTable


def buildLabels(cityTable: pd.DataFrame) -> pd.Series:
    """Bottom/middle/top third of gdp_per_capita -> Budget/Mid-range/Luxury."""
    if cityTable["gdp_per_capita"].nunique() < 3:
        raise RuntimeError(
            "Can't build Budget/Mid-range/Luxury labels: there isn't enough "
            "GDP-per-person data loaded to split cities into three groups "
            f"(only {cityTable['gdp_per_capita'].nunique()} distinct value(s) found, need at least 3).\n\n"
            "This almost always means gdp_per_capita is empty for most or all "
            "cities — which is expected right after running fetchCountries.py "
            "on its own, since that API doesn't provide GDP. Run "
            "fetchTourism.py next (it fills gdp_per_capita in from the World "
            "Bank), then re-run src/buildCityFeatures.py before this script."
        )
    bins = pd.qcut(cityTable["gdp_per_capita"], q=3, duplicates="drop")
    tierNames = {3: ["Budget", "Mid-range", "Luxury"], 2: ["Budget", "Luxury"], 1: ["Mid-range"]}
    names = tierNames.get(len(bins.cat.categories), [f"Tier {tierNumber + 1}" for tierNumber in range(len(bins.cat.categories))])
    return bins.cat.codes.map(dict(enumerate(names)))


def compareModels(cityTable: pd.DataFrame, labels: pd.Series, folds: int = 5) -> pd.DataFrame:
    """Honest accuracy for each model, plus the numbers that reveal overfitting."""
    featureMatrix = StandardScaler().fit_transform(cityTable[featureColumns])
    groups = cityTable["country_id"].to_numpy()
    nSplits = min(folds, len(set(groups)))
    baseline = labels.value_counts(normalize=True).max()
    modelResults = []
    for name, model in models.items():
        crossValidationAccuracy = cross_val_score(model, featureMatrix, labels, cv=GroupKFold(n_splits=nSplits), groups=groups).mean()
        train = model.fit(featureMatrix, labels).score(featureMatrix, labels)
        modelResults.append({"model": name, "cv_accuracy": crossValidationAccuracy, "train_accuracy": train,
                        "gap": train - crossValidationAccuracy, "baseline": baseline})
    return pd.DataFrame(modelResults).sort_values("cv_accuracy", ascending=False)


def fitBestModel(cityTable: pd.DataFrame, labels: pd.Series, comparison: pd.DataFrame):
    """Fit the model with the best cross-validated accuracy on all the data, ready to label every city."""
    bestName = comparison.iloc[0]["model"]  # Best accuracy on unseen countries
    model = models[bestName]
    scaler = StandardScaler()
    featureMatrix = scaler.fit_transform(cityTable[featureColumns])
    model.fit(featureMatrix, labels)
    return model, scaler, bestName


def persist(cityTable: pd.DataFrame, predictions: pd.Series):
    engine = getEngine()
    with engine.begin() as conn:
        for cityId, tier in zip(cityTable["city_id"], predictions):
            conn.execute(
                text("UPDATE city_features SET price_tier = :tier WHERE city_id = :city_id"),
                {"tier": str(tier), "city_id": int(cityId)},
            )


def run():
    cityTable = loadData()
    labels = buildLabels(cityTable)

    comparison = compareModels(cityTable, labels)
    print("Model comparison (cv_accuracy = on unseen countries; gap = train - cv, large gap = overfitting):")
    print(comparison.round(2).to_string(index=False))
    if comparison.iloc[0]["cv_accuracy"] <= comparison.iloc[0]["baseline"] + 0.05:
        print("WARNING: the best model barely beats always guessing the most common tier — treat "
              "price_tier as a rough label, not a reliable prediction.")

    model, scaler, bestName = fitBestModel(cityTable, labels, comparison)
    print(f"\nUsing {bestName} (best cross-validated accuracy) to label every city.")

    predictions = model.predict(scaler.transform(cityTable[featureColumns]))
    persist(cityTable, predictions)
    print(f"Labelled {len(cityTable)} cities.")


if __name__ == "__main__":
    run()
