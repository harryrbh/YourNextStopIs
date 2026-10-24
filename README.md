# City Breaks

Recommends city-break destinations using real flight-route data,
sample weather/culture/tourism data, a local SQLite database, and
machine learning (K-Means clustering, a KNN recommender, a regression
model, and a supervised price-tier classifier), served through a
Streamlit app.

> Want to swap the sample data for real, live data from four
> different free APIs? See **[apiGuide.md](apiGuide.md)**. Curious
> how Docker actually works in this project, line by line? See
> **[setupGuide.md](setupGuide.md)**. This file just covers running
> what's already here.

## Requirements

- Python 3.10+
- That's it — no database server to install. The whole database is
  one file (`data/cityBreaks.db`), created by the setup steps below.

## Option A: Run locally (recommended — simplest option)

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database, load data, and run every model
python src/database.py
python src/loadDataToDatabase.py
python src/buildCityFeatures.py
python src/clusterCities.py
python src/classifyPriceTier.py

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

See [setupGuide.md](setupGuide.md) for a full explanation of what a
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
(`cityImages.py`) — this needs an internet connection at the time the app
runs; if it's unavailable, the card just shows without a photo rather
than erroring.

## Project layout

```
city-break-simple/
├── app.py                    # home page (run this)
├── dataAccess.py             # shared, cached database queries used by every page
├── uiComponents.py               # the reusable "city card" (image, flag, badges, flights)
├── displayLabels.py                    # plain-English names, rounding, and flags for anything shown on screen
├── themeStyles.py                      # shared colours, chart palette, card styling
├── distanceCalculator.py                    # real-world distance between two coordinates (geopy)
├── cityImages.py                       # fetches a city photo from Wikipedia
├── pages/                            # pages registered in app.py
│   ├── homePage.py
│   ├── exploreCities.py
│   ├── recommendCities.py
│   ├── compareCities.py
│   ├── tourismTrends.py
│   └── cityDetails.py
├── src/
│   ├── database.py                            # database connection (one function)
│   ├── loadDataToDatabase.py                      # reads data/*.csv, inserts into SQLite
│   ├── buildCityFeatures.py                  # turns raw data into 0-100 scores + nearest airport
│   ├── clusterCities.py                          # K-Means: unsupervised travel-style categories
│   ├── recommendSimilarCities.py                         # KNN: matches preferences to cities, and city-to-city similarity
│   ├── predictTourismDemand.py                          # predicts visitor numbers from city/country attributes
│   ├── classifyPriceTier.py                              # Budget/Mid-range/Luxury price-tier prediction
│   ├── touristCityList.py, selectCompleteCities.py, httpClient.py
│   └── fetch*.py                                # optional: pull real data instead of the sample CSVs
├── data/                                          # the CSV files loadDataToDatabase.py reads, plus the database file
├── sql/schema.sql                                    # database table definitions
├── tests/                                              # pytest tests
├── .streamlit/config.toml                                # app colour theme
└── Dockerfile
```


## Using real data (250 tourist cities)

The repo ships a 46-city sample so the app runs immediately. To build the real
dataset, follow **[dataSources.md](dataSources.md)** (exactly which extracts to
download and how each file is interpreted). In short:

```bash
python src/fetchCities.py       # ~370 curated tourist candidates, matched to GeoNames
python src/fetchCountries.py    # country facts
python src/fetchTourism.py      # visitor numbers + GDP + urbanisation (World Bank)
python src/fetchWeather.py      # NASA POWER monthly climate normals (1 request/city, resumable)
python src/downloadRawData.py  # GeoNames per-country files, OpenFlights, UNESCO -> data/raw/
python src/fetchAirports.py     # airports + routes; an airport serves every city within 100 km
python src/buildCulture.py      # UNESCO sites + attractions + top-3 sights per city
python src/database.py && python src/loadDataToDatabase.py && python src/buildCityFeatures.py
python src/clusterCities.py && python src/classifyPriceTier.py
```

`loadDataToDatabase.py` keeps the first 250 candidates (in `src/touristCityList.py` order) that have
complete data for every tourist attribute, and prints why each dropped city was dropped.
Full from-scratch build instructions (including git commits): **[setupGuide.md](setupGuide.md)**.

## Re-running the pipeline

Whenever you change `data/*.csv` or the scoring logic, re-run:

```bash
python src/loadDataToDatabase.py        # only if the CSVs changed
python src/buildCityFeatures.py   # always, after any change
python src/clusterCities.py          # refreshes the travel-style categories
python src/classifyPriceTier.py         # refreshes the price-tier predictions
```

`buildCityFeatures.py` recalculates the whole `city_features` table from
scratch each time, so it's always safe to re-run. If you ever want a
completely clean slate, delete `data/cityBreaks.db` and start again
from `python src/database.py`.

## Data note

The airport and route data in `data/airports.csv` and
`data/routes.csv` is **real**, from the
[OpenFlights](https://openflights.org/data.html) project. The
country/city/weather/culture/tourism data is a small **hand-picked
sample** — it exists so you can run this project immediately without
needing any accounts or API keys. **See
[apiGuide.md](apiGuide.md)** for a step-by-step guide to swapping in
real data from countries.dev, GeoNames, Open-Meteo and the World
Bank — all free, no key needed — and for what's honestly missing from
the sample data (museum/park/restaurant-level detail, multi-year
tourism history).

## A note on the two classification-style features

This app has two different ways of grouping cities, and they mean
different things:

- **Travel style** (`clusterCities.py`) is *unsupervised* — K-Means finds
  groups of cities with similar scores and we name each group after
  its most dominant trait. There's no "correct" grouping being
  learned here, just a useful way to browse.
- **Price tier** (`classifyPriceTier.py`) is *supervised* — Budget/Mid-range/
  Luxury labels are first constructed from a rule (country GDP per
  person, split into thirds), then a model (whichever of Logistic
  Regression, a Decision Tree, or Random Forest cross-validates best)
  is trained to predict that label from *other* attributes. The label
  is a proxy, not a verified fact, and the module's docstring explains
  exactly why and how it was built — read it before treating "price
  tier" as ground truth for a real decision. Because gdp_per_capita is
  a country-level number, many cities in the same country share the
  exact same value, which can occasionally put several cities exactly
  on a tercile boundary — `buildLabels()` handles that gracefully
  (falls back to two tiers rather than crashing) rather than assuming
  the data will always split cleanly into three.

## Changing what the recommender prioritises

Open `src/buildCityFeatures.py` and edit the `WEIGHTS` dictionary near
the top — it's a plain weighted average, nothing hidden.

## Changing the colours

Edit `.streamlit/config.toml` (controls Streamlit's own buttons and
sliders) and `themeStyles.py` (controls the Plotly charts, score badges,
and card styling) — keep the colours in both roughly matching.

> **Windows:** run each command on its own line and don't paste the `# comments` (cmd.exe treats them as arguments, e.g. `python -m pytest -q # ...` fails). Use `del data\cityBreaks.db` instead of `rm`.

## Tuning the scores

`src/buildCityFeatures.py` has two constants near the top: `CLIP_PERCENT` (default 5) and `LOG_SCALE` (default True). They stop one outlier city (a mega-hub airport, a country with huge visitor numbers) from squashing every other city's score towards 0. Set `CLIP_PERCENT = 0` and `LOG_SCALE = False` for the old plain min-max behaviour; raise `CLIP_PERCENT` for more generous scores. `WEIGHTS` controls the overall score. Re-run `buildCityFeatures.py`, `clusterCities.py` and `classifyPriceTier.py` after changing them.
