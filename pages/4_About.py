import streamlit as st

st.set_page_config(page_title="About", page_icon="ℹ️", layout="wide")
st.title("ℹ️ About this project")

st.markdown(
    """
### What this is

A city-break recommender: real airport/flight-route data plus a small
sample of city/weather/culture data, combined into scores, then used
to cluster and recommend destinations.

### Data

| Source | What we use it for | Real or sample? |
|---|---|---|
| **OpenFlights** | Airports and flight routes | **Real** — downloaded from the official OpenFlights GitHub repo |
| Country/city facts | Population, GDP, coordinates | Sample — a hand-picked set of ~35 countries and ~46 cities |
| Weather | Monthly temperature & rainfall | Sample — rough climate estimates, not live forecasts |
| Culture | Heritage sites & attraction counts | Sample — rough estimates |
| Tourism | Yearly visitor arrivals | Sample — one indicative year per country |

The sample data exists so the project runs immediately without needing
API keys. See `README.md` for how to plug in real APIs (REST
Countries, GeoNames, Open-Meteo, World Bank) instead.

### How the scoring works

Every city gets five scores, each rescaled to 0-100:

- **Weather** — how close to ~22°C with low rainfall, averaged over the year
- **Accessibility** — number of airports/routes, plus how "central" the
  airport is in the flight network (calculated with NetworkX)
- **Culture** — heritage sites and attractions
- **Cost** — inverse of GDP per capita (higher score = cheaper)
- **Tourism** — how many visitors the country gets

These combine into one **overall score** using a plain weighted
average — see the `WEIGHTS` dictionary at the top of
`src/build_features.py` if you want to change the balance.

### The two machine-learning pieces

- **K-Means clustering** (`src/cluster.py`) groups cities into 4
  similar "travel profiles".
- **K-Nearest-Neighbours with cosine similarity** (`src/recommend.py`)
  matches your preferences to the closest cities.

### Built with

Python, pandas, scikit-learn, NetworkX, PostgreSQL, Streamlit, Docker.
"""
)
