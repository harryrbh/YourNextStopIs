import os
import sys

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from components import render_city_card
from data_access import direct_flights_from, load_cities, load_direct_flights
from recommend import recommend
from theme import inject_css

st.set_page_config(page_title="Recommend", page_icon="🎯", layout="wide")
inject_css()
st.title("🎯 Recommend")
st.caption("Tell us what matters to you, and we'll find your closest matches.")

cities = load_cities()
flights = load_direct_flights()
if cities.empty:
    st.warning("No data yet — see README.md for setup steps.")
    st.stop()

st.subheader("How much do you care about each of these?")
col1, col2 = st.columns(2)
with col1:
    weather = st.slider("Warm weather", 0, 100, 75)
    accessibility = st.slider("Being easy to fly to", 0, 100, 50)
    culture = st.slider("Culture and heritage", 0, 100, 50)
with col2:
    cost = st.slider("Being cheap", 0, 100, 55)
    tourism = st.slider("Being a popular destination", 0, 100, 40)

preferences = {
    "weather_score": weather,
    "accessibility_score": accessibility,
    "culture_score": culture,
    "cost_score": cost,
    "tourism_score": tourism,
}

results = recommend(preferences, top_n=9, cities=cities)

st.subheader("Your top matches")
cols_per_row = 3
rows = [results.iloc[i:i + cols_per_row] for i in range(0, len(results), cols_per_row)]
for chunk in rows:
    cols = st.columns(cols_per_row)
    for col, (_, row) in zip(cols, chunk.iterrows()):
        with col:
            render_city_card(
                row,
                direct_flights=direct_flights_from(flights, row["city_name"]),
                badge_value=row["similarity"] * 100,
                badge_suffix="% match",
            )
