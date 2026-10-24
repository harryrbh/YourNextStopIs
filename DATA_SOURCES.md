# Data sources: exactly what to download, and how to read it

Every attribute the app shows comes from one of the extracts below. The
sample CSVs in `data/` (46 hand-made cities) work out of the box; this
document is for building the **real** dataset (250 cities).

Put manual downloads in **`data/raw/`** (git-ignored). `python src/download_raw_data.py`
does all of this for you and prints the manual steps for anything it can't fetch.

| # | Feeds | Extract to download | Save as | Interpreted with | Read by |
|---|---|---|---|---|---|
| 1 | City coordinates, population | GeoNames `cities15000.zip` | *(downloaded by the script itself)* | `geonames_readme.txt` | `fetch_cities.py` |
| 2 | Country facts | countries.dev API | — | — | `fetch_countries.py` |
| 3 | Popularity, GDP, urbanisation | World Bank API | — | — | `fetch_tourism.py` |
| 4 | Weather | NASA POWER API | — | — | `fetch_weather.py` |
| 5 | **Culture: attractions** | GeoNames **per-country** files `<ISO2>.zip` | `data/raw/geonames/FR.txt`, `IT.txt`, ... (one per country in `cities.csv`) | `featureCodes_en.txt`, `geonames_readme.txt` | `build_culture.py` |
| 6 | **Culture: heritage** | UNESCO World Heritage List | `data/raw/unesco_whc.xml` (or `.csv`/`.xlsx`) | this page | `build_culture.py` |
| 7 | **Ease of travel: airports** | OpenFlights `airports.dat` | `data/raw/airports.dat` | OpenFlights data page | `fetch_airports.py` |
| 8 | **Ease of travel: routes** | OpenFlights `routes.dat` | `data/raw/routes.dat` | OpenFlights data page | `fetch_airports.py` |

## 5. GeoNames per-country files (attractions)

* **Where:** https://download.geonames.org/export/dump/ — download `FR.zip`, `IT.zip`, ... for every
  country code in the `iso2` column of `data/cities.csv` (about 70 files, 1–40 MB each). Unzip each and
  keep only `<ISO2>.txt` (ignore the `readme.txt` inside the zip). **Do not** download `allCountries.zip`
  (1.5 GB) — you don't need it.
* **Also download** (small, to interpret the data): `featureCodes_en.txt` and `readme.txt`
  (save as `geonames_readme.txt`) from the same folder.
* **Format:** tab-separated, no header, 19 columns (listed in `readme.txt`): id, name, asciiname,
  alternatenames, latitude, longitude, **feature class**, **feature code**, country, ..., population,
  ..., timezone, modified date.
* **How it is read:** a row is a *sight* if its class/code is one of `SIGHT_FEATURE_CODES` in
  `src/build_culture.py` (museum `S.MUS`, castle `S.CSTL`, palace `S.PAL`, monument `S.MNMT`, historic
  site `S.HSTS`, ruin `S.RUIN`, church `S.CH`, temple `S.TMPL`, mosque `S.MSQE`, park `L.PRK`, ...).
  `featureCodes_en.txt` is the dictionary for those codes; `build_culture.py` warns if a code we use isn't in it.
* **Derived columns:** `attraction_count` = sights within 10 km of the city centre;
  `attraction_1..3` = the three with the most alternate names (a fame proxy: well-known places are
  written in many languages).
* **Caveat:** GeoNames maps some countries more densely than others, so counts are a *relative* measure.

## 6. UNESCO World Heritage List (heritage sites)

* **Where:** https://whc.unesco.org/en/list/ — use the page's download/export option for the **full
  list** (XML or Excel). Save as `data/raw/unesco_whc.xml`; if you get Excel/CSV, save as
  `unesco_whc.xlsx` / `unesco_whc.csv`.
* **What is needed from it:** one row per site with a name and latitude/longitude.
  `load_unesco()` reads coordinates from `<latitude>/<longitude>`, or from the `<geolocations>` element used by current exports (nested elements, attributes or plain "lat, lon" text), or from CSV/Excel columns by name (`site`/`name`, `latitude`/`lat`, `longitude`/`lon`) and
  raises an error listing the columns it saw if UNESCO changes its layout — then add the new names to
  that function.
* **Derived column:** `heritage_site_count` = UNESCO sites within 25 km of the city centre. Sites with
  no single coordinate (some serial, multi-country ones) are ignored.

## 7 & 8. OpenFlights airports and routes (ease of travel)

* **Where:** https://github.com/jpatokal/openflights/tree/master/data — files `airports.dat` and
  `routes.dat` (raw links: `https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat`).
* **Format:** comma-separated, **no header**, `\N` = missing. Airports: id, name, city, country, IATA,
  ICAO, latitude, longitude, altitude, tz offset, DST, tz name, type, source. Routes: airline, airline id,
  source IATA, source id, destination IATA, destination id, codeshare, stops, equipment.
* **How it is read (`fetch_airports.py`):** every airport with a 3-letter IATA code is attached to the
  **every** city in `cities.csv` within 100 km (so Orly/CDG -> Paris, Bergamo -> Milan, and Kansai -> both Osaka and Kyoto). `airports.csv` has one row per airport-city pair, with `distance_km` and `is_nearest` columns. A route is kept
  only if both ends were attached to a city. The output is `data/airports.csv` and `data/routes.csv`.
* **Caveat:** OpenFlights' route data stops around 2014, so treat connectivity as relative, not current.

## How incomplete cities are handled

`src/select_cities.py` (run by `load_data.py`) requires every kept city to have: country GDP,
urbanisation and tourist arrivals; 12 months of weather; at least one attraction, three attraction names and a heritage
count; and an airport with at least one route. Cities failing any test are dropped with the reason
printed, and the next city in `src/tourist_cities.py` takes their place, up to 250.
