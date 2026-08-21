import streamlit as st

from data_access import load_cities

st.set_page_config(page_title="Explore", page_icon="🔎", layout="wide")
st.title("🔎 Explore all destinations")
st.caption("Filter every city in the database by budget, weather, and culture.")

cities = load_cities()
if cities.empty:
    st.warning("No data yet — see README.md for setup steps.")
    st.stop()

with st.sidebar:
    st.header("Filters")
    countries = st.multiselect("Country", sorted(cities["country_name"].unique()))
    min_weather = st.slider("Minimum weather score", 0, 100, 0)
    min_culture = st.slider("Minimum culture score", 0, 100, 0)
    min_cost = st.slider("Minimum cost score (higher = cheaper)", 0, 100, 0)

filtered = cities.copy()
if countries:
    filtered = filtered[filtered["country_name"].isin(countries)]
filtered = filtered[
    (filtered["weather_score"] >= min_weather)
    & (filtered["culture_score"] >= min_culture)
    & (filtered["cost_score"] >= min_cost)
]

st.write(f"**{len(filtered)}** of {len(cities)} cities match your filters.")
st.dataframe(
    filtered[
        ["city_name", "country_name", "overall_score", "weather_score",
         "accessibility_score", "culture_score", "cost_score"]
    ].sort_values("overall_score", ascending=False),
    use_container_width=True, hide_index=True,
)

st.download_button(
    "Download results as CSV",
    data=filtered.to_csv(index=False),
    file_name="filtered_cities.csv",
    mime="text/csv",
)
