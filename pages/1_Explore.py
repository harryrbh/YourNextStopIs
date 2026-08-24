import os
import sys

import matplotlib.pyplot as plt
import streamlit as st

# See data_access.py for why src/ needs to be added to sys.path here.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data_access import load_cities
from distance import add_distance_column
from labels import friendly
from theme import GREEN

st.set_page_config(page_title="Explore", page_icon="🔎", layout="wide")
st.title("🔎 Explore")

cities = load_cities()
if cities.empty:
    st.warning("No data yet — see README.md for setup steps.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    search = st.text_input("Search by city name")
    countries = st.multiselect("Country", sorted(cities["country_name"].unique()))
    min_weather = st.slider("Minimum weather score", 0, 100, 0)
    min_culture = st.slider("Minimum culture score", 0, 100, 0)
    min_cost = st.slider("Minimum affordability score", 0, 100, 0)

    st.divider()
    st.caption("Distance from a city you pick")
    reference_city = st.selectbox("Show distance from", ["(none)"] + sorted(cities["city_name"].unique()))

filtered = cities.copy()
if search:
    filtered = filtered[filtered["city_name"].str.contains(search, case=False, na=False)]
if countries:
    filtered = filtered[filtered["country_name"].isin(countries)]
filtered = filtered[
    (filtered["weather_score"] >= min_weather)
    & (filtered["culture_score"] >= min_culture)
    & (filtered["cost_score"] >= min_cost)
]

display_cols = [
    "city_name", "country_name", "overall_score", "weather_score",
    "accessibility_score", "culture_score", "cost_score",
]

# Real-world distances, calculated with geopy — see distance.py.
if reference_city != "(none)":
    ref_row = cities[cities["city_name"] == reference_city].iloc[0]
    filtered = add_distance_column(filtered, ref_row["latitude"], ref_row["longitude"])
    display_cols.append("distance_km")
    filtered = filtered.sort_values("distance_km")
else:
    filtered = filtered.sort_values("overall_score", ascending=False)

st.write(f"**{len(filtered)}** of {len(cities)} cities match your filters.")

if not filtered.empty:
    top = filtered.head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, max(3, len(top) * 0.35)))
    ax.barh(top["city_name"], top["overall_score"], color=GREEN)
    ax.set_xlabel("Overall score")
    ax.set_xlim(0, 100)
    fig.tight_layout()
    st.pyplot(fig)

st.dataframe(friendly(filtered[display_cols]), use_container_width=True, hide_index=True)

st.download_button(
    "Download results as CSV",
    data=filtered.to_csv(index=False),
    file_name="cities.csv",
    mime="text/csv",
)
