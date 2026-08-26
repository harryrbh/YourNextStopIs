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

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from data_access import load_cities
from labels import flag_emoji, friendly
from regression import feature_importance, fit_model, load_training_data
from theme import COLORSCALE, GREEN, inject_css

st.set_page_config(page_title="City Breaks", page_icon="🧭", layout="wide")
inject_css()


def main():
    st.title("🧭 City Breaks")
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
        custom_data=["flag", "country_name", "hover_score", "hover_temp", "top_attraction", "category"],
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
    st.plotly_chart(fig, use_container_width=True)

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
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("📈 What drives a city's popularity?"):
        st.caption(
            "A regression model, trained on these 46 cities, estimating which "
            "attributes best predict yearly visitor numbers."
        )
        try:
            data = load_training_data()
            model, scaler, r2 = fit_model(data)
            importance = feature_importance(model)
            importance["direction"] = importance["effect"].apply(lambda x: "Increases visitors" if x > 0 else "Decreases visitors")
            fig3 = px.bar(
                importance, x="effect", y="feature", orientation="h", color="direction",
                color_discrete_map={"Increases visitors": GREEN, "Decreases visitors": "#EF4444"},
                labels={"effect": "Effect on visitor numbers", "feature": ""},
                height=300,
            )
            fig3.update_layout(margin=dict(l=0, r=10, t=10, b=0))
            st.plotly_chart(fig3, use_container_width=True)
            st.caption(f"Model fit: R² = {r2:.2f} (small sample — treat as illustrative, not exact).")
        except Exception:
            st.info("Not enough data yet to train the model — run the setup steps first.")

    st.info("Use the sidebar to explore, get a recommendation, or compare cities.")


if __name__ == "__main__":
    main()
