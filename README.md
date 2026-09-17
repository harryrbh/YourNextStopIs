# City Breaks

Recommends city-break destinations using real flight-route data,
sample weather/culture/tourism data, a local SQLite database, and
machine learning (K-Means clustering, a KNN recommender, a regression
model, and a supervised price-tier classifier), served through a
Streamlit app.

> Want to swap the sample data for real, live data from four
> different free APIs? See **[API_GUIDE.md](API_GUIDE.md)**. Curious
> how Docker actually works in this project, line by line? See
> **[SETUP_GUIDE.md](SETUP_GUIDE.md)**. This file just covers running
> what's already here.

## Requirements

- Python 3.10+
- That's it — no database server to install. The whole database is
  one file (`data/city_breaks.db`), created by the setup steps below.

## Option A: Run locally (recommended — simplest option)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database, load data, and run the models
python src/db.py
python src/load_data.py
python src/build_features.py
python src/cluster.py

# 4. Run the app
streamlit run app.py
```

Open **http://localhost:8501**.

## Option B: Run with Docker

```bash
docker build -t city-breaks .
docker run -p 8501:8501 city-breaks
```

Open **http://localhost:8501**. The image builds its own database
during `docker build`, so there's nothing extra to run afterwards.

If you'd like the database to survive rebuilding the image (rather
than starting fresh every time), mount the `data/` folder from your
own machine instead:
```bash
docker run -p 8501:8501 -v $(pwd)/data:/app/data city-breaks
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for a full explanation of what a
container actually is and what each line of the `Dockerfile` does.

## What's in the app

- **Home** — an interactive, scrollable map of every city (hover for
  weather, top attraction, and travel style), quick browsing by
  travel-style category, and a top-10 chart.
- **Explore** — filter by travel style, price tier, country, or
  score; search by name; sort by distance from a city you pick (using
  `geopy`); view results as photo cards or a table with real flag
  icons.
- **Recommend** — set your preferences on five sliders and get your
  closest-matching cities, each with a match percentage.
- **Compare** — a radar chart, side-by-side scores, real distances
  between cities, and a map showing which of your chosen cities have
  a tracked direct flight between them.
- **Tourism** — visitor numbers and growth by country, and an
  interactive "estimate demand for a destination" calculator powered
  by a regression model.
- **City Details** — a full dossier for one city: location, country
  indicators (GDP, urbanisation), a 12-month weather chart, its three
  best-known attractions, nearest airport, a flight-connections map,
  and its three most similar cities.

City cards try to show a real photo, pulled live from Wikipedia
(`images.py`) — this needs an internet connection at the time the app
runs; if it's unavailable, the card just shows without a photo rather
than erroring.

## Project layout

```
city-break-simple/
├── app.py                    # home page (run this)
├── data_access.py             # shared, cached database queries used by every page
├── components.py               # the reusable "city card" (image, flag, badges, flights)
├── labels.py                    # plain-English names, rounding, and flags for anything shown on screen
├── theme.py                      # shared colours, chart palette, card styling
├── distance.py                    # real-world distance between two coordinates (geopy)
├── images.py                       # fetches a city photo from Wikipedia
├── pages/                            # each file here becomes a page in the sidebar
│   ├── 1_Explore.py
│   ├── 2_Recommend.py
│   ├── 3_Compare.py
│   ├── 4_Tourism.py
│   └── 5_City_Details.py
├── src/
│   ├── db.py                            # database connection (one function)
│   ├── load_data.py                      # reads data/*.csv, inserts into SQLite
│   ├── build_features.py                  # turns raw data into 0-100 scores + nearest airport
│   ├── cluster.py                          # K-Means: unsupervised travel-style categories
│   ├── recommend.py                         # KNN: matches preferences to cities, and city-to-city similarity
│   ├── regression.py                          # predicts visitor numbers from city/country attributes
│   ├── classify.py                              # optional, not run by default — see note below
│   └── fetch_*.py                                # optional: pull real data instead of the sample CSVs
├── data/                                          # the CSV files load_data.py reads, plus the database file
├── sql/schema.sql                                    # database table definitions
├── tests/                                              # pytest tests
├── .streamlit/config.toml                                # app colour theme
└── Dockerfile
```

## Re-running the pipeline

Whenever you change `data/*.csv` or the scoring logic, re-run:

```bash
python src/load_data.py        # only if the CSVs changed
python src/build_features.py   # always, after any change
python src/cluster.py          # refreshes the travel-style categories
```

`build_features.py` recalculates the whole `city_features` table from
scratch each time, so it's always safe to re-run. If you ever want a
completely clean slate, delete `data/city_breaks.db` and start again
from `python src/db.py`.

## Data note

The airport and route data in `data/airports.csv` and
`data/routes.csv` is **real**, from the
[OpenFlights](https://openflights.org/data.html) project. The
country/city/weather/culture/tourism data is a small **hand-picked
sample** — it exists so you can run this project immediately without
needing any accounts or API keys. **See
[API_GUIDE.md](API_GUIDE.md)** for a step-by-step guide to swapping in
real data from countries.dev, GeoNames, Open-Meteo and the World
Bank — all free, no key needed — and for what's honestly missing from
the sample data (museum/park/restaurant-level detail, multi-year
tourism history).

## A note on `classify.py` (not run by default)

`src/classify.py` predicts a Budget/Mid-range/Luxury "price tier" for
each city — a *supervised* model, trained on labels constructed from
a rule (country GDP per person, split into thirds), which the module's
docstring documents in full, including why that's a proxy and not a
verified fact. It's disabled by default in this app's pipeline and UI:
because gdp_per_capita is a country-level number, many cities in the
same country share the exact same value, which can occasionally put
several cities exactly on a tercile boundary — `build_labels()` now
handles that gracefully rather than crashing, but the feature adds
real complexity for a proxy label. If you want it back, run
`python src/classify.py` after `cluster.py`, and re-add the
`price_tier` displays this project previously had in `components.py`,
`pages/1_Explore.py`, and `pages/5_City_Details.py`.

## Changing what the recommender prioritises

Open `src/build_features.py` and edit the `WEIGHTS` dictionary near
the top — it's a plain weighted average, nothing hidden.

## Changing the colours

Edit `.streamlit/config.toml` (controls Streamlit's own buttons and
sliders) and `theme.py` (controls the Plotly charts, score badges,
and card styling) — keep the colours in both roughly matching.
