# City Break Recommender

Recommends city-break destinations using real flight-route data,
sample weather/culture/tourism data, PostgreSQL, and two machine
learning techniques (K-Means clustering + a KNN recommender), served
through a Streamlit app.

> Building this project yourself from an empty folder, including every
> `git` command? See **[SETUP_GUIDE.md](SETUP_GUIDE.md)**. This file
> just covers running what's already here.

## Requirements

- Python 3.10+
- PostgreSQL (or Docker, which includes it — see below)

## Option A: Run with Docker (recommended)

This starts both the database and the app for you.

```bash
docker compose up --build
```

Then, in a **second terminal**, load the data (only needs doing once):

```bash
docker compose exec app python src/load_data.py
docker compose exec app python src/build_features.py
docker compose exec app python src/cluster.py
```

Open **http://localhost:8501**.

Stop everything with `docker compose down` (add `-v` to also delete
the database's saved data).

## Option B: Run locally, without Docker

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up your database connection
cp .env.example .env
# edit .env if your PostgreSQL username/password/port are different

# 4. Make sure PostgreSQL is running, then create the database
#    (skip this if the database already exists)
psql -U postgres -c "CREATE DATABASE city_breaks;"

# 5. Create the tables, load data, build features, run clustering
python src/db.py
python src/load_data.py
python src/build_features.py
python src/cluster.py

# 6. Run the app
streamlit run app.py
```

Open **http://localhost:8501**.

## Project layout

```
city-break-simple/
├── app.py               # Streamlit home page (run this)
├── data_access.py        # shared, cached database query used by every page
├── pages/                 # each file here becomes a page in the sidebar
│   ├── 1_Explore.py
│   ├── 2_Recommend.py
│   ├── 3_Compare.py
│   └── 4_About.py
├── src/
│   ├── db.py               # database connection (one function)
│   ├── load_data.py         # reads data/*.csv, inserts into PostgreSQL
│   ├── build_features.py    # turns raw data into 0-100 scores
│   ├── cluster.py            # K-Means: groups cities into travel profiles
│   └── recommend.py          # KNN: matches your preferences to cities
├── data/                     # the CSV files load_data.py reads
├── sql/schema.sql             # database table definitions
├── tests/                     # pytest tests
├── Dockerfile
└── compose.yaml
```

## Re-running the pipeline

Whenever you change `data/*.csv` or the scoring logic, re-run:

```bash
python src/load_data.py        # only if the CSVs changed
python src/build_features.py   # always, after any change
python src/cluster.py          # optional — refreshes the cluster groups
```

`build_features.py` recalculates the whole `city_features` table from
scratch each time, so it's always safe to re-run.

## Data note

The airport and route data in `data/airports.csv` and
`data/routes.csv` is **real**, from the
[OpenFlights](https://openflights.org/data.html) project. The
country/city/weather/culture/tourism data is a small **hand-picked
sample** (see `pages/4_About.py` in the app for the full list) — it
exists so you can run this project immediately without needing API
keys. Swapping in real data from REST Countries, GeoNames, Open-Meteo
and the World Bank (all free, no key needed except optionally
GeoNames) is a good next step once you're comfortable with how
`src/load_data.py` works — the pattern (read → clean → insert) stays
the same, you'd just add a script that fetches from those APIs instead
of reading a CSV.

## Changing what the recommender prioritises

Open `src/build_features.py` and edit the `WEIGHTS` dictionary near
the top — it's a plain weighted average, nothing hidden.
