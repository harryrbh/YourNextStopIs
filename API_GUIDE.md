# API Guide: Swapping in Real Data, API by API

The project ships with sample data in `data/*.csv` so it runs
immediately. This guide walks through replacing each sample file with
real data from a live API — one API at a time, in the order you should
do them, with exactly what each step does, why, what the response
looks like, and what's honestly still missing afterwards.

**Important — do these in order, and run all four before the rest of
the pipeline.** `fetch_weather.py` needs `data/cities.csv` to already
exist (it looks up each city's coordinates), and `fetch_tourism.py`
needs `data/countries.csv` to already exist (it fills in two columns
on it). Skipping ahead will either fail outright or quietly leave
columns empty. The short version: run all four fetch scripts below,
*then* run the whole `db.py` -> `build_features.py` -> `cluster.py`
pipeline once, not interleaved. (If you also use the optional
`src/classify.py` — not run by default; see README.md's note on it —
the same rule applies even more strictly: it builds its price-tier
labels directly from `gdp_per_capita`, so running it before Step 4 has
filled that column in will stop with a clear error telling you to run
`fetch_tourism.py` first.)

| Step | Script | Writes to | Needs run first |
|---|---|---|---|
| 1 | `src/fetch_countries.py` | `data/countries.csv` | — |
| 2 | `src/fetch_cities.py` | `data/cities.csv` | — |
| 3 | `src/fetch_weather.py` | `data/weather.csv` | Step 2 |
| 4 | `src/fetch_tourism.py` | `data/tourism.csv`, and fills in two columns of `data/countries.csv` | Step 1 |

None of these four APIs need a signup or an API key. (OpenFlights,
which supplies `data/airports.csv` and `data/routes.csv`, is already
real data — see the note near the end.)

Before starting, make a backup of the sample data so you can compare,
or switch back if something goes wrong:

```bash
cp -r data data_sample_backup
```

---

## Step 1: Countries — countries.dev

**A note on which API this is, and why it changed:** this step
originally used REST Countries (restcountries.com) v3.1, which was
genuinely free and keyless. As of 2026, REST Countries v1-v4 are
**deprecated** — the old endpoint now returns an error object instead
of data — and the replacement, v5, requires creating a free account
and an API key. Since this project is specifically built so nobody
needs to sign up for anything, `fetch_countries.py` now uses
[countries.dev](https://countries.dev) instead: a free, keyless API
returning equivalent country data. If you'd rather use the more
established REST Countries v5 and don't mind a free signup, see the
comment at the top of `fetch_countries.py` for exactly what to change.

**What it is:** a free, keyless API that returns country-level facts
(name, region, population, coordinates) for every country in the
world.

**Endpoint:** `https://countries.dev/countries`

**Try it yourself first**, before running any code, just to see the
shape of the data — paste this into your browser:
```
https://countries.dev/countries?fields=name,alpha2Code,population
```

You'll get back a big JSON array, one object per country, that looks
like:
```json
[
  {
    "name": "France",
    "alpha2Code": "FR",
    "population": 67391582
  }
]
```
Getting comfortable reading a raw API response before writing code
around it is a habit worth building — notice `name` here is a plain
string, not a nested object (some country APIs, including REST
Countries, nest it as `{"common": "France", "official": "..."}`
instead) — which is why `to_dataframe()` in the script reads it
directly with `country.get("name")` rather than reaching into a
sub-dictionary.

**Run it:**
```bash
python src/fetch_countries.py
```

**What the script does, step by step** (open `src/fetch_countries.py`
to follow along):
1. `requests.get(URL, params={"fields": FIELDS})` sends the HTTP
   request. The `fields` parameter matters a lot here: without it,
   the API returns *everything* it knows about each country — flags,
   currencies, languages, calling codes, and more — several times
   bigger than we need, and slower to download and parse for no
   benefit.
2. `response.raise_for_status()` — if the request failed (wrong URL,
   no internet, the API is down, you've been rate-limited), this
   raises a clear error immediately, rather than the script silently
   continuing with no data and failing confusingly three steps later.
3. `response.json()` turns the response body into a Python list of
   dictionaries — `requests` handles the JSON parsing for you.
4. **The script then checks `isinstance(data, list)`** before doing
   anything else with it. This isn't defensive paranoia for its own
   sake — it's there because this exact failure already happened once
   while building this project: an API changed/deprecated and started
   returning an error *object* (e.g.
   `{"success": False, "errors": [...]}`) instead of the expected
   *list*, and without this check, the next line silently iterated
   over that object's keys as if they were countries and crashed
   three function calls later with a confusing `AttributeError`. If
   this ever happens again (the API changes again, is temporarily
   down, etc.), you'll now see the API's own error message directly,
   plus the exact URL to open in your browser to see the live
   response yourself.
5. `to_dataframe()` picks out just the fields our database needs,
   pulls `latlng` apart into separate `latitude`/`longitude` columns,
   and renames things to match what `data/countries.csv` needs.
6. `df.to_csv(...)` writes the result, overwriting the sample file.

**Error handling to be aware of:** if the API is temporarily
unreachable, `requests.get` will eventually raise a
`requests.exceptions.ConnectionError` (not caught here on purpose —
for a one-off script, letting it crash with Python's own clear
traceback is more useful than swallowing the error and continuing
with bad data).

**Two gaps you'll hit immediately:** this API doesn't provide GDP per
capita or urban population percentage (neither did REST Countries).
The script leaves both `gdp_per_capita_usd` and `urban_population_pct`
empty for now — Step 4 (World Bank) fills both back in. This is a
completely normal part
of working with real APIs: no single free source has everything, so
real projects nearly always combine two or three.

---

## Step 2: Cities — GeoNames

**What it is:** a free, keyless bulk download of every city in the
world with population >= 15,000 — about 25,000 rows, maintained by
the GeoNames geographical database project.

**Why a download instead of an API call:** GeoNames also has a live
search API, but it's rate-limited (2,000 requests/hour on a free
account) and needs a username. For a one-off "get me every city,"
downloading the whole file once is both faster and dramatically
simpler than paginating through thousands of small API calls, and it
means the script has no external account dependency at all.

**Try it yourself first:** paste this into your browser —
```
https://download.geonames.org/export/dump/cities15000.zip
```
— and your browser will download a `.zip` file. Unzip it and open the
`.txt` file inside in a spreadsheet program (Excel, Google Sheets,
even a plain text editor for the first few lines). Notice it has **no
header row** and is **tab-separated, not comma-separated** — that's
why `src/fetch_cities.py` defines the column names by hand
(`COLUMNS = [...]`) and reads it with `sep="\t"`, taken from GeoNames'
own documentation at
`https://download.geonames.org/export/dump/readme.txt`. A typical row
looks like:
```
2988507	Paris	Paris	Paris,par-i,...	48.85341	2.3488	P	PPLC	FR		...	2138551	...
```
Eighteen tab-separated fields, in the exact order `COLUMNS` lists them.

**Run it:**
```bash
python src/fetch_cities.py
```

**What the script does:**
1. Downloads the `.zip` file into memory
   (`io.BytesIO(response.content)`) — it never gets written to your
   disk as a `.zip` file, which keeps the `data/` folder tidy and
   means there's nothing extra to clean up.
2. Opens the file *inside* the zip archive without extracting it
   first (`zipfile.ZipFile(...).open(...)`), and reads it as
   tab-separated values using the column names above.
3. Sorts by population and keeps only the biggest `MAX_CITIES` (200
   by default) — the full 25,000-city file works too, but is slower
   to experiment with while you're learning, and most of those rows
   are small towns you'd filter out anyway for a "city break"
   recommender. Raise the number in the script once you're happy with
   everything else.
4. Renames `country_code` to `iso2` (GeoNames' name for the column
   happens to already use the same standard two-letter ISO codes as
   countries.dev's `alpha2Code` — a small stroke of luck that makes
   joining the two data sources together later completely trivial,
   rather than needing a lookup table to translate between different
   country-coding systems).

**A gap you'll hit:** the sample `data/culture.csv` — heritage-site
counts, attraction counts, and the three named top attractions — is a
small, hand-picked file matching only the original 46 sample cities
by name. Once you swap in 200 real GeoNames cities, `load_data.py`'s
merge in `clean_cities()` will only find a match for the ~46 cities
that happen to overlap; every other city gets `heritage_sites = 0`,
`attractions = 0`, and empty attraction names (the merge is
`how="left"`, and missing values are filled with 0/""). This isn't a
bug — `load_data.py` handles it gracefully — but it does mean
`culture_score` (and the "Culture & heritage" section of the City
Details page) will be uninformative for most cities until you add a
real source. See "What's still missing" at the end of this guide for
how you'd genuinely fix that.

---

## Step 3: Weather — Open-Meteo

**What it is:** a free, keyless historical weather API covering the
whole globe from satellite/reanalysis data. Unlike the previous two,
this one needs coordinates *per city*, so it makes one request per
row in `data/cities.csv` — run Step 2 first.

**Endpoint:** `https://archive-api.open-meteo.com/v1/archive`

**Try it yourself first:**
```
https://archive-api.open-meteo.com/v1/archive?latitude=48.85&longitude=2.35&start_date=2023-01-01&end_date=2023-01-31&daily=temperature_2m_mean,precipitation_sum&timezone=UTC
```
That's Paris's coordinates, one month of daily data. The response
looks like:
```json
{
  "daily": {
    "time": ["2023-01-01", "2023-01-02"],
    "temperature_2m_mean": [5.2, 4.8],
    "precipitation_sum": [0.0, 2.3]
  }
}
```
Notice the `"daily"` object holds **parallel arrays** — one list of
dates, one of temperatures, one of rainfall, all the same length and
in the same order — rather than a list of `{date, temp, rain}`
objects. That "arrays that line up by position" shape is common in
weather and scientific APIs, and is exactly why the script builds a
DataFrame directly from those three arrays
(`pd.DataFrame({"date": ..., "temperature_c": ..., ...})`) rather than
looping through records one at a time.

**Run it:**
```bash
python src/fetch_weather.py
```
This takes a few minutes for 200 cities — one HTTP request per city,
with a short `time.sleep(0.2)` pause between each so the script
doesn't hammer a free API that other people also rely on. If you're
impatient while learning, temporarily lower `MAX_CITIES` in
`fetch_cities.py` to something like 20 first.

**What the script does:**
1. For each city, requests ten years of daily temperature and
   rainfall (`START_YEAR` to `END_YEAR` — 2015 to 2024 by default).
   One single year wouldn't tell you much about a "typical" month
   (a freak heatwave or a record-dry January would skew the whole
   result); ten years averaged together smooths that out.
2. Groups the resulting ~3,650 daily rows by calendar month
   (`df["month"] = df["date"].dt.month`, then `.groupby("month")`)
   and averages each group — turning "ten years of daily data" into
   "12 typical monthly numbers," which is exactly the shape
   `weather.csv` and the `weather` database table expect (one row per
   city per month, 1-12).
3. If one city's request fails (a network hiccup, a coordinate that
   somehow errors), the script catches the exception, prints a
   warning naming that city, and **keeps going** rather than crashing
   the whole run — you don't want to lose 199 good results because 1
   request failed partway through a multi-minute run.

---

## Step 4: Tourism, GDP & Urbanisation — World Bank

**What it is:** a free, keyless API covering thousands of economic
and social indicators for every country, going back decades,
maintained by the World Bank's own Open Data project. We use three:
international tourist arrivals, GDP per capita, and urban population
percentage.

**Endpoint pattern:**
`https://api.worldbank.org/v2/country/all/indicator/<CODE>?format=json`

**Try it yourself first:**
```
https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD?format=json&per_page=5
```
The response looks like:
```json
[
  {"page": 1, "pages": 216, "per_page": "5", "total": 1080},
  [
    {
      "indicator": {"id": "NY.GDP.PCAP.CD", "value": "GDP per capita (current US$)"},
      "country": {"id": "FR", "value": "France"},
      "date": "2023",
      "value": 44408.68
    }
  ]
]
```
Three things worth noticing, all of which the code handles explicitly:
- The response is a list of **two** items — `[metadata, records]` —
  not just the records directly. This trips people up constantly, and
  is exactly why `fetch_indicator()` has a comment pointing at
  `response.json()[1]`, not `[0]`.
- Some countries have `"value": null` for some years — not every
  country reports every indicator every year (small or data-poor
  countries especially). The script filters these out with
  `if r["value"] is not None` before they even reach the DataFrame.
- `country.id` here is already a two-letter ISO code (`"FR"`), which
  is what makes matching this back to `countries.csv` by `iso2`
  reliable — see "Why match by ISO code, not country name" below.

**Finding more indicator codes:** World Bank publishes thousands of
these. Browse them at `https://data.worldbank.org/indicator` — search
for what you want (e.g. "tourism", "internet users", "life
expectancy") and the code is in the URL of whichever indicator you
click (e.g. `.../indicator/NY.GDP.PCAP.CD` gives code `NY.GDP.PCAP.CD`).
We use:
- `ST.INT.ARVL` — international tourist arrivals (count of people)
- `NY.GDP.PCAP.CD` — GDP per capita, current US$
- `SP.URB.TOTL.IN.ZS` — urban population, % of total population

**Run it (after Step 1):**
```bash
python src/fetch_tourism.py
```

**What the script does:**
1. Calls `fetch_indicator()` three times — once per code above.
   `mrnev=1` in the request means "the most recent non-empty value",
   so each country appears once, with whichever year it most recently
   reported — not the same year for every country (some countries
   report 2023 figures, others only have 2021 data available; the API
   handles that for you).
2. Writes the tourist-arrivals data straight to `data/tourism.csv`.
3. For GDP and urbanisation, instead of writing new files, it
   **updates the existing** `data/countries.csv` — matching rows by
   `iso2` and filling in the `gdp_per_capita_usd` and
   `urban_population_pct` columns that Step 1 left empty.
   `combine_first()` fills gaps without overwriting anything that's
   already there, so running this step twice is harmless.

**Why match by ISO code, not country name:** World Bank calls a
country `"United States"`; some other sources say `"United States of
America"`, or use accented characters (`"Cote d'Ivoire"` vs
`"Côte d'Ivoire"`). Text matching breaks on these mismatches silently
— no error is raised, the row just quietly fails to match and ends up
with missing data. Two-letter ISO codes (`US`, `CI`) don't have this
problem, which is why `load_data.py` prefers to merge tourism data by
`iso2` when it's available (see the comment in that file), and why
this matters more with real, messier data than with the tidy sample
set. This is a genuinely common real-world data-integration issue,
not something specific to this project.

**A known limitation of this step:** `mrnev=1` only fetches the
single most recent year per country, so the resulting `tourism.csv`
has no `tourism_growth_pct` column, and `build_features.py`'s
`add_tourism_history()` will fall back to `tourism_growth_pct = 0`
and `previous_arrivals = tourist_arrivals` for every city (see that
function's docstring). To get a real, independently-measured
"previous year" figure — rather than one calculated backwards from a
growth rate, which is the sample data's known limitation too (see
`src/regression.py`'s docstring) — change `mrnev=1` to `mrnev=2` and
pivot the result so each country has two years side by side. A sketch
of exactly this is included at the bottom of `fetch_tourism.py` as
`fetch_two_years_sketch()` (not called by default) — read it alongside
`regression.py`'s docstring before using it, since it's the fix for
the very leakage problem that docstring describes.

---

## After running all four

Reload everything into the database:

```bash
python src/db.py             # wipes and recreates the tables
python src/load_data.py      # reads the new CSVs
python src/build_features.py
python src/cluster.py
streamlit run app.py
```

Open the app and sanity-check the results — with 200 real cities
instead of 46 curated ones, expect some surprises (a few tiny or
oddly-named places will slip in; culture scores will look flat since
most cities now lack heritage/attraction data). That's normal, and a
good prompt to go add a real culture-data source next (see below).

## About OpenFlights (already real)

`data/airports.csv` and `data/routes.csv` already contain **real**
airport and flight-route data from OpenFlights — no fetch script
needed for the version shipped with this project. If you want to
refresh it or point it at your new (larger) city list, the two files
to download are:
```
https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat
https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat
```
Both are plain CSVs with no header row (columns documented at
`https://openflights.org/data.html`). Matching every airport to its
nearest city by coordinates (rather than by name) is the fiddly part —
worth attempting once you're comfortable with everything above, but
deliberately left out of this project to keep `load_data.py` simple.
`build_features.py`'s `nearest_airport()` function already does the
geopy distance calculation you'd need for this, just applied to
whichever cities/airports end up loaded.

---

## What's still missing, honestly (and how you'd add it)

This project is upfront that some fields shown in the app — museums,
parks, restaurants, railway stations, and other fine-grained points of
interest — are **not** in the sample data, and none of the four APIs
above provide them either. Faking plausible-looking names for hundreds
of cities would be worse than leaving the gap visible, so the City
Details page says so directly instead. If you want to add this
yourself:

- **OpenStreetMap** has exactly this kind of data (tagged points like
  `tourism=museum`, `leisure=park`, `amenity=restaurant`,
  `railway=station`), but querying it live per-city via the Overpass
  API doesn't scale to hundreds of cities and is easy to accidentally
  overload — a shared public service, not built for bulk automated
  use. The standard approach is a **bulk extract**: download a
  regional `.osm.pbf` file (e.g. from Geofabrik,
  `https://download.geofabrik.de/`) and filter it locally with a tool
  like `osmium` or the Python library `pyrosm`, rather than making
  thousands of live API calls.
- **UNESCO World Heritage** has an official list of heritage sites
  with coordinates, usable for a much more precise `heritage_sites`
  count than our hand-picked numbers — check current licensing/reuse
  terms at `https://whc.unesco.org/en/syndication` before
  redistributing anything derived from it.
- **Real multi-year tourism data**, for genuine (non-circular)
  `previous_arrivals` and `tourism_growth_pct` predictors — see the
  `fetch_two_years_sketch()` note in Step 4 above.

None of these are wired into `load_data.py` in this project — adding
one is a natural next step once you're comfortable with the
read-clean-insert pattern every `fetch_*.py` script already follows.
