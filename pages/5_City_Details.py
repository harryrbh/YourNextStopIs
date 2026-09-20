import os
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data_access import (
    direct_flights_from,
    load_cities,
    load_country_indicators,
    load_direct_flights,
    load_monthly_weather,
)
from labels import flag_image_html
from recommend import most_similar_cities
from theme import BLUE, GREEN, inject_css

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

st.set_page_config(page_title="City Details", layout="wide")
inject_css()
st.title("City Details")
st.caption("Everything the app knows about one destination, in one place.")

cities = load_cities()
flights = load_direct_flights()
if cities.empty:
    st.warning("No data yet — see README.md for setup steps.")
    st.stop()

city_name = st.selectbox("Choose a city", sorted(cities["city_name"].unique()))
row = cities[cities["city_name"] == city_name].iloc[0]
city_id = int(row["city_id"])

# --- header -----------------------------------------------------------
header = st.columns([1, 5])
header[0].markdown(flag_image_html(row["iso2"], height=40), unsafe_allow_html=True)
header[1].markdown(f"## {row['city_name']}, {row['country_name']}")
st.caption(f"{row['region']} · Population {row['population']:,.0f}")

score_cols = st.columns(6)
score_cols[0].metric("Overall score", f"{row['overall_score']:.0f}/100")
score_cols[1].metric("Weather", f"{row['weather_score']:.0f}")
score_cols[2].metric("Ease of travel", f"{row['accessibility_score']:.0f}")
score_cols[3].metric("Culture", f"{row['culture_score']:.0f}")
score_cols[4].metric("Affordability", f"{row['cost_score']:.0f}")
score_cols[5].metric("Popularity", f"{row['tourism_score']:.0f}")

price_tier_text = f"   |   **Price tier:** {row['price_tier']}" if pd.notna(row.get("price_tier")) else ""
st.markdown(f"**Travel style:** {row['category']}{price_tier_text}")
st.caption(
    "Travel style is an unsupervised grouping (K-Means) of cities with similar scores. "
    "Price tier is a supervised prediction trained on a constructed proxy label — see "
    "src/classify.py for exactly how, and treat both as estimates, not verified facts."
)

st.divider()

# --- location & country context ---------------------------------------
col1, col2 = st.columns(2)
with col1:
    st.subheader("Location")
    st.write(f"Latitude / longitude: {row['latitude']:.2f}, {row['longitude']:.2f}")
    st.write(f"Administrative region: {row['region']}")
    st.write(f"City population: {row['population']:,.0f}")

with col2:
    st.subheader("Country indicators")
    country = load_country_indicators(city_id)
    if not country.empty:
        c = country.iloc[0]
        st.write(f"Country population: {c['population']:,.0f}" if pd.notna(c["population"]) else "Country population: unavailable")
        if pd.notna(c["gdp_per_capita"]):
            st.write(f"GDP per person: ${c['gdp_per_capita']:,.0f}")
            st.write(f"Estimated total GDP: ${c['gdp_per_capita'] * c['population']:,.0f}")
        else:
            st.write("GDP per person: unavailable")
        st.write(
            f"Urban population: {c['urban_population_pct']:.0f}%"
            if pd.notna(c["urban_population_pct"]) else "Urban population: unavailable"
        )
        st.caption("Total GDP is estimated as GDP per person x country population — not an independently reported figure.")

st.divider()

# --- weather ------------------------------------------------------------
st.subheader("Weather through the year")
monthly = load_monthly_weather(city_id)
if not monthly.empty:
    monthly = monthly.copy()
    monthly["month_name"] = monthly["month"].apply(lambda m: MONTH_NAMES[m - 1])
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly["month_name"], y=monthly["precipitation_mm"], name="Rainfall (mm)",
        marker_color=BLUE, yaxis="y2", opacity=0.5,
    ))
    fig.add_trace(go.Scatter(
        x=monthly["month_name"], y=monthly["temperature_c"], name="Temperature (°C)",
        line=dict(color=GREEN, width=3),
    ))
    fig.update_layout(
        height=350, margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(title="Temperature (°C)"),
        yaxis2=dict(title="Rainfall (mm)", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.15),
    )
    st.plotly_chart(fig, width="stretch")

st.divider()

# --- culture & heritage ---------------------------------------------------
st.subheader("Culture & heritage")
st.write(f"Heritage sites nearby: {int(row['heritage_sites'])}")
st.write(f"Total attractions tracked: {int(row['attractions'])}")
st.markdown("**Three largest / best-known attractions:**")
for i, col in enumerate(["attraction_1", "attraction_2", "attraction_3"], start=1):
    if pd.notna(row.get(col)):
        st.write(f"{i}. {row[col]}")
st.caption(
    "Museums, parks, restaurants, railway stations, and other fine-grained points of "
    "interest are not included in this sample dataset — that level of detail needs a "
    "bulk OpenStreetMap extract (see API_GUIDE.md), which this project doesn't ingest."
)

st.divider()

# --- airports & flights -----------------------------------------------------
st.subheader("Airports & flights")
col1, col2 = st.columns(2)
with col1:
    st.write(f"Airports nearby: {int(row['airport_count'])}")
    st.write(f"Flight routes tracked: {int(row['route_count'])}")
    st.write(f"Flight network score: {row['connectivity']:.2f}")
    if pd.notna(row.get("nearest_airport_name")):
        st.write(f"Nearest airport (of any tracked): {row['nearest_airport_name']} ({row['nearest_airport_km']:.1f} km away)")
with col2:
    destinations = direct_flights_from(flights, city_name)
    st.write(f"Direct flights tracked to {len(destinations)} other sample cities:")
    st.write(", ".join(destinations) if destinations else "None tracked")

# map: this city plus every direct-flight destination
dest_rows = cities[cities["city_name"].isin(destinations)]
map_fig = go.Figure()
for _, dest in dest_rows.iterrows():
    map_fig.add_trace(go.Scattermap(
        lat=[row["latitude"], dest["latitude"]], lon=[row["longitude"], dest["longitude"]],
        mode="lines", line=dict(width=1, color=BLUE), opacity=0.6, showlegend=False, hoverinfo="skip",
    ))
if not dest_rows.empty:
    map_fig.add_trace(go.Scattermap(
        lat=dest_rows["latitude"], lon=dest_rows["longitude"], mode="markers",
        marker=dict(size=8, color=BLUE), text=dest_rows["city_name"], hoverinfo="text", showlegend=False,
    ))
map_fig.add_trace(go.Scattermap(
    lat=[row["latitude"]], lon=[row["longitude"]], mode="markers+text",
    marker=dict(size=16, color=GREEN), text=[city_name], textposition="top right",
    hoverinfo="text", showlegend=False,
))
map_fig.update_layout(
    map=dict(style="open-street-map", zoom=1, center=dict(lat=row["latitude"], lon=row["longitude"])),
    height=420, margin=dict(l=0, r=0, t=0, b=0),
)
st.plotly_chart(map_fig, width="stretch")

st.divider()

# --- most similar cities -----------------------------------------------------
st.subheader("Most similar cities")
st.caption("The three cities whose scores are closest to this one overall (weather, ease of travel, culture, affordability, popularity).")
similar = most_similar_cities(city_id, n=3, cities=cities)
sim_cols = st.columns(3)
for col, (_, sim_row) in zip(sim_cols, similar.iterrows()):
    with col:
        col.markdown(
            f"{flag_image_html(sim_row['iso2'])} **{sim_row['city_name']}**, {sim_row['country_name']}",
            unsafe_allow_html=True,
        )
        col.write(f"Similarity: {sim_row['similarity']*100:.0f}%")
        col.write(f"Overall score: {sim_row['overall_score']:.0f}/100")
