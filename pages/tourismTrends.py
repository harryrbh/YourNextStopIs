import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dataAccess import loadCities
from displayLabels import friendly
from predictTourismDemand import structuralPredictors, fitModel, loadTrainingData, predict
from themeStyles import colorscale, injectCss

st.set_page_config(page_title="Tourism", layout="wide")
injectCss()
st.title("Tourism")
st.caption("Visitor numbers by country and a simple demand estimate.")

cities = loadCities()
if cities.empty:
    st.warning("No data found. Run the setup steps in README.md.")
    st.stop()

# One row per country (many cities share a country and its tourism figures)
byCountry = cities.drop_duplicates("country_name").sort_values("tourist_arrivals", ascending=False)

st.subheader("Visitors by country")
figure = px.bar(
    byCountry.head(20).sort_values("tourist_arrivals"),
    x="tourist_arrivals", y="country_name", orientation="h",
    color="tourist_arrivals", color_continuous_scale=colorscale,
    labels={"tourist_arrivals": "Yearly visitors", "country_name": ""},
    height=500,
)
figure.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=10, t=10, b=0))
st.plotly_chart(figure, width="stretch")

st.subheader("Fastest and slowest growing destinations")
growthSorted = byCountry.dropna(subset=["tourism_growth_pct"]).sort_values("tourism_growth_pct", ascending=False)
leftColumn, middleColumn = st.columns(2)
with leftColumn:
    st.markdown("**Growing fastest**")
    st.dataframe(
        friendly(growthSorted.head(6)[["country_name", "tourism_growth_pct", "tourist_arrivals"]]),
        width="stretch", hide_index=True,
    )
with middleColumn:
    st.markdown("**Growing slowest**")
    st.dataframe(
        friendly(growthSorted.tail(6)[["country_name", "tourism_growth_pct", "tourist_arrivals"]]),
        width="stretch", hide_index=True,
    )

st.divider()
st.subheader("Estimate visitor demand for a destination")
st.caption(
    "A linear regression estimates yearly visitors from the characteristics below."
)

try:
    trainingData = loadTrainingData()
    model, scaler, rSquared = fitModel(trainingData, structuralPredictors)

    leftColumn, middleColumn, rightColumn = st.columns(3)
    with leftColumn:
        population = st.number_input("City population", min_value=10_000, max_value=30_000_000, value=1_000_000, step=50_000)
        gdpPerCapita = st.number_input("Country GDP per person (USD)", min_value=500, max_value=100_000, value=30_000, step=500)
    with middleColumn:
        connectivity = st.slider("Airport connectivity (0-1)", 0.0, 1.0, 0.2)
        heritage = st.number_input("Heritage sites nearby", min_value=0, max_value=10, value=2)
    with rightColumn:
        temperature = st.slider("Average temperature (°C)", -10, 40, 18)
        rainfall = st.slider("Average rainfall (mm)", 0, 300, 60)

    inputs = {
        "population": population, "gdp_per_capita": gdpPerCapita, "connectivity": connectivity,
        "heritage_sites": heritage, "avg_temperature_c": temperature, "avg_precipitation_mm": rainfall,
    }
    estimate = predict(model, scaler, inputs, structuralPredictors)
    estimate = max(0, estimate)

    st.metric("Estimated yearly visitors", f"{estimate:,.0f}")
    st.caption(
        f"Model R²: {rSquared:.2f}. This is a rough estimate, not a forecast."
    )
except Exception as error:
    st.info(f"Could not train the model: {error}")
