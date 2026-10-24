import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

from database import getEngine

# What we're predicting FROM
defaultPredictors = [
    "population", "gdp_per_capita", "connectivity", "heritage_sites",
    "avg_temperature_c", "avg_precipitation_mm",
    "previous_arrivals", "tourism_growth_pct",
]
structuralPredictors = [predictor for predictor in defaultPredictors if predictor not in ("previous_arrivals", "tourism_growth_pct")]

# What we're predicting: the actual number of yearly visitors
targetColumn = "tourist_arrivals"

predictorLabels = {
    "population": "Population",
    "gdp_per_capita": "GDP per person",
    "connectivity": "Airport connectivity",
    "heritage_sites": "Heritage sites",
    "avg_temperature_c": "Average temperature",
    "avg_precipitation_mm": "Average rainfall",
    "previous_arrivals": "Previous year's visitors",
    "tourism_growth_pct": "Tourism growth rate",
}


def loadTrainingData() -> pd.DataFrame:
    """Loads every predictor plus the target."""
    engine = getEngine()
    query = f"""
        SELECT c.population, {', '.join(f'cf.{predictor}' for predictor in defaultPredictors if predictor != 'population')},
               cf.{targetColumn}
        FROM city_features cf
        JOIN cities c ON c.city_id = cf.city_id
    """
    trainingTable = pd.read_sql(query, engine)

    # Only the TARGET (tourist_arrivals) is truly required
    trainingTable = trainingTable.dropna(subset=[targetColumn])
    for columnName in defaultPredictors:
        trainingTable[columnName] = trainingTable[columnName].fillna(trainingTable[columnName].median())
    return trainingTable


def fitModel(trainingTable: pd.DataFrame, predictors: list[str] = defaultPredictors) -> tuple[LinearRegression, StandardScaler, float]:
    featureMatrix = trainingTable[predictors]
    targetValues = trainingTable[targetColumn]

    scaler = StandardScaler()
    scaledFeatures = scaler.fit_transform(featureMatrix)

    model = LinearRegression()
    model.fit(scaledFeatures, targetValues)

    rSquared = r2_score(targetValues, model.predict(scaledFeatures))
    return model, scaler, rSquared


def crossValidatedR2(trainingTable: pd.DataFrame, predictors: list[str] = defaultPredictors, folds: int = 5) -> float:
    featureMatrix = StandardScaler().fit_transform(trainingTable[predictors])
    targetValues = trainingTable[targetColumn]
    scores = cross_val_score(LinearRegression(), featureMatrix, targetValues, cv=min(folds, len(trainingTable)), scoring="r2")
    return float(scores.mean())


def featureImportance(model: LinearRegression, predictors: list[str] = defaultPredictors) -> pd.DataFrame:
    """How much each predictor matters, as a plain table."""
    importance = pd.DataFrame({
        "feature": [predictorLabels[predictor] for predictor in predictors],
        "effect": model.coef_,
    })
    return importance.sort_values("effect", key=abs, ascending=False)


def predict(model: LinearRegression, scaler: StandardScaler, inputs: dict, predictors: list[str] = defaultPredictors) -> float:
    """Predict yearly visitors for a hypothetical destination."""
    inputRow = pd.DataFrame([[inputs[predictor] for predictor in predictors]], columns=predictors)
    return float(model.predict(scaler.transform(inputRow))[0])


if __name__ == "__main__":
    trainingData = loadTrainingData()

    print(f"Trained on {len(trainingData)} cities.\n")

    model, scaler, rSquared = fitModel(trainingData, defaultPredictors)
    crossValidationScore = crossValidatedR2(trainingData, defaultPredictors)
    print("Full model (all predictors, including previous year's arrivals and growth):")
    print(f"  R-squared (training data): {rSquared:.2f}")
    print(f"  R-squared (cross-validated): {crossValidationScore:.2f}")
    print("  ^ Suspiciously close to 1.0 — see load_training_data()'s docstring: this is")
    print("    the sample data's built-in arithmetic being recovered, not real skill.")

    structModel, structScaler, structuralRSquared = fitModel(trainingData, structuralPredictors)
    structuralCrossValidationScore = crossValidatedR2(trainingData, structuralPredictors)
    print("\nStructural model (excludes previous arrivals/growth — the honest one):")
    print(f"  R-squared (training data): {structuralRSquared:.2f}")
    print(f"  R-squared (cross-validated): {structuralCrossValidationScore:.2f}")
    print("\nWhat predicts visitor numbers most, structurally:")
    print(featureImportance(structModel, structuralPredictors).to_string(index=False))
