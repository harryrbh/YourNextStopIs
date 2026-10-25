# Data Sources

This document lists every external dataset used to build the full 250-city dataset, how each is obtained, how it is interpreted, and which output file it feeds. The 46-city sample in `data/` is hand-prepared and is used when the fetch scripts have not been run.

## Contents

1. [Source summary](#1-source-summary)
2. [Raw extracts](#2-raw-extracts)
3. [Interpretation of each extract](#3-interpretation-of-each-extract)
4. [City selection](#4-city-selection)
5. [Terms of use](#5-terms-of-use)

## 1. Source summary

| Dataset | Provider | Access | Script | Output |
|---|---|---|---|---|
| City coordinates, population | GeoNames `cities15000` | Download (zip) | `fetchCities.py` | `data/cities.csv` |
| Country facts | countries.dev | API | `fetchCountries.py` | `data/countries.csv` |
| Arrivals, GDP per person, urbanisation | World Bank indicators | API | `fetchTourism.py` | `data/tourism.csv`, `data/countries.csv` |
| Monthly temperature and rainfall | NASA POWER climatology | API | `fetchWeather.py` | `data/weather.csv` |
| Attractions | GeoNames per-country files | Download (zip) | `buildCulture.py` | `data/culture.csv` |
| World Heritage sites | UNESCO World Heritage List | Download (XML) | `buildCulture.py` | `data/culture.csv` |
| Airports | OpenFlights `airports.dat` | Download | `fetchAirports.py` | `data/airports.csv` |
| Routes | OpenFlights `routes.dat` | Download | `fetchAirports.py` | `data/routes.csv` |
| City photographs | Wikipedia summary API | API, at display time | `cityImages.py` | Not stored |

## 2. Raw extracts

`python src/downloadRawData.py` downloads the files below into `data/raw/`. Files already present are skipped. For any file that cannot be downloaded, the script prints the URL and the path to save it at.

| File in `data/raw/` | Source URL | Notes |
|---|---|---|
| `geonames/<CC>.txt` | `https://download.geonames.org/export/dump/<CC>.zip` | One file per country code in `data/cities.csv`; unzip and keep `<CC>.txt` |
| `geonamesFeatureCodes.txt` | `.../export/dump/featureCodes_en.txt` | Dictionary of GeoNames feature codes |
| `geonamesReadme.txt` | `.../export/dump/readme.txt` | Column definitions for the GeoNames files |
| `airports.dat` | `https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat` | |
| `routes.dat` | `https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat` | |
| `unescoHeritageSites.xml` | `https://whc.unesco.org/en/list/` (export option) | Excel or CSV exports may be saved as `.xlsx` or `.csv` instead |

The per-country GeoNames files total roughly 70 downloads. The combined `allCountries.zip` (about 1.5 GB) is not needed.

## 3. Interpretation of each extract

### 3.1 GeoNames per-country files (attractions)

Tab-separated, no header, 19 columns defined in `geonamesReadme.txt`. Relevant columns: name, alternate names, latitude, longitude, feature class, feature code.

A row counts as a sight if its class and code appear in `sightFeatureCodes` in `src/buildCulture.py`: museum (`S.MUS`), castle (`S.CSTL`), palace (`S.PAL`), monument (`S.MNMT`), historic site (`S.HSTS`), ruin (`S.RUIN`), ancient site (`S.ANS`), church (`S.CH`), temple (`S.TMPL`), mosque (`S.MSQE`), park (`L.PRK`) and others in that list. `geonamesFeatureCodes.txt` defines each code; the script warns if a code in use is not listed there.

Derived columns:

| Column | Definition |
|---|---|
| `attraction_count` | Sights within 10 km of the city centre |
| `attraction_1` to `attraction_3` | The three sights with the most alternate names |

Alternate-name count is used as a proxy for how well known a place is, because prominent sights are recorded in many languages. It is not a visitor ranking. Coverage varies by country, so counts are suitable for relative comparison only.

### 3.2 UNESCO World Heritage List

The loader accepts XML, CSV or Excel. For XML it reads `<latitude>`/`<longitude>` elements or the `<geolocations>` element used by current exports, whether coordinates are nested elements, attributes or plain text. For CSV and Excel it matches columns named `site` or `name`, `latitude` or `lat`, and `longitude` or `lon`. If no coordinates are found, the first record is printed to show the layout.

`heritage_site_count` is the number of distinct sites with at least one location within 25 km of the city centre. A site with several locations is counted once.

### 3.3 OpenFlights

Comma-separated, no header, `\N` for missing values.

- `airports.dat`: id, name, city, country, IATA, ICAO, latitude, longitude, altitude, timezone offset, DST, timezone name, type, source.
- `routes.dat`: airline, airline id, source IATA, source id, destination IATA, destination id, codeshare, stops, equipment.

`fetchAirports.py` links each airport with a valid three-letter IATA code to every city within 100 km. An airport may therefore appear in several rows of `data/airports.csv`, with `distance_km` and `is_nearest` columns. A route is kept only if both airports were linked to a city. The route data ends around 2014.

### 3.4 NASA POWER climatology

One request per city returns 30-year monthly means for `T2M` (air temperature at 2 m, degrees Celsius) and `PRECTOTCORR` (corrected precipitation, millimetres per day). Rainfall is multiplied by the days in each month and stored as `precipitation_mm`, a monthly total. February uses 28.25 days.

### 3.5 World Bank indicators

| Indicator code | Meaning | Column |
|---|---|---|
| `ST.INT.ARVL` | International tourist arrivals | `tourism.csv: arrivals` |
| `NY.GDP.PCAP.CD` | GDP per person, current US dollars | `countries.csv: gdp_per_capita_usd` |
| `SP.URB.TOTL.IN.ZS` | Urban population, percent of total | `countries.csv: urban_population_pct` |

The most recent non-empty value for each country is used. Countries without a value, such as Taiwan, cannot be scored and their cities are dropped.

## 4. City selection

`src/selectCompleteCities.py`, called from `loadDataToDatabase.py`, keeps a candidate city only if all of the following hold:

- its country has GDP per person, urban population percentage and tourist arrivals;
- it has temperature and rainfall for all 12 months;
- it has at least one attraction, three attraction names and a heritage count;
- it has an airport with at least one route.

Candidates are taken in the order of `src/touristCityList.py`, and the first 250 that pass are loaded. Each rejected city is printed with its reasons.

## 5. Terms of use

Each provider sets its own terms, which should be checked before redistributing derived data. GeoNames data requires attribution, and the OpenFlights database is published under an open database licence. Wikipedia and Wikimedia ask API clients to identify themselves with a descriptive User-Agent; `cityImages.py` sets one, and the contact details in it should be replaced with real ones before deployment.
