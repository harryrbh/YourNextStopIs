# Setup Guide

This guide describes how to build the project from an empty directory, one commit at a time, and how it is packaged with Docker. It is a recommended build order; the repository's actual history contains additional fix commits.

## Contents

1. [Prerequisites](#1-prerequisites)
2. [File structure](#2-file-structure)
3. [Build sequence](#3-build-sequence)
4. [Rebuilding the full dataset](#4-rebuilding-the-full-dataset)
5. [Docker](#5-docker)
6. [Troubleshooting](#6-troubleshooting)

## 1. Prerequisites

- Python 3.10 or later
- git
- Docker (optional)

Initialise the repository and environment:

```
mkdir city-break-simple
cd city-break-simple
git init
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
```

`.gitignore` should exclude `__pycache__/`, `*.pyc`, `.venv/`, `.pytest_cache/`, `data/cityBreaks.db` and `data/raw/`. The database is generated from the CSV files, so committing it would allow the two to diverge.

`requirements.txt` lists: pandas, SQLAlchemy, scikit-learn, networkx, geopy, plotly, streamlit, pytest, requests, openpyxl.

## 2. File structure

```
city-break-simple/
  app.py                       Navigation entry point
  pages/                       homePage, exploreCities, recommendCities,
                               compareCities, tourismTrends, cityDetails
  uiComponents.py  dataAccess.py  displayLabels.py
  themeStyles.py  distanceCalculator.py  cityImages.py
  src/
    database.py                          loadDataToDatabase.py
    selectCompleteCities.py              buildCityFeatures.py
    clusterCities.py                     classifyPriceTier.py
    predictTourismDemand.py              recommendSimilarCities.py
    touristCityList.py                   httpClient.py
    fetchCities.py  fetchCountries.py  fetchTourism.py  fetchWeather.py
    downloadRawData.py  fetchAirports.py  buildCulture.py  diagnoseAirports.py
  sql/schema.sql
  data/                        CSV files; data/raw/ holds downloaded extracts
  tests/
  .streamlit/config.toml
  Dockerfile  .dockerignore  .gitignore  pytest.ini  requirements.txt
  README.md  setupGuide.md  dataSources.md  apiGuide.md
```

## 3. Build sequence

| Step | Create | Check | Commit message |
|---|---|---|---|
| 1 | `.gitignore`, `requirements.txt` | `pip install -r requirements.txt` succeeds | Project skeleton |
| 2 | `sql/schema.sql`, `src/database.py`, sample CSV files in `data/` | `python src/database.py` reports tables created | SQLite schema and sample data |
| 3 | `src/loadDataToDatabase.py` | Prints counts of rows loaded | CSV loader |
| 4 | `src/buildCityFeatures.py` | No null values in any score column | Feature engineering |
| 5 | `src/clusterCities.py`, `classifyPriceTier.py`, `predictTourismDemand.py`, `recommendSimilarCities.py`, tests, `pytest.ini` | `python -m pytest -q` passes | Analytics modules and tests |
| 6 | `.streamlit/config.toml`, `themeStyles.py`, `dataAccess.py`, `uiComponents.py`, `displayLabels.py`, `distanceCalculator.py`, `cityImages.py`, `app.py`, `pages/` | `streamlit run app.py`; open every page | Streamlit application |
| 7 | `src/touristCityList.py`, `src/fetchCities.py` | Reports how many pool cities matched GeoNames | Candidate city pool |
| 8 | `src/httpClient.py`, `fetchCountries.py`, `fetchTourism.py`, `fetchWeather.py` (uses `httpClient.py`) | `fetchWeather.py` completes or can be re-run to resume | Data fetchers and HTTP client |
| 9 | `src/downloadRawData.py`, `src/fetchAirports.py` | Reports airports matched to cities | Airport and route matching |
| 10 | `src/buildCulture.py` | Reports cities with at least one sight | Culture data |
| 11 | `src/selectCompleteCities.py`; call it from `loadDataToDatabase.py` | Dropped cities are listed with reasons | City selection |
| 12 | `Dockerfile`, `.dockerignore`, documentation | `docker build -t city-breaks .` succeeds | Documentation and Docker |

Each step is committed with `git add .` followed by `git commit -m "<message>"`.

### Implementation notes

- **CSV reading.** Read CSV files with `keep_default_na=False, na_values=[""]`. Otherwise pandas interprets Namibia's country code `NA` as a missing value.
- **Rainfall units.** Precipitation must be stored as monthly totals in millimetres, because the weather score divides by 20 on that assumption.
- **Rate limits.** Open-Meteo's archive API weights each request by locations and days requested, so a ten-year daily request for 30 cities exceeds the free quota in one call. The project uses NASA POWER monthly climatology instead (one request per city) and retries individual requests with back-off in `httpClient.py`.
- **Airport matching.** An airport is linked to every city within 100 km. Linking each airport only to its nearest city left smaller neighbours of large cities with no airport.

## 4. Rebuilding the full dataset

Run from the project root, one command per line.

```
python src/fetchCities.py
python src/fetchCountries.py
python src/fetchTourism.py
python src/fetchWeather.py
python src/downloadRawData.py
python src/fetchAirports.py
python src/buildCulture.py
python src/database.py
python src/loadDataToDatabase.py
python src/buildCityFeatures.py
python src/clusterCities.py
python src/classifyPriceTier.py
python -m pytest -q
streamlit run app.py
```

Delete `data/cityBreaks.db` before `database.py` when rebuilding. `fetchWeather.py` saves after each city and resumes if interrupted; `--fresh` restarts it.

If `loadDataToDatabase.py` reports fewer than 250 complete cities, review the list of dropped cities. Common causes are a missing GeoNames country file, an unparsed UNESCO file, or a country with no World Bank figures. Add names to `src/touristCityList.py` to widen the pool.

## 5. Docker

The `Dockerfile` contains the following instructions:

| Instruction | Purpose |
|---|---|
| `FROM python:3.12-slim` | Base image with Python installed |
| `WORKDIR /app` | Working directory inside the container |
| `COPY requirements.txt .` and `RUN pip install ...` | Installs dependencies. This layer is cached and only rebuilt when `requirements.txt` changes. |
| `COPY . .` | Copies the project; files listed in `.dockerignore` are excluded |
| `RUN python src/database.py && ...` | Builds the database and models from the CSV files at image build time |
| `EXPOSE 8501` | Documents the port Streamlit uses |
| `CMD ["streamlit", "run", ...]` | Starts the application, listening on all interfaces |

Commands:

```
docker build -t city-breaks .
docker run -p 8501:8501 city-breaks
```

To keep data outside the image, mount the data directory:

```
docker run -p 8501:8501 -v "%cd%/data:/app/data" city-breaks
```

(On macOS and Linux use `$(pwd)/data` in place of `%cd%/data`.) The database is built during `docker build` from the CSV files in `data/`, so run the data fetch scripts before building if the full dataset is wanted in the image.

## 6. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `'rm' is not recognized` on Windows | Use `del data\cityBreaks.db` |
| `pytest` reports `file or directory not found: #` | A `#` comment was pasted after the command. Run `python -m pytest -q` on its own. |
| `Couldn't find site/latitude/longitude` or `Found no coordinates` in `buildCulture.py` | The UNESCO file layout differs from the parser. The error prints the first record; adapt `loadUnesco` or save the list as CSV with `site`, `latitude`, `longitude` columns. |
| A city is dropped for "no airport with flight routes nearby" | Run `python src/diagnoseAirports.py CityName` to list nearby airports and whether they have routes. |
| Page shows "No data found" | The database has not been built. Run the five commands in the README quick start. |
