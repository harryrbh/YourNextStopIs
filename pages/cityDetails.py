import os
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dataAccess import (
    directFlightsFrom,
    loadCities,
    loadCountryIndicators,
    loadDirectFlights,
    loadMonthlyWeather,
)
from displayLabels import flagImageHtml
from recommendSimilarCities import mostSimilarCities
from themeStyles import blueColor, greenColor, injectCss

monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

st.set_page_config(page_title="City Details", layout="wide")
injectCss()
st.title("City Details")
st.caption("Scores, weather, culture and flights for one city.")

cities = loadCities()
flights = loadDirectFlights()
if cities.empty:
    st.warning("No data found. Run the setup steps in README.md.")
    st.stop()

cityName = st.selectbox("Choose a city", sorted(cities["city_name"].unique()))
row = cities[cities["city_name"] == cityName].iloc[0]
cityId = int(row["city_id"])

# Header
header = st.columns([1, 5])
header[0].markdown(flagImageHtml(row["iso2"], height=40), unsafe_allow_html=True)
header[1].markdown(f"## {row['city_name']}, {row['country_name']}")
st.caption(f"{row['region']} · Population {row['population']:,.0f}")

scoreColumns = st.columns(6)
scoreColumns[0].metric("Overall score", f"{row['overall_score']:.0f}/100")
scoreColumns[1].metric("Weather", f"{row['weather_score']:.0f}")
scoreColumns[2].metric("Ease of travel", f"{row['accessibility_score']:.0f}")
scoreColumns[3].metric("Culture", f"{row['culture_score']:.0f}")
scoreColumns[4].metric("Affordability", f"{row['cost_score']:.0f}")
scoreColumns[5].metric("Popularity", f"{row['tourism_score']:.0f}")

priceTierText = f"   |   **Price tier:** {row['price_tier']}" if pd.notna(row.get("price_tier")) else ""
st.markdown(f"**Travel style:** {row['category']}{priceTierText}")
st.caption(
    "Travel style groups cities with similar scores. Price tier is estimated from country GDP per person."
)

st.divider()

# Location & country context
leftColumn, rightColumn = st.columns(2)
with leftColumn:
    st.subheader("Location")
    st.write(f"Latitude / longitude: {row['latitude']:.2f}, {row['longitude']:.2f}")
    st.write(f"Administrative region: {row['region']}")
    st.write(f"City population: {row['population']:,.0f}")

with rightColumn:
    st.subheader("Country indicators")
    country = loadCountryIndicators(cityId)
    if not country.empty:
        countryRow = country.iloc[0]
        st.write(f"Country population: {countryRow['population']:,.0f}" if pd.notna(countryRow["population"]) else "Country population: unavailable")
        if pd.notna(countryRow["gdp_per_capita"]):
            st.write(f"GDP per person: ${countryRow['gdp_per_capita']:,.0f}")
            st.write(f"Estimated total GDP: ${countryRow['gdp_per_capita'] * countryRow['population']:,.0f}")
        else:
            st.write("GDP per person: unavailable")
        st.write(
            f"Urban population: {countryRow['urban_population_pct']:.0f}%"
            if pd.notna(countryRow["urban_population_pct"]) else "Urban population: unavailable"
        )
        st.caption("Total GDP is GDP per person multiplied by country population.")

st.divider()

# Weather
st.subheader("Weather through the year")
monthly = loadMonthlyWeather(cityId)
if not monthly.empty:
    monthly = monthly.copy()
    monthly["month_name"] = monthly["month"].apply(lambda monthNumber: monthNames[monthNumber - 1])
    figure = go.Figure()
    figure.add_trace(go.Bar(
        x=monthly["month_name"], y=monthly["precipitation_mm"], name="Rainfall (mm)",
        marker_color=blueColor, yaxis="y2", opacity=0.5,
    ))
    figure.add_trace(go.Scatter(
        x=monthly["month_name"], y=monthly["temperature_c"], name="Temperature (°C)",
        line=dict(color=greenColor, width=3),
    ))
    figure.update_layout(
        height=350, margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(title="Temperature (°C)"),
        yaxis2=dict(title="Rainfall (mm)", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.15),
    )
    st.plotly_chart(figure, width="stretch")

st.divider()

# Culture & heritage
st.subheader("Culture & heritage")
st.write(f"Heritage sites nearby: {int(row['heritage_sites'])}")
st.write(f"Attractions nearby: {int(row['attractions'])}")
st.markdown("**Best-known attractions:**")
for attractionNumber, columnContainer in enumerate(["attraction_1", "attraction_2", "attraction_3"], start=1):
    if pd.notna(row.get(columnContainer)):
        st.write(f"{attractionNumber}. {row[columnContainer]}")
st.caption(
    "Attraction counts cover sights within 10 km of the city centre."
)

st.divider()

# Airports & flights
st.subheader("Airports & flights")
leftColumn, rightColumn = st.columns(2)
with leftColumn:
    st.write(f"Airports nearby: {int(row['airport_count'])}")
    st.write(f"Flight routes: {int(row['route_count'])}")
    st.write(f"Flight network score: {row['connectivity']:.2f}")
    if pd.notna(row.get("nearest_airport_name")):
        st.write(f"Nearest airport: {row['nearest_airport_name']} ({row['nearest_airport_km']:.1f} km away)")
with rightColumn:
    destinations = directFlightsFrom(flights, cityName)
    st.write(f"Direct flights to {len(destinations)} other cities:")
    st.write(", ".join(destinations) if destinations else "None")

# Map: this city plus every direct-flight destination
destinationRows = cities[cities["city_name"].isin(destinations)]
mapFig = go.Figure()
for _, dest in destinationRows.iterrows():
    mapFig.add_trace(go.Scattermap(
        lat=[row["latitude"], dest["latitude"]], lon=[row["longitude"], dest["longitude"]],
        mode="lines", line=dict(width=1, color=blueColor), opacity=0.6, showlegend=False, hoverinfo="skip",
    ))
if not destinationRows.empty:
    mapFig.add_trace(go.Scattermap(
        lat=destinationRows["latitude"], lon=destinationRows["longitude"], mode="markers",
        marker=dict(size=8, color=blueColor), text=destinationRows["city_name"], hoverinfo="text", showlegend=False,
    ))
mapFig.add_trace(go.Scattermap(
    lat=[row["latitude"]], lon=[row["longitude"]], mode="markers+text",
    marker=dict(size=16, color=greenColor), text=[cityName], textposition="top right",
    hoverinfo="text", showlegend=False,
))
mapFig.update_layout(
    map=dict(style="open-street-map", zoom=1, center=dict(lat=row["latitude"], lon=row["longitude"])),
    height=420, margin=dict(l=0, r=0, t=0, b=0),
)
st.plotly_chart(mapFig, width="stretch")

st.divider()

# Most similar cities
st.subheader("Most similar cities")
st.caption("The three cities with the closest scores to this one.")
similar = mostSimilarCities(cityId, numberOfCities=3, cities=cities)
similarColumns = st.columns(3)
for columnContainer, (_, similarRow) in zip(similarColumns, similar.iterrows()):
    with columnContainer:
        columnContainer.markdown(
            f"{flagImageHtml(similarRow['iso2'])} **{similarRow['city_name']}**, {similarRow['country_name']}",
            unsafe_allow_html=True,
        )
        columnContainer.write(f"Similarity: {similarRow['similarity']*100:.0f}%")
        columnContainer.write(f"Overall score: {similarRow['overall_score']:.0f}/100")
