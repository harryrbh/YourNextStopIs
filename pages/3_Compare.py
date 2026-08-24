import itertools
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data_access import load_cities
from distance import km_between
from labels import FRIENDLY_NAMES, SCORE_LABELS
from theme import BLUE, GREEN, GRAY

st.set_page_config(page_title="Compare", page_icon="⚖️", layout="wide")
st.title("⚖️ Compare")

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

subset = cities[cities["city_name"].isin(names)].set_index("city_name").loc[names].reset_index()
score_cols = list(SCORE_LABELS.keys())
score_labels = list(SCORE_LABELS.values())
palette = [GREEN, BLUE, GRAY, "#F59E0B", "#8B5CF6"]

st.subheader("Score comparison")
angles = np.linspace(0, 2 * np.pi, len(score_cols), endpoint=False).tolist()
angles += angles[:1]

fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
for i, (_, row) in enumerate(subset.iterrows()):
    values = [row[c] for c in score_cols]
    values += values[:1]
    color = palette[i % len(palette)]
    ax.plot(angles, values, color=color, linewidth=2, label=row["city_name"])
    ax.fill(angles, values, color=color, alpha=0.1)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(score_labels)
ax.set_ylim(0, 100)
ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
fig.tight_layout()
st.pyplot(fig)

st.subheader("Side-by-side scores")
table = subset.set_index("city_name")[["country_name", "overall_score"] + score_cols].T
table.index = table.index.map(lambda c: FRIENDLY_NAMES.get(c, c))
st.dataframe(table, use_container_width=True)

# Real-world distances between each pair, calculated with geopy — see distance.py.
if len(names) >= 2:
    st.subheader("Distance between cities")
    rows = []
    for city_a, city_b in itertools.combinations(names, 2):
        row_a = subset[subset["city_name"] == city_a].iloc[0]
        row_b = subset[subset["city_name"] == city_b].iloc[0]
        km = km_between(row_a["latitude"], row_a["longitude"], row_b["latitude"], row_b["longitude"])
        rows.append({"City A": city_a, "City B": city_b, "Distance (km)": round(km)})
    st.dataframe(rows, use_container_width=True, hide_index=True)
