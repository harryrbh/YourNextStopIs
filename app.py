"""
app.py — the app's home page.

Run it with:
    streamlit run app.py

Streamlit automatically turns every file in pages/ into an extra page
in the sidebar — that's the only "magic" in this project. Everything
else is plain Python.
"""
import os
import sys

import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from data_access import load_cities
from labels import flag_emoji
from theme import COLORSCALE, inject_css

st.set_page_config(page_title="City Breaks", layout="wide")
inject_css()


def main():
    st.title("City Breaks")
    st.caption("Find your next short break using real airport, weather and travel data.")

    try:
        cities = load_cities()
    except Exception as e:
        st.error(
            "Couldn't open the database. Have you run `python src/db.py`, "
            f"`python src/load_data.py` and `python src/build_features.py` yet?\n\nDetails: {e}"
        )
        st.stop()

    if cities.empty:
        st.warning("No data found. Run the setup steps in README.md first.")
        st.stop()

    col1, col2, col3 = st.columns(3)
    col1.metric("Cities", len(cities))
    col2.metric("Countries", cities["country_name"].nunique())
    col3.metric("Average score", f"{cities['overall_score'].mean():.0f}/100")

    st.subheader("Explore the map")
    st.caption("Scroll to zoom, drag to pan. Hover a city for details.")

    map_df = cities.copy()
    map_df["flag"] = map_df["iso2"].apply(flag_emoji)
    map_df["hover_temp"] = map_df["avg_temperature_c"].round(1)
    map_df["hover_score"] = map_df["overall_score"].round(0)

    fig = px.scatter_map(
        map_df,
        lat="latitude", lon="longitude",
        color="overall_score", size="tourist_arrivals",
        color_continuous_scale=COLORSCALE,
        size_max=22, zoom=1, height=560,
        hover_name="city_name",
        custom_data=["flag", "country_name", "hover_score", "hover_temp", "attraction_1", "category"],
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{hovertext}</b> %{customdata[0]}<br>"
            "%{customdata[1]}<br>"
            "Overall score: %{customdata[2]}/100<br>"
            "Avg. temperature: %{customdata[3]}°C<br>"
            "Top attraction: %{customdata[4]}<br>"
            "%{customdata[5]}<extra></extra>"
        )
    )
    fig.update_layout(
        map_style="open-street-map",
        margin=dict(l=0, r=0, t=0, b=0),
        coloraxis_colorbar=dict(title="Score"),
    )
    st.plotly_chart(fig, width="stretch")

    st.subheader("Browse by travel style")
    categories = sorted(cities["category"].dropna().unique())
    cols = st.columns(len(categories)) if categories else []
    for col, cat in zip(cols, categories):
        count = (cities["category"] == cat).sum()
        col.metric(cat, f"{count} cities")

    st.subheader("Top 10 right now")
    top10 = cities.sort_values("overall_score", ascending=False).head(10)
    fig2 = px.bar(
        top10.sort_values("overall_score"),
        x="overall_score", y="city_name", orientation="h",
        color="overall_score", color_continuous_scale=COLORSCALE,
        labels={"overall_score": "Overall score", "city_name": ""},
        height=420,
    )
    fig2.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=10, t=10, b=0))
    st.plotly_chart(fig2, width="stretch")

    st.info(
        "Use the sidebar to explore, get a recommendation, compare cities, "
        "see tourism trends, or look up full details for one city."
    )


if __name__ == "__main__":
    main()
