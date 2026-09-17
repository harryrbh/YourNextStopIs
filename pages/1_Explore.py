import os
import sys

import plotly.express as px
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from components import render_city_card
from data_access import direct_flights_from, load_cities, load_direct_flights
from distance import add_distance_column
from labels import friendly
from theme import COLORSCALE, inject_css

st.set_page_config(page_title="Explore", layout="wide")
inject_css()
st.title("Explore")

cities = load_cities()
flights = load_direct_flights()
if cities.empty:
    st.warning("No data yet — see README.md for setup steps.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    search = st.text_input("Search by city name")
    categories = st.multiselect("Travel style", sorted(cities["category"].dropna().unique()))
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
if categories:
    filtered = filtered[filtered["category"].isin(categories)]
if countries:
    filtered = filtered[filtered["country_name"].isin(countries)]
filtered = filtered[
    (filtered["weather_score"] >= min_weather)
    & (filtered["culture_score"] >= min_culture)
    & (filtered["cost_score"] >= min_cost)
]

if reference_city != "(none)":
    ref_row = cities[cities["city_name"] == reference_city].iloc[0]
    filtered = add_distance_column(filtered, ref_row["latitude"], ref_row["longitude"])
    filtered = filtered.sort_values("distance_km")
else:
    filtered = filtered.sort_values("overall_score", ascending=False)

st.write(f"**{len(filtered)}** of {len(cities)} cities match your filters.")

view = st.radio("View as", ["Cards", "Table"], horizontal=True, label_visibility="collapsed")

if view == "Cards":
    cols_per_row = 3
    rows = [filtered.iloc[i:i + cols_per_row] for i in range(0, min(len(filtered), 30), cols_per_row)]
    for chunk in rows:
        cols = st.columns(cols_per_row)
        for col, (_, row) in zip(cols, chunk.iterrows()):
            with col:
                render_city_card(row, direct_flights=direct_flights_from(flights, row["city_name"]))
    if len(filtered) > 30:
        st.caption(f"Showing the first 30 of {len(filtered)} matches. Narrow your filters to see fewer, or switch to Table view for all of them.")
else:
    display_cols = [
        "city_name", "country_name", "category", "overall_score", "weather_score",
        "accessibility_score", "culture_score", "cost_score",
    ]
    if "distance_km" in filtered.columns:
        display_cols.append("distance_km")

    if not filtered.empty:
        top = filtered.head(15).iloc[::-1]
        fig = px.bar(
            top, x="overall_score", y="city_name", orientation="h",
            color="overall_score", color_continuous_scale=COLORSCALE,
            labels={"overall_score": "Overall score", "city_name": ""},
            height=max(300, len(top) * 32),
        )
        fig.update_layout(coloraxis_showscale=False, margin=dict(l=0, r=10, t=10, b=0))
        st.plotly_chart(fig, width="stretch")

    table = filtered[display_cols].copy()
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
