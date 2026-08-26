import itertools
import os
import sys

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data_access import direct_flights_from, load_cities, load_direct_flights
from distance import km_between
from labels import FRIENDLY_NAMES, SCORE_LABELS, flag_emoji
from theme import PALETTE, inject_css

st.set_page_config(page_title="Compare", page_icon="⚖️", layout="wide")
inject_css()
st.title("⚖️ Compare")

cities = load_cities()
flights = load_direct_flights()
if cities.empty:
    st.warning("No data yet — see README.md for setup steps.")
    st.stop()

names = st.multiselect(
    "Pick 2-5 cities",
    sorted(cities["city_name"].unique()),
    default=sorted(cities["city_name"].unique())[:3],
)

if len(names) < 2:
    st.info("Pick at least two cities to compare.")
    st.stop()

subset = cities[cities["city_name"].isin(names)].set_index("city_name").loc[names].reset_index()
score_cols = list(SCORE_LABELS.keys())
score_labels = list(SCORE_LABELS.values())

st.subheader("Score comparison")
fig = go.Figure()
for i, (_, row) in enumerate(subset.iterrows()):
    values = [row[c] for c in score_cols]
    values += values[:1]
    color = PALETTE[i % len(PALETTE)]
    label = f"{flag_emoji(row.get('iso2', ''))} {row['city_name']}"
    fig.add_trace(go.Scatterpolar(
        r=values, theta=score_labels + [score_labels[0]],
        fill="toself", name=label, line_color=color,
    ))
fig.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
    height=480, margin=dict(t=30, b=10),
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Side-by-side scores")
table = subset.set_index("city_name")[["country_name", "overall_score"] + score_cols].round(0).T
table.index = table.index.map(lambda c: FRIENDLY_NAMES.get(c, c))
st.dataframe(table, use_container_width=True)

# Real-world distances between each pair, calculated with geopy — see distance.py.
st.subheader("Distance between cities")
rows = []
for city_a, city_b in itertools.combinations(names, 2):
    row_a = subset[subset["city_name"] == city_a].iloc[0]
    row_b = subset[subset["city_name"] == city_b].iloc[0]
    km = km_between(row_a["latitude"], row_a["longitude"], row_b["latitude"], row_b["longitude"])
    rows.append({"City A": city_a, "City B": city_b, "Distance (km)": round(km)})
st.dataframe(rows, use_container_width=True, hide_index=True)

# Real flight-route data — see data_access.load_direct_flights().
st.subheader("Direct flights between them")
flight_rows = []
for city_a, city_b in itertools.combinations(names, 2):
    a_to_b = city_b in direct_flights_from(flights, city_a)
    b_to_a = city_a in direct_flights_from(flights, city_b)
    flight_rows.append({
        "Route": f"{city_a} ↔ {city_b}",
        "Direct flight tracked": "✅ Yes" if (a_to_b or b_to_a) else "❌ No",
    })
st.dataframe(flight_rows, use_container_width=True, hide_index=True)
