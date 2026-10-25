# Pipeline Script Reference

Reference for the data acquisition scripts in `src/`. Each script reads or writes CSV files in `data/`; none writes to the database. The database is populated only by `loadDataToDatabase.py`. For the meaning of each dataset see [dataSources.md](dataSources.md).

## Contents

1. [Execution order](#1-execution-order)
2. [Script reference](#2-script-reference)
3. [HTTP client](#3-http-client)
4. [Output schemas](#4-output-schemas)
5. [Extending the pipeline](#5-extending-the-pipeline)

## 1. Execution order

```
fetchCities -> fetchCountries -> fetchTourism -> fetchWeather
downloadRawData -> fetchAirports -> buildCulture
database -> loadDataToDatabase -> buildCityFeatures -> clusterCities -> classifyPriceTier
```

`fetchCities.py` must run first because every later script reads `data/cities.csv`. `downloadRawData.py` must run before `fetchAirports.py` and `buildCulture.py` if the extracts are not already in `data/raw/`.

## 2. Script reference

| Script | Reads | Request | Writes | Behaviour |
|---|---|---|---|---|
| `fetchCities.py` | `touristCityList.py` | GET GeoNames `cities15000.zip` | `cities.csv` | Matches each curated `(name, country)` against name, ASCII name and alternate names within that country; takes the most populous match; reports unmatched names |
| `fetchCountries.py` | none | GET `countries.dev/countries` | `countries.csv` | Requests `fields=name,alpha2Code,region,population,latlng`; writes one row per country returned; GDP and urbanisation are left empty for `fetchTourism.py` |
| `fetchTourism.py` | `countries.csv` | GET World Bank `.../country/all/indicator/<code>` with `format=json`, `per_page=20000`, `mrnev=<n>` | `tourism.csv`, `countries.csv` | Fetches three indicators; calculates arrivals growth from the two most recent years; fills GDP and urbanisation in `countries.csv` |
| `fetchWeather.py` | `cities.csv` | GET NASA POWER climatology point with `parameters=T2M,PRECTOTCORR`, `community=RE`, latitude, longitude | `weather.csv` | One request per city; appends after each city; skips cities already complete; `--fresh` restarts |
| `downloadRawData.py` | `cities.csv` | GET GeoNames, OpenFlights and UNESCO files | `data/raw/` | Skips existing files; retries; lists any file that could not be downloaded |
| `fetchAirports.py` | `cities.csv`, `data/raw/airports.dat`, `routes.dat` | Downloads the OpenFlights files if not present locally | `airports.csv`, `routes.csv` | Links airports to all cities within 100 km; keeps routes between linked airports |
| `buildCulture.py` | `cities.csv`, `data/raw/geonames/`, UNESCO file | none | `culture.csv` | Counts UNESCO sites within 25 km and sights within 10 km; names top three sights |
| `diagnoseAirports.py` | `cities.csv`, `data/raw/`, `airports.csv` | none | console | For named cities, lists airports within 150 km, their route counts and whether each is linked |
| `loadDataToDatabase.py` | all CSV files | none | `cityBreaks.db` | Selects up to 250 complete cities, loads tables |

## 3. HTTP client

`src/httpClient.py` provides `getJson(url, params, ...)`, used by `fetchWeather.py`, which makes the largest number of requests. The other fetch scripts make a small number of requests with `requests.get` directly.

| Behaviour | Detail |
|---|---|
| Retried responses | 429, 500, 502, 503, 504, timeouts and connection errors |
| Not retried | Other 4xx responses; raised immediately |
| Delay before retry | The `Retry-After` header if present, otherwise exponential back-off from 5 s to a 300 s cap, plus up to 1 s of jitter |
| Attempts | 8 by default; `RequestFailed` is raised afterwards |
| Pacing | A `Throttle` enforces a minimum gap between requests, increases it by 50% after each rate-limit response, and reduces it by 5% after each success |

Each request is retried in place. An earlier design retried failed requests in fixed rounds, which allowed only about one request per round to succeed once the server began rejecting traffic.

## 4. Output schemas

| File | Columns |
|---|---|
| `cities.csv` | name, iso2, population, latitude, longitude (sample file also has country_name, timezone, geoname_id) |
| `countries.csv` | name, iso2, iso3, region, subregion, capital, latitude, longitude, population, area_km2, currency, gdp_per_capita_usd, urban_population_pct |
| `tourism.csv` | iso2, country_name, year, arrivals, tourism_growth_pct (sample file also has overnight_stays, tourism_receipts and no iso2) |
| `weather.csv` | city_name, month, temperature_c, precipitation_mm |
| `culture.csv` | city_name, heritage_site_count, attraction_count, attraction_1, attraction_2, attraction_3 |
| `airports.csv` | iata_code, icao_code, airport_name, city_name, latitude, longitude, distance_km, is_nearest |
| `routes.csv` | source_iata, destination_iata, airline, stops |

Column names in the CSV files and the database use snake_case. Python identifiers use camelCase.

## 5. Extending the pipeline

To add a data source:

1. Write `src/fetch<Name>.py` that reads `data/cities.csv`, calls `getJson`, and writes a CSV keyed by `city_name` or `iso2`.
2. Add the table and columns to `sql/schema.sql`.
3. Load the CSV in `loadDataToDatabase.py`.
4. Add a completeness check in `selectCompleteCities.py` if the attribute must be present for every city.
5. Use the new columns in `buildCityFeatures.py`.
6. Add parsing tests that do not require network access.
