import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data_access import load_cities
from labels import friendly
from regression import STRUCTURAL_PREDICTORS, fit_model, load_training_data, predict
from theme import COLORSCALE, inject_css

st.set_page_config(page_title="Tourism", layout="wide")
inject_css()
st.title("Tourism")
st.caption("Visitor numbers, growth, and an estimate of what drives demand.")

cities = load_cities()
if cities.empty:
    st.warning("No data yet — see README.md for setup steps.")
    st.stop()

# One row per country (many cities share a country and its tourism figures).
by_country = cities.drop_duplicates("country_name").sort_values("tourist_arrivals", ascending=False)

st.subheader("Visitors by country")
fig = px.bar(
    by_country.head(20).sort_values("tourist_arrivals"),
    x="tourist_arrivals", y="country_name", orientation="h",
    color="tourist_arrivals", color_continuous_scale=COLORSCALE,
    labels={"tourist_arrivals": "Yearly visitors", "country_name": ""},
    height=500,
)
fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=10, t=10, b=0))
st.plotly_chart(fig, use_container_width=True)

st.subheader("Fastest-growing and fastest-shrinking destinations")
growth_sorted = by_country.dropna(subset=["tourism_growth_pct"]).sort_values("tourism_growth_pct", ascending=False)
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Growing fastest**")
    st.dataframe(
        friendly(growth_sorted.head(6)[["country_name", "tourism_growth_pct", "tourist_arrivals"]]),
        use_container_width=True, hide_index=True,
    )
with col2:
    st.markdown("**Growing slowest**")
    st.dataframe(
        friendly(growth_sorted.tail(6)[["country_name", "tourism_growth_pct", "tourist_arrivals"]]),
        use_container_width=True, hide_index=True,
    )

st.divider()
st.subheader("Estimate visitor demand for a destination")
st.caption(
    "Set some characteristics of a real or hypothetical destination below, and a "
    "regression model trained on these 46 cities will estimate roughly how many "
    "yearly visitors a place like that might get. This uses only the "
    "'structural' predictors (not previous visitor numbers), so it reflects what "
    "kind of place it is rather than just repeating a trend — see src/regression.py "
    "for the full explanation and honesty notes on model accuracy."
)

try:
    data = load_training_data()
    model, scaler, r2 = fit_model(data, STRUCTURAL_PREDICTORS)

    col1, col2, col3 = st.columns(3)
    with col1:
        population = st.number_input("City population", min_value=10_000, max_value=30_000_000, value=1_000_000, step=50_000)
        gdp = st.number_input("Country GDP per person (USD)", min_value=500, max_value=100_000, value=30_000, step=500)
    with col2:
        connectivity = st.slider("Airport connectivity (0-1)", 0.0, 1.0, 0.2)
        heritage = st.number_input("Heritage sites nearby", min_value=0, max_value=10, value=2)
    with col3:
        temperature = st.slider("Average temperature (°C)", -10, 40, 18)
        rainfall = st.slider("Average rainfall (mm)", 0, 300, 60)

    inputs = {
        "population": population, "gdp_per_capita": gdp, "connectivity": connectivity,
        "heritage_sites": heritage, "avg_temperature_c": temperature, "avg_precipitation_mm": rainfall,
    }
    estimate = predict(model, scaler, inputs, STRUCTURAL_PREDICTORS)
    estimate = max(0, estimate)

    st.metric("Estimated yearly visitors", f"{estimate:,.0f}")
    st.caption(
        f"Model fit on training data: R² = {r2:.2f}. With only 46 cities to learn "
        "from, treat this as a rough, illustrative estimate rather than a forecast."
    )
except Exception as e:
    st.info(f"Not enough data yet to train the model — run the setup steps first. ({e})")
