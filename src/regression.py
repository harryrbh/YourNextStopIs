"""
regression.py — a linear regression that predicts how many yearly
visitors a city's country gets ("tourism demand"), from a set of
candidate predictors:

    - GDP per person (gdp_per_capita)
    - population
    - airport connectivity (the NetworkX score from build_features.py)
    - heritage sites
    - weather (temperature and rainfall)
    - previous year's arrivals
    - year-on-year tourism growth

This is a genuinely different kind of question from `recommend.py`.
Recommend answers "which cities suit *this person*?" (comparing
preferences to cities). Regression answers "given a destination's
measurable characteristics, roughly how many visitors would we expect
it to get?" — a number, not a score out of 100.

Small honesty note: with only 46 cities, this model is illustrative,
not something you'd trust for a real forecasting decision — the app
shows the R² score alongside the results so that's visible rather than
hidden.

Run it with:
    python src/regression.py
"""
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

from db import get_engine

# What we're predicting FROM. All eight candidate predictors named in
# the project brief; every one already lives in city_features.
PREDICTORS = [
    "population", "gdp_per_capita", "connectivity", "heritage_sites",
    "avg_temperature_c", "avg_precipitation_mm",
    "previous_arrivals", "tourism_growth_pct",
]
# A second, smaller predictor set: everything EXCEPT previous_arrivals
# and tourism_growth_pct. See the big comment in load_training_data()
# for why this second set exists — short version: in our sample data,
# previous_arrivals is calculated FROM this year's arrivals, so a
# model using it "predicts" the target almost perfectly without
# learning anything real. This structural-only set is the honest,
# genuinely predictive question: what explains demand from a
# destination's characteristics alone?
STRUCTURAL_PREDICTORS = [p for p in PREDICTORS if p not in ("previous_arrivals", "tourism_growth_pct")]

# What we're predicting: the actual number of yearly visitors.
TARGET = "tourist_arrivals"

PREDICTOR_LABELS = {
    "population": "Population",
    "gdp_per_capita": "GDP per person",
    "connectivity": "Airport connectivity",
    "heritage_sites": "Heritage sites",
    "avg_temperature_c": "Average temperature",
    "avg_precipitation_mm": "Average rainfall",
    "previous_arrivals": "Previous year's visitors",
    "tourism_growth_pct": "Tourism growth rate",
}


def load_training_data() -> pd.DataFrame:
    """Loads every predictor plus the target.

    IMPORTANT — a data-construction caveat, not a modelling one: our
    sample data only has one real year of tourism figures per
    country, so build_features.py's add_tourism_history() calculates
    `previous_arrivals` algebraically FROM this year's arrivals and
    the growth rate (previous = arrivals / (1 + growth/100)). That
    means `arrivals ≈ previous_arrivals × (1 + tourism_growth_pct/100)`
    is baked into the sample data by construction — a model given
    both previous_arrivals and tourism_growth_pct can reconstruct
    arrivals almost exactly, which LOOKS like an excellent model but
    isn't demonstrating real predictive skill, just recovering the
    arithmetic we put in. This is why the app trains and reports TWO
    models (see fit_model / STRUCTURAL_PREDICTORS): the full one,
    matching the predictors requested, and a "structural-only" one
    that excludes previous_arrivals/growth and is the more honest
    measure of what this model can actually predict. With real
    multi-year data — where previous_arrivals is an independent
    historical measurement, not backed out algebraically — this
    circularity wouldn't exist, and the full model's score would mean
    something.
    """
    engine = get_engine()
    query = f"""
        SELECT c.population, {', '.join(f'cf.{p}' for p in PREDICTORS if p != 'population')},
               cf.{TARGET}
        FROM city_features cf
        JOIN cities c ON c.city_id = cf.city_id
    """
    df = pd.read_sql(query, engine)

    # Only the TARGET (tourist_arrivals) is truly required — a city
    # missing that can't be used to train or evaluate the model at
    # all. A missing PREDICTOR (say, avg_temperature_c for a city
    # Open-Meteo rate-limited, or previous_arrivals for a country
    # World Bank has no data for) shouldn't drop the whole city from
    # training, the same "unknown → neutral" approach used elsewhere
    # in this project (see build_features.py's normalise_0_100 and
    # classify.py's load_data() for the same reasoning) — a plain
    # `.dropna()` here used to throw away every city missing even one
    # predictor, which with real API data can be most of them.
    df = df.dropna(subset=[TARGET])
    for col in PREDICTORS:
        df[col] = df[col].fillna(df[col].median())
    return df


def fit_model(df: pd.DataFrame, predictors: list[str] = PREDICTORS) -> tuple[LinearRegression, StandardScaler, float]:
    """Returns the fitted model, the scaler used to prepare its
    inputs, and the R² score (how much of the variation in visitor
    numbers the model explains — 1.0 is a perfect fit, 0 is no better
    than guessing the average every time)."""
    X = df[predictors]
    y = df[TARGET]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LinearRegression()
    model.fit(X_scaled, y)

    r2 = r2_score(y, model.predict(X_scaled))
    return model, scaler, r2


def cross_validated_r2(df: pd.DataFrame, predictors: list[str] = PREDICTORS, folds: int = 5) -> float:
    """A more honest accuracy check than fit_model()'s R²: that one
    tests the model on the same data it was trained on (which always
    looks better than reality). This instead trains on 4/5 of the
    cities and tests on the held-out 1/5, five times over, and
    averages the result — a fairer estimate of how the model would do
    on a city it has never seen.
    """
    X = StandardScaler().fit_transform(df[predictors])
    y = df[TARGET]
    scores = cross_val_score(LinearRegression(), X, y, cv=min(folds, len(df)), scoring="r2")
    return float(scores.mean())


def feature_importance(model: LinearRegression, predictors: list[str] = PREDICTORS) -> pd.DataFrame:
    """How much each predictor matters, as a plain table. Because we
    standardised the inputs before fitting, the coefficients are
    directly comparable to each other (a bigger number really does
    mean a bigger effect, regardless of whether the original column
    was measured in millions or degrees).
    """
    importance = pd.DataFrame({
        "feature": [PREDICTOR_LABELS[p] for p in predictors],
        "effect": model.coef_,
    })
    return importance.sort_values("effect", key=abs, ascending=False)


def predict(model: LinearRegression, scaler: StandardScaler, inputs: dict, predictors: list[str] = PREDICTORS) -> float:
    """Predict yearly visitors for a hypothetical destination.
    `inputs` must have one value for every name in `predictors`."""
    row = pd.DataFrame([[inputs[p] for p in predictors]], columns=predictors)
    return float(model.predict(scaler.transform(row))[0])


if __name__ == "__main__":
    data = load_training_data()

    print(f"Trained on {len(data)} cities.\n")

    model, scaler, r2 = fit_model(data, PREDICTORS)
    cv_r2 = cross_validated_r2(data, PREDICTORS)
    print("Full model (all predictors, including previous year's arrivals and growth):")
    print(f"  R-squared (training data): {r2:.2f}")
    print(f"  R-squared (cross-validated): {cv_r2:.2f}")
    print("  ^ Suspiciously close to 1.0 — see load_training_data()'s docstring: this is")
    print("    the sample data's built-in arithmetic being recovered, not real skill.")

    struct_model, struct_scaler, struct_r2 = fit_model(data, STRUCTURAL_PREDICTORS)
    struct_cv_r2 = cross_validated_r2(data, STRUCTURAL_PREDICTORS)
    print("\nStructural model (excludes previous arrivals/growth — the honest one):")
    print(f"  R-squared (training data): {struct_r2:.2f}")
    print(f"  R-squared (cross-validated): {struct_cv_r2:.2f}")
    print("\nWhat predicts visitor numbers most, structurally:")
    print(feature_importance(struct_model, STRUCTURAL_PREDICTORS).to_string(index=False))
