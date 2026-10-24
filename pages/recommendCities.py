import os
import sys

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from uiComponents import renderCityCard
from dataAccess import directFlightsFrom, loadCities, loadDirectFlights
from recommendSimilarCities import recommend
from themeStyles import injectCss

st.set_page_config(page_title="Recommend", layout="wide")
injectCss()
st.title("Recommend")
st.caption("Set what matters to you to see the closest matching cities.")

cities = loadCities()
flights = loadDirectFlights()
if cities.empty:
    st.warning("No data found. Run the setup steps in README.md.")
    st.stop()

st.subheader("How important is each factor?")
leftColumn, rightColumn = st.columns(2)
with leftColumn:
    weather = st.slider("Warm weather", 0, 100, 75)
    accessibility = st.slider("Being easy to fly to", 0, 100, 50)
    culture = st.slider("Culture and heritage", 0, 100, 50)
with rightColumn:
    cost = st.slider("Being cheap", 0, 100, 55)
    tourism = st.slider("Being a popular destination", 0, 100, 40)

preferences = {
    "weather_score": weather,
    "accessibility_score": accessibility,
    "culture_score": culture,
    "cost_score": cost,
    "tourism_score": tourism,
}

recommendations = recommend(preferences, topN=9, cities=cities)

st.subheader("Your top matches")
columnsPerRow = 3
cardRows = [recommendations.iloc[rowStart:rowStart + columnsPerRow] for rowStart in range(0, len(recommendations), columnsPerRow)]
for chunk in cardRows:
    columnContainers = st.columns(columnsPerRow)
    for columnContainer, (_, row) in zip(columnContainers, chunk.iterrows()):
        with columnContainer:
            renderCityCard(
                row,
                directFlights=directFlightsFrom(flights, row["city_name"]),
                badgeValue=row["similarity"] * 100,
                badgeSuffix="% match",
            )
