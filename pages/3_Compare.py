import plotly.graph_objects as go
import streamlit as st

from data_access import load_cities

st.set_page_config(page_title="Compare", page_icon="⚖️", layout="wide")
st.title("⚖️ Compare cities side by side")

cities = load_cities()
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

subset = cities[cities["city_name"].isin(names)]
score_cols = ["weather_score", "accessibility_score", "culture_score", "cost_score", "tourism_score"]

st.subheader("Score comparison")
fig = go.Figure()
for _, row in subset.iterrows():
    values = [row[c] for c in score_cols]
    labels = [c.replace("_score", "").title() for c in score_cols]
    fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=labels + [labels[0]], fill="toself", name=row["city_name"]))
fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), height=500)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Table")
table = subset.set_index("city_name")[["country_name", "overall_score"] + score_cols].T
st.dataframe(table, use_container_width=True)
