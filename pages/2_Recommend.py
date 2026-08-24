import os
import sys

import streamlit as st

# See data_access.py for why src/ needs to be added to sys.path here.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data_access import load_cities
from recommend import recommend
from theme import score_badge_html

st.set_page_config(page_title="Recommend", page_icon="🎯", layout="wide")
st.title("🎯 Recommend")
st.caption("Tell us what matters to you, and we'll find your closest matches.")

cities = load_cities()
if cities.empty:
    st.warning("No data yet — see README.md for setup steps.")
    st.stop()

st.subheader("How much do you care about each of these?")
col1, col2 = st.columns(2)
with col1:
    weather = st.slider("Warm weather", 0, 100, 75)
    accessibility = st.slider("Being easy to fly to", 0, 100, 50)
    culture = st.slider("Culture and heritage", 0, 100, 50)
with col2:
    cost = st.slider("Being cheap", 0, 100, 55)
    tourism = st.slider("Being a popular destination", 0, 100, 40)

preferences = {
    "weather_score": weather,
    "accessibility_score": accessibility,
    "culture_score": culture,
    "cost_score": cost,
    "tourism_score": tourism,
}

results = recommend(preferences, top_n=8, cities=cities)

st.subheader("Your top matches")
for _, row in results.iterrows():
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        c1.markdown(f"### {row['city_name']}, {row['country_name']}")
        c2.markdown(score_badge_html(row["similarity"] * 100, "%"), unsafe_allow_html=True)
        st.progress(min(max(row["overall_score"] / 100, 0), 1), text=f"Overall score: {row['overall_score']:.0f}/100")
