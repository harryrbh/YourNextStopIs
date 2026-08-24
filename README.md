# City Breaks

Recommends city-break destinations using real flight-route data,
sample weather/culture/tourism data, a local SQLite database, and two
machine learning techniques (K-Means clustering + a KNN recommender),
served through a Streamlit app.

> Building this project yourself from an empty folder, including every
> `git` command? See **[SETUP_GUIDE.md](SETUP_GUIDE.md)**. Want to
> swap the sample data for real, live data from four different free
> APIs? See **[API_GUIDE.md](API_GUIDE.md)**. This file just covers
> running what's already here.

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

# 3. Create the database, load data, build features, run clustering
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

## Project layout

```
city-break-simple/
├── app.py               # home page (run this)
├── data_access.py         # shared, cached database query used by every page
├── labels.py               # plain-English names for every column shown on screen
├── theme.py                 # shared colours for charts and badges
├── distance.py               # real-world distance between two coordinates (geopy)
├── pages/                     # each file here becomes a page in the sidebar
│   ├── 1_Explore.py
│   ├── 2_Recommend.py
│   └── 3_Compare.py
├── src/
│   ├── db.py                    # database connection (one function)
│   ├── load_data.py              # reads data/*.csv, inserts into SQLite
│   ├── build_features.py          # turns raw data into 0-100 scores
│   ├── cluster.py                  # K-Means: groups cities into travel profiles
│   ├── recommend.py                 # KNN: matches your preferences to cities
│   └── fetch_*.py                    # optional: pull real data instead of the sample CSVs
├── data/                                # the CSV files load_data.py reads, plus the database file
├── sql/schema.sql                        # database table definitions
├── tests/                                 # pytest tests
├── .streamlit/config.toml                  # app colour theme
└── Dockerfile
```

## Re-running the pipeline

Whenever you change `data/*.csv` or the scoring logic, re-run:

```bash
python src/load_data.py        # only if the CSVs changed
python src/build_features.py   # always, after any change
python src/cluster.py          # optional — refreshes the travel-style groups
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
real data from REST Countries, GeoNames, Open-Meteo and the World
Bank — all free, no key needed.

## Changing what the recommender prioritises

Open `src/build_features.py` and edit the `WEIGHTS` dictionary near
the top — it's a plain weighted average, nothing hidden.

## Changing the colours

Edit `.streamlit/config.toml` (controls Streamlit's own buttons and
sliders) and `theme.py` (controls the matplotlib charts and score
badges) — keep the colours in both roughly matching.
