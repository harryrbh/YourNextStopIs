import itertools
import os
import sys

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dataAccess import directFlightsFrom, loadCities, loadDirectFlights
from distanceCalculator import distanceBetweenKm
from displayLabels import friendlyNames, scoreLabels, flagEmoji
from themeStyles import blueColor, greenColor, palette, injectCss

st.set_page_config(page_title="Compare", layout="wide")
injectCss()
st.title("Compare")

cities = loadCities()
flights = loadDirectFlights()
if cities.empty:
    st.warning("No data found. Run the setup steps in README.md.")
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
scoreColumns = list(scoreLabels.keys())
scoreLabelNames = list(scoreLabels.values())

st.subheader("Score comparison")
figure = go.Figure()
for cityIndex, (_, row) in enumerate(subset.iterrows()):
    scoreValues = [row[scoreName] for scoreName in scoreColumns]
    scoreValues += scoreValues[:1]
    color = palette[cityIndex % len(palette)]
    label = f"{flagEmoji(row.get('iso2', ''))} {row['city_name']}"
    figure.add_trace(go.Scatterpolar(
        r=scoreValues, theta=scoreLabelNames + [scoreLabelNames[0]],
        fill="toself", name=label, line_color=color,
    ))
figure.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
    height=480, margin=dict(t=30, b=10),
)
st.plotly_chart(figure, width="stretch")

st.subheader("Side-by-side scores")
table = subset.set_index("city_name")[["country_name", "overall_score"] + scoreColumns].copy()
for columnName in ["overall_score"] + scoreColumns:
    table[columnName] = table[columnName].round(0)
table = table.T
table.index = table.index.map(lambda scoreName: friendlyNames.get(scoreName, scoreName))
table = table.fillna("N/A").astype(str)
st.dataframe(table, width="stretch")

# Real-world distances between each pair, calculated with geopy
st.subheader("Distance between cities")
distanceRows = []
for cityA, cityB in itertools.combinations(names, 2):
    rowA = subset[subset["city_name"] == cityA].iloc[0]
    rowB = subset[subset["city_name"] == cityB].iloc[0]
    distanceKm = distanceBetweenKm(rowA["latitude"], rowA["longitude"], rowB["latitude"], rowB["longitude"])
    distanceRows.append({"City A": cityA, "City B": cityB, "Distance (km)": round(distanceKm)})
st.dataframe(distanceRows, width="stretch", hide_index=True)

# Real flight-route data
st.subheader("Direct flights between them")
flightRows = []
connectedPairs = []
for cityA, cityB in itertools.combinations(names, 2):
    aToB = cityB in directFlightsFrom(flights, cityA)
    bToA = cityA in directFlightsFrom(flights, cityB)
    isConnected = aToB or bToA
    flightRows.append({"Route": f"{cityA} - {cityB}", "Direct flight tracked": "Yes" if isConnected else "No"})
    if isConnected:
        connectedPairs.append((cityA, cityB))
st.dataframe(flightRows, width="stretch", hide_index=True)

st.subheader("Flight connections on the map")
mapFig = go.Figure()
for cityA, cityB in connectedPairs:
    rowA = subset[subset["city_name"] == cityA].iloc[0]
    rowB = subset[subset["city_name"] == cityB].iloc[0]
    mapFig.add_trace(go.Scattermap(
        lat=[rowA["latitude"], rowB["latitude"]],
        lon=[rowA["longitude"], rowB["longitude"]],
        mode="lines", line=dict(width=2, color=blueColor), showlegend=False,
        hoverinfo="skip",
    ))
mapFig.add_trace(go.Scattermap(
    lat=subset["latitude"], lon=subset["longitude"],
    mode="markers+text", text=subset["city_name"], textposition="top right",
    marker=dict(size=12, color=greenColor), showlegend=False,
    hovertext=subset["city_name"], hoverinfo="text",
))
mapFig.update_layout(
    map=dict(style="open-street-map", zoom=1, center=dict(lat=subset["latitude"].mean(), lon=subset["longitude"].mean())),
    height=450, margin=dict(l=0, r=0, t=0, b=0),
)
st.plotly_chart(mapFig, width="stretch")
if not connectedPairs:
    st.caption("No direct flights between the selected cities.")
