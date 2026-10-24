"""The app's home page."""
import os
import sys

import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dataAccess import loadCities
from displayLabels import flagEmoji
from themeStyles import colorscale, injectCss

st.set_page_config(page_title="City Breaks", layout="wide")
injectCss()


def main():
    st.title("City Breaks")
    st.caption("Compare city break destinations by weather, flights, culture, cost and popularity.")

    try:
        cities = loadCities()
    except Exception as error:
        st.error(
            f"Could not open the database. Run the setup steps in README.md. Details: {error}"
        )
        st.stop()

    if cities.empty:
        st.warning("No data found. Run the setup steps in README.md.")
        st.stop()

    citiesColumn, countriesColumn, scoreColumn = st.columns(3)
    citiesColumn.metric("Cities", len(cities))
    countriesColumn.metric("Countries", cities["country_name"].nunique())
    scoreColumn.metric("Average score", f"{cities['overall_score'].mean():.0f}/100")

    st.subheader("Explore the map")
    st.caption("Colour shows overall score and size shows tourist arrivals.")

    mapData = cities.copy()
    mapData["flag"] = mapData["iso2"].apply(flagEmoji)
    mapData["hover_temp"] = mapData["avg_temperature_c"].round(1)
    mapData["hover_score"] = mapData["overall_score"].round(0)

    mapFigure = px.scatter_map(
        mapData,
        lat="latitude", lon="longitude",
        color="overall_score", size="tourist_arrivals",
        color_continuous_scale=colorscale,
        size_max=22, zoom=1, height=560,
        hover_name="city_name",
        custom_data=["flag", "country_name", "hover_score", "hover_temp", "attraction_1", "category"],
    )
    mapFigure.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b> %{customdata[0]}<br>"
            "%{customdata[1]}<br>"
            "Overall score: %{customdata[2]}/100<br>"
            "Avg. temperature: %{customdata[3]}°C<br>"
            "Top attraction: %{customdata[4]}<br>"
            "%{customdata[5]}<extra></extra>"
        )
    )
    mapFigure.update_layout(
        map_style="open-street-map",
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(title="Score"),
    )
    st.plotly_chart(mapFigure, width="stretch")

    st.subheader("Browse by travel style")
    categories = sorted(cities["category"].dropna().unique())
    categoryColumns = st.columns(len(categories)) if categories else []
    for metricColumn, category in zip(categoryColumns, categories):
        count = (cities["category"] == category).sum()
        metricColumn.metric(category, f"{count} cities")

    st.subheader("Top 10 cities")
    topTenCities = cities.sort_values("overall_score", ascending=False).head(10)
    topCitiesFigure = px.bar(
        topTenCities.sort_values("overall_score"),
        x="overall_score", y="city_name", orientation="h",
        color="overall_score", color_continuous_scale=colorscale,
        labels={"overall_score": "Overall score", "city_name": ""},
        height=420,
    )
    topCitiesFigure.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=10, t=10, b=0))
    st.plotly_chart(topCitiesFigure, width="stretch")

    st.info(
        "Use the sidebar to explore, compare or get recommendations."
    )


main()
