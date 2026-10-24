import os
import sys

import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from uiComponents import renderCityCard
from dataAccess import directFlightsFrom, loadCities, loadDirectFlights
from distanceCalculator import addDistanceColumn
from displayLabels import friendly
from themeStyles import colorscale, injectCss

st.set_page_config(page_title="Explore", layout="wide")
injectCss()
st.title("Explore")

cities = loadCities()
flights = loadDirectFlights()
if cities.empty:
    st.warning("No data found. Run the setup steps in README.md.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    search = st.text_input("Search by city name")
    categories = st.multiselect("Travel style", sorted(cities["category"].dropna().unique()))
    priceTiers = st.multiselect("Price tier", sorted(cities["price_tier"].dropna().unique()))
    countries = st.multiselect("Country", sorted(cities["country_name"].unique()))
    minimumWeather = st.slider("Minimum weather score", 0, 100, 0)
    minimumCulture = st.slider("Minimum culture score", 0, 100, 0)
    minimumCost = st.slider("Minimum affordability score", 0, 100, 0)

    st.divider()
    st.caption("Distance from a city you pick")
    referenceCity = st.selectbox("Show distance from", ["(none)"] + sorted(cities["city_name"].unique()))

filtered = cities.copy()
if search:
    filtered = filtered[filtered["city_name"].str.contains(search, case=False, na=False)]
if categories:
    filtered = filtered[filtered["category"].isin(categories)]
if priceTiers:
    filtered = filtered[filtered["price_tier"].isin(priceTiers)]
if countries:
    filtered = filtered[filtered["country_name"].isin(countries)]
filtered = filtered[
    (filtered["weather_score"] >= minimumWeather)
    & (filtered["culture_score"] >= minimumCulture)
    & (filtered["cost_score"] >= minimumCost)
]

if referenceCity != "(none)":
    refRow = cities[cities["city_name"] == referenceCity].iloc[0]
    filtered = addDistanceColumn(filtered, refRow["latitude"], refRow["longitude"])
    filtered = filtered.sort_values("distance_km")
else:
    filtered = filtered.sort_values("overall_score", ascending=False)

st.write(f"**{len(filtered)}** of {len(cities)} cities match your filters.")

view = st.radio("View as", ["Cards", "Table"], horizontal=True, label_visibility="collapsed")

if view == "Cards":
    columnsPerRow = 3
    cardRows = [filtered.iloc[rowStart:rowStart + columnsPerRow] for rowStart in range(0, min(len(filtered), 30), columnsPerRow)]
    for chunk in cardRows:
        columnContainers = st.columns(columnsPerRow)
        for columnContainer, (_, row) in zip(columnContainers, chunk.iterrows()):
            with columnContainer:
                renderCityCard(row, directFlights=directFlightsFrom(flights, row["city_name"]))
    if len(filtered) > 30:
        st.caption(f"Showing the first 30 of {len(filtered)} matches. Use Table view to see all of them.")
else:
    displayColumns = [
        "city_name", "country_name", "category", "price_tier", "overall_score", "weather_score",
        "accessibility_score", "culture_score", "cost_score",
    ]
    if "distance_km" in filtered.columns:
        displayColumns.append("distance_km")

    if not filtered.empty:
        topCities = filtered.head(15).iloc[::-1]
        figure = px.bar(
            topCities, x="overall_score", y="city_name", orientation="h",
            color="overall_score", color_continuous_scale=colorscale,
            labels={"overall_score": "Overall score", "city_name": ""},
            height=max(300, len(topCities) * 32),
        )
        figure.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=10, t=10, b=0))
        st.plotly_chart(figure, width="stretch")

    table = filtered[displayColumns].copy()
    table.insert(1, "flag_url", filtered["iso2"].str.lower().apply(
        lambda code: f"https://flagcdn.com/w40/{code}.png" if isinstance(code, str) and len(code) == 2 else None
    ))
    st.dataframe(
        friendly(table),
        width="stretch", hide_index=True,
        column_config={"flag_url": st.column_config.ImageColumn("Flag", width="small")},
    )

    st.download_button(
        "Download results as CSV",
        data=filtered.to_csv(index=False),
        file_name="cities.csv",
        mime="text/csv",
    )
