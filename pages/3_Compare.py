import itertools
import os
import sys

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data_access import direct_flights_from, load_cities, load_direct_flights
from distance import km_between
from labels import FRIENDLY_NAMES, SCORE_LABELS, flag_emoji
from theme import BLUE, GREEN, PALETTE, inject_css

st.set_page_config(page_title="Compare", layout="wide")
inject_css()
st.title("Compare")

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
st.plotly_chart(fig, width="stretch")

st.subheader("Side-by-side scores")
table = subset.set_index("city_name")[["country_name", "overall_score"] + score_cols].copy()
for col in ["overall_score"] + score_cols:
    table[col] = table[col].round(0)
table = table.T
table.index = table.index.map(lambda c: FRIENDLY_NAMES.get(c, c))
# After the transpose above, every COLUMN is one city, and each city's
# column holds a mix of text (its country name) and numbers (every
# score) together — a genuinely mixed-type column. st.dataframe uses
# PyArrow to render tables, and PyArrow can't reliably serialize a
# column like that (it crashes with "Expected bytes, got a 'float'
# object" on whichever city happens to trip it). Formatting everything
# as plain text sidesteps this entirely; this table is for reading,
# not further computation, so losing native numeric typing costs
# nothing here.
table = table.fillna("N/A").astype(str)
st.dataframe(table, width="stretch")

# Real-world distances between each pair, calculated with geopy — see distance.py.
st.subheader("Distance between cities")
distance_rows = []
for city_a, city_b in itertools.combinations(names, 2):
    row_a = subset[subset["city_name"] == city_a].iloc[0]
    row_b = subset[subset["city_name"] == city_b].iloc[0]
    km = km_between(row_a["latitude"], row_a["longitude"], row_b["latitude"], row_b["longitude"])
    distance_rows.append({"City A": city_a, "City B": city_b, "Distance (km)": round(km)})
st.dataframe(distance_rows, width="stretch", hide_index=True)

# Real flight-route data — see data_access.load_direct_flights() — shown
# both as a table and, since routes are inherently geographic, as lines
# on a map.
st.subheader("Direct flights between them")
flight_rows = []
connected_pairs = []
for city_a, city_b in itertools.combinations(names, 2):
    a_to_b = city_b in direct_flights_from(flights, city_a)
    b_to_a = city_a in direct_flights_from(flights, city_b)
    is_connected = a_to_b or b_to_a
    flight_rows.append({"Route": f"{city_a} - {city_b}", "Direct flight tracked": "Yes" if is_connected else "No"})
    if is_connected:
        connected_pairs.append((city_a, city_b))
st.dataframe(flight_rows, width="stretch", hide_index=True)

st.subheader("Flight connections on the map")
map_fig = go.Figure()
for city_a, city_b in connected_pairs:
    row_a = subset[subset["city_name"] == city_a].iloc[0]
    row_b = subset[subset["city_name"] == city_b].iloc[0]
    map_fig.add_trace(go.Scattermap(
        lat=[row_a["latitude"], row_b["latitude"]],
        lon=[row_a["longitude"], row_b["longitude"]],
        mode="lines", line=dict(width=2, color=BLUE), showlegend=False,
        hoverinfo="skip",
    ))
map_fig.add_trace(go.Scattermap(
    lat=subset["latitude"], lon=subset["longitude"],
    mode="markers+text", text=subset["city_name"], textposition="top right",
    marker=dict(size=12, color=GREEN), showlegend=False,
    hovertext=subset["city_name"], hoverinfo="text",
))
map_fig.update_layout(
    map=dict(style="open-street-map", zoom=1, center=dict(lat=subset["latitude"].mean(), lon=subset["longitude"].mean())),
    height=450, margin=dict(l=0, r=0, t=0, b=0),
)
st.plotly_chart(map_fig, width="stretch")
if not connected_pairs:
    st.caption("No direct flights tracked between any of the selected cities — the map shows their locations only.")
