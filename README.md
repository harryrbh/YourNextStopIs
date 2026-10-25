# City Break Finder

A Streamlit application for comparing city-break destinations. Each city is scored on weather, ease of travel, culture, affordability and popularity. The app supports filtering, side-by-side comparison, preference-based recommendations and a per-city detail view.

## Contents

1. [Overview](#1-overview)
2. [Quick start](#2-quick-start)
3. [Application pages](#3-application-pages)
4. [Scoring method](#4-scoring-method)
5. [Models](#5-models)
6. [Data](#6-data)
7. [Project structure](#7-project-structure)
8. [Testing](#8-testing)
9. [Limitations](#9-limitations)

Related documents: [setupGuide.md](setupGuide.md) (building the project and Docker), [dataSources.md](dataSources.md) (data extracts), [apiGuide.md](apiGuide.md) (pipeline script reference).

## 1. Overview

| Item | Detail |
|---|---|
| Interface | Streamlit, six pages |
| Storage | SQLite (`data/cityBreaks.db`), built from CSV files |
| Analytics | pandas, scikit-learn, networkx, geopy |
| Charts | Plotly |
| Packaging | Docker (optional) |

The repository includes a 46-city sample dataset so the application runs without any downloads. A full dataset of up to 250 tourist cities can be built with the scripts in `src/` (see [Section 6](#6-data)).

## 2. Quick start

Requires Python 3.10 or later. No database server is needed.

**Windows (Command Prompt)**

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src\database.py
python src\loadDataToDatabase.py
python src\buildCityFeatures.py
python src\clusterCities.py
python src\classifyPriceTier.py
streamlit run app.py
```

**macOS / Linux**

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/database.py
python src/loadDataToDatabase.py
python src/buildCityFeatures.py
python src/clusterCities.py
python src/classifyPriceTier.py
streamlit run app.py
```

The application opens at http://localhost:8501.

**Docker**

```
docker build -t city-breaks .
docker run -p 8501:8501 city-breaks
```

The image builds its database during `docker build`. See [setupGuide.md](setupGuide.md) for details.

**Rebuilding.** After changing a CSV file or the scoring code, delete `data/cityBreaks.db` and repeat the five `python` commands above. `buildCityFeatures.py` recalculates all scores on every run.

## 3. Application pages

| Page | Purpose |
|---|---|
| Home | Map of all cities, counts by travel style, top ten cities by overall score |
| Explore | Filter by travel style, price tier, country and minimum scores; sort by distance from a chosen city; card or table view |
| Recommend | Five importance sliders; returns the nearest matching cities with a match percentage |
| Compare | Radar chart, score table, pairwise distances and direct flights for two to five cities |
| Tourism | Visitor numbers and growth by country; regression-based demand estimate |
| City details | Weather by month, country indicators, best-known attractions, airports, flight map and three similar cities |

City photos are requested from the Wikipedia summary API when a card is displayed. If the request fails, the card is shown without a photo.

## 4. Scoring method

Each city receives five scores on a 0 to 100 scale, calculated in `src/buildCityFeatures.py`.

| Score | Raw measure |
|---|---|
| Weather | `100 - (abs(mean temperature - 22) * 4 + mean monthly rainfall / 20)` |
| Ease of travel | `airports * 2 + routes * 0.1 + network centrality * 100` |
| Culture | `UNESCO sites * 3 + attractions / 20` |
| Affordability | Country GDP per person, inverted (lower GDP gives a higher score) |
| Popularity | Country tourist arrivals |

Network centrality is the degree centrality of each city's airports in the route graph.

**Scaling.** Raw values are scaled to 0 to 100 as follows: counts and monetary values are log-transformed, the lowest and highest 5% of values are clipped to 0 and 100, and the result is min-max scaled. This prevents a single outlier, such as a major hub airport, from compressing all other cities towards zero. Weather is clipped but not log-transformed. The constants `defaultClipPercent` and `defaultUseLogScale` at the top of `buildCityFeatures.py` control this. Setting them to `0` and `False` gives plain min-max scaling.

**Overall score.** A weighted average of the five scores:

| Weather | Ease of travel | Culture | Affordability | Popularity |
|---|---|---|---|---|
| 0.30 | 0.25 | 0.20 | 0.15 | 0.10 |

The weights are defined in the `weights` dictionary in the same file.

## 5. Models

| Feature | Method | Module |
|---|---|---|
| Travel style | K-Means clustering (4 clusters) on standardised scores. Each cluster is named after its strongest trait. | `clusterCities.py` |
| Price tier | Classification into Budget, Mid-range and Luxury. The label is derived from country GDP per person split into thirds, and the model predicts it from other city attributes. Logistic regression, a decision tree and a random forest are compared by cross-validation, and the best is used. | `classifyPriceTier.py` |
| Recommendations | Nearest neighbours (cosine distance) between the user's slider values and each city's scores; also used for similar cities. | `recommendSimilarCities.py` |
| Demand estimate | Linear regression predicting country tourist arrivals from population, GDP per person, connectivity, heritage sites and weather. | `predictTourismDemand.py` |

**Validation.** Cross-validation for the price tier classifier is split by country, because GDP and arrivals are country-level values and ordinary folds would place cities from the same country in both training and test sets. The comparison table reports training accuracy, cross-validated accuracy and the majority-class baseline so that overfitting is visible. Tree depth is limited to reduce it.

## 6. Data

| Dataset | Source |
|---|---|
| City coordinates and population | GeoNames `cities15000` |
| Country facts | countries.dev |
| Tourist arrivals, GDP per person, urbanisation | World Bank indicators |
| Monthly temperature and rainfall | NASA POWER climatology |
| Attractions | GeoNames per-country files |
| World Heritage sites | UNESCO World Heritage List |
| Airports and routes | OpenFlights |

Building the full dataset:

```
python src/fetchCities.py
python src/fetchCountries.py
python src/fetchTourism.py
python src/fetchWeather.py
python src/downloadRawData.py
python src/fetchAirports.py
python src/buildCulture.py
```

Then run the database and model steps from Section 2.

`src/touristCityList.py` holds a curated pool of about 370 candidate cities, ordered by prominence. `loadDataToDatabase.py` keeps the first 250 that have complete data (country statistics, 12 months of weather, at least one attraction, and an airport with routes) and prints the reason for each city it drops. See [dataSources.md](dataSources.md) for the extracts and [apiGuide.md](apiGuide.md) for each script.

## 7. Project structure

```
app.py                      Navigation entry point
pages/                      One file per page
uiComponents.py             City card component
dataAccess.py               Cached database queries
displayLabels.py            Display names, rounding and flag helpers
themeStyles.py              Colours and card styling
distanceCalculator.py       Distance between coordinates (geopy)
cityImages.py               Wikipedia photo lookup
src/
  database.py               Engine and schema creation
  loadDataToDatabase.py     CSV import and city selection
  selectCompleteCities.py   Completeness checks
  buildCityFeatures.py      Score calculation
  clusterCities.py          Travel style clusters
  classifyPriceTier.py      Price tier classifier
  recommendSimilarCities.py Recommendations
  predictTourismDemand.py   Demand regression
  touristCityList.py        Candidate city pool
  httpClient.py             HTTP client with retries
  fetch*.py, build*.py      Data acquisition scripts
  downloadRawData.py        Raw extract downloader
  diagnoseAirports.py       Airport matching diagnostics
sql/schema.sql              Table definitions
data/                       CSV files and database
tests/                      Unit tests
Dockerfile
```

## 8. Testing

```
python -m pytest -q
```

The suite has 23 tests covering score scaling, city selection, airport matching, culture parsing, retry behaviour and recommendations. Four tests that query the database are skipped if it has not been built. The fetch scripts' network calls are not tested; their parsing functions are.

## 9. Limitations

- Popularity and affordability are country-level figures, so cities in the same country share them.
- Attraction and heritage counts depend on how completely GeoNames and UNESCO cover each country. They are suitable for relative comparison only.
- OpenFlights route data dates from around 2014.
- The price tier is predicted from a label derived from GDP, so it is a proxy and not a measured price level.
- The sample dataset is small, so model accuracy figures are indicative only.
- The curated city list is a judgement, not a measured ranking.
