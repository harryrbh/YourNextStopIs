"""
regression.py — a simple linear regression that predicts how many
yearly visitors a city gets, from its other attributes (population,
airports, heritage sites, GDP per person, temperature).

This is a genuinely different kind of question from `recommend.py`.
Recommend answers "which cities suit *this person*?" (comparing
preferences to cities). Regression answers "*why* do some cities get
more visitors than others?" — which attributes actually predict
popularity, and by how much.

Small honesty note: with only 46 cities, this model is illustrative,
not something you'd trust for a real business decision — the app
shows the R² score alongside the results so that's visible rather than
hidden.

Run it with:
    python src/regression.py
"""
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler

from db import get_engine

# What we're predicting FROM.
PREDICTORS = ["population", "gdp_per_capita", "airport_count", "heritage_sites", "avg_temperature_c"]
# What we're predicting.
TARGET = "tourist_arrivals"


def load_training_data() -> pd.DataFrame:
    engine = get_engine()
    query = f"""
        SELECT c.population, {', '.join(f'cf.{p}' for p in PREDICTORS if p != 'population')},
               cf.{TARGET}
        FROM city_features cf
        JOIN cities c ON c.city_id = cf.city_id
    """
    df = pd.read_sql(query, engine)
    return df.dropna()


def fit_model(df: pd.DataFrame) -> tuple[LinearRegression, StandardScaler, float]:
    """Returns the fitted model, the scaler used to prepare its
    inputs, and the R² score (how much of the variation in visitor
    numbers the model explains — 1.0 is a perfect fit, 0 is no better
    than guessing the average every time)."""
    X = df[PREDICTORS]
    y = df[TARGET]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LinearRegression()
    model.fit(X_scaled, y)

    r2 = r2_score(y, model.predict(X_scaled))
    return model, scaler, r2


def feature_importance(model: LinearRegression) -> pd.DataFrame:
    """How much each predictor matters, as a plain table — this is
    what the 'What drives popularity?' chart on the home page shows.
    Because we standardised the inputs before fitting, the
    coefficients are directly comparable to each other (a bigger
    number really does mean a bigger effect, regardless of whether
    the original column was measured in millions or degrees).
    """
    importance = pd.DataFrame({"feature": PREDICTORS, "effect": model.coef_})
    return importance.sort_values("effect", key=abs, ascending=False)


def predict(model: LinearRegression, scaler: StandardScaler, inputs: dict) -> float:
    """Predict yearly visitors for a hypothetical city. `inputs` must
    have one value for every name in PREDICTORS."""
    row = pd.DataFrame([[inputs[p] for p in PREDICTORS]], columns=PREDICTORS)
    return float(model.predict(scaler.transform(row))[0])


if __name__ == "__main__":
    data = load_training_data()
    model, scaler, r2 = fit_model(data)
    print(f"Trained on {len(data)} cities. R-squared: {r2:.2f}")
    print("\nWhat drives visitor numbers most:")
    print(feature_importance(model).to_string(index=False))
