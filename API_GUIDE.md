# API Guide: Swapping in Real Data, API by API

The project ships with sample data in `data/*.csv` so it runs
immediately. This guide walks through replacing each sample file with
real data from a live API — one API at a time, in the order you should
do them, with what each step actually does and why.

**Important — do these in order.** `fetch_weather.py` needs
`data/cities.csv` to already exist (it looks up each city's
coordinates), and `fetch_tourism.py` needs `data/countries.csv` to
already exist (it fills in a column on it). Skipping ahead will either
fail outright or quietly use stale data.

| Step | Script | Replaces | Needs run first |
|---|---|---|---|
| 1 | `src/fetch_countries.py` | `data/countries.csv` | — |
| 2 | `src/fetch_cities.py` | `data/cities.csv` | — |
| 3 | `src/fetch_weather.py` | `data/weather.csv` | Step 2 |
| 4 | `src/fetch_tourism.py` | `data/tourism.csv`, updates `data/countries.csv` | Step 1 |

None of these four APIs need a signup or an API key. (OpenFlights,
which supplies `data/airports.csv` and `data/routes.csv`, is already
real data — see the note at the end.)

Before starting, make a backup of the sample data so you can compare,
or switch back if something goes wrong:

```bash
cp -r data data_sample_backup
```

---

## Step 1: Countries — REST Countries

**What it is:** a free, keyless API that returns country-level facts
(name, region, population, coordinates) for every country in the world.

**Endpoint:** `https://restcountries.com/v3.1/all`

**Try it yourself first**, before running any code, just to see the
shape of the data — paste this into your browser:
```
https://restcountries.com/v3.1/all?fields=name,cca2,population
```
You'll get back a big JSON array, one object per country. Getting
comfortable reading a raw API response before writing code around it
is a habit worth building.

**Run it:**
```bash
python src/fetch_countries.py
```

**What the script does, step by step** (open `src/fetch_countries.py`
to follow along):
1. `requests.get(URL, params={"fields": FIELDS})` sends the HTTP
   request. The `fields` parameter matters: without it, REST Countries
   returns *everything* it knows about each country (flags, borders,
   currencies, languages...) — a much bigger response than we need.
2. `response.raise_for_status()` — if the request failed (wrong URL, no
   internet, API down), this raises an error immediately with a clear
   message, instead of the script silently continuing with no data.
3. `response.json()` turns the response body into a Python list of
   dictionaries.
4. `to_dataframe()` picks out just the fields our database needs, and
   renames/reshapes them to match `data/countries.csv`'s expected
   columns.
5. `df.to_csv(...)` writes the result, overwriting the sample file.

**A gap you'll hit immediately:** REST Countries doesn't provide GDP.
The script leaves `gdp_per_capita_usd` empty for now — Step 4 (World
Bank) fills it back in. This is a normal part of working with real
APIs: no single source has everything, so real projects often combine
two or three.

---

## Step 2: Cities — GeoNames

**What it is:** a free, keyless bulk download of every city in the
world with population ≥ 15,000 — about 25,000 rows.

**Why a download instead of an API call:** GeoNames also has a live
search API, but it's rate-limited (2,000 requests/hour on a free
account) and needs a username. For a one-off "get me every city,"
downloading the whole file once is both faster and simpler than
paginating through thousands of small API calls.

**Try it yourself first:** paste this into your browser —
```
https://download.geonames.org/export/dump/cities15000.zip
```
— and your browser will download a `.zip` file. Unzip it and open the
`.txt` file inside in a spreadsheet program. Notice it has **no header
row** — that's why `src/fetch_cities.py` defines the column names by
hand (`COLUMNS = [...]`), taken from GeoNames' own documentation at
`https://download.geonames.org/export/dump/readme.txt`.

**Run it:**
```bash
python src/fetch_cities.py
```

**What the script does:**
1. Downloads the `.zip` file into memory (`io.BytesIO(response.content)`)
   — it never gets written to your disk as a `.zip`, which keeps things
   tidy.
2. Opens the file *inside* the zip and reads it as tab-separated values
   (`sep="\t"`) using the column names above.
3. Sorts by population and keeps only the biggest `MAX_CITIES` (200 by
   default) — the full 25,000-city file works too, but is slower to
   experiment with while you're learning. Raise the number in the
   script once you're happy with everything else.
4. Renames `country_code` to `iso2` (GeoNames' name for the column
   happens to already use the same two-letter codes as REST Countries
   — a small stroke of luck that makes joining them later trivial).

**A gap you'll hit:** the sample `data/cities.csv` had heritage-site
and attraction counts (used for `culture_score`); GeoNames doesn't
provide those. `load_data.py` already treats missing culture data as
zero, so the pipeline still runs — but every city's culture score will
be identical (and low) until you add a real source for it. A natural
next project step: OpenStreetMap's Overpass API can count
`tourism=attraction|museum` points near a coordinate.

---

## Step 3: Weather — Open-Meteo

**What it is:** a free, keyless historical weather API. Unlike the
previous two, this one needs coordinates *per city*, so it makes one
request per row in `data/cities.csv` — run Step 2 first.

**Endpoint:** `https://archive-api.open-meteo.com/v1/archive`

**Try it yourself first:**
```
https://archive-api.open-meteo.com/v1/archive?latitude=48.85&longitude=2.35&start_date=2023-01-01&end_date=2023-01-31&daily=temperature_2m_mean,precipitation_sum&timezone=UTC
```
That's Paris's coordinates, one month of daily data. Notice the
response has a `"daily"` object containing parallel arrays — one list
of dates, one list of temperatures, one of rainfall, all the same
length. That "arrays that line up by position" shape is common in
weather/scientific APIs, and is exactly why the script builds a
DataFrame from it (`pd.DataFrame({...})`) rather than looping.

**Run it:**
```bash
python src/fetch_weather.py
```
This takes a few minutes for 200 cities — one request per city, with a
short `time.sleep(0.2)` pause between each so we don't hammer a free
API that other people also rely on.

**What the script does:**
1. For each city, requests ten years of daily temperature and rainfall
   (`START_YEAR` to `END_YEAR`) — one *year* wouldn't tell you much
   about a "typical" month, but ten years averaged together does.
2. Groups the ~3,650 daily rows by calendar month (`df["month"]`) and
   averages each group — turning "ten years of daily data" into "12
   typical monthly numbers," which is what `weather.csv` and the
   `weather` table expect.
3. If one city's request fails (a typo in a name, a temporary API
   hiccup), the script prints a warning and *keeps going* rather than
   crashing the whole run — you don't want to lose 199 good results
   because 1 request failed.

---

## Step 4: Tourism + GDP — World Bank

**What it is:** a free, keyless API covering thousands of economic
indicators for every country, going back decades. We use two:
international tourist arrivals, and GDP per capita.

**Endpoint pattern:**
`https://api.worldbank.org/v2/country/all/indicator/<CODE>?format=json`

**Try it yourself first:**
```
https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD?format=json&per_page=5
```
Two things worth noticing:
- The response is a list of **two** items: `[metadata, records]` — not
  just the records directly. This trips people up constantly; the
  script's `fetch_indicator()` function has a comment pointing at
  exactly where this matters (`response.json()[1]`).
- Some countries will have `"value": null` for some years — not every
  country reports every indicator every year. The script filters these
  out (`if r["value"] is not None`).

**Finding indicator codes:** World Bank has thousands of these. Browse
them at `https://data.worldbank.org/indicator` — search "tourism" or
"GDP per capita" and the code is in the URL of whichever indicator you
click. We use:
- `ST.INT.ARVL` — international tourist arrivals
- `NY.GDP.PCAP.CD` — GDP per capita, current US$

**Run it (after Step 1):**
```bash
python src/fetch_tourism.py
```

**What the script does:**
1. Calls `fetch_indicator()` twice — once per code above. `mrnev=1` in
   the request means "most recent non-empty value", so you get each
   country's latest reported figure rather than every year back to the
   1960s.
2. Writes the arrivals data straight to `data/tourism.csv`.
3. For GDP, instead of writing a new file, it **updates the existing**
   `data/countries.csv` — matching rows by `iso2` and filling in the
   `gdp_per_capita_usd` column that Step 1 left empty.
   `combine_first()` fills gaps without overwriting anything that's
   already there.

**Why match by ISO code, not country name:** World Bank calls a
country `"United States"`; some other sources say `"United States of
America"`, or use accented characters (`"Côte d'Ivoire"` vs `"Cote
d'Ivoire"`). Text matching breaks on these mismatches silently — no
error, just missing rows. Two-letter ISO codes (`US`, `CI`) don't have
this problem, which is why `load_data.py` prefers to merge tourism
data by `iso2` when it's available (see the comment in that file).
This is a genuinely common real-world data-integration issue, not
something specific to this project.

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
oddly-named places will slip in; some scores will look different once
culture data is mostly zero). That's normal, and a good prompt to go
add a real culture-data source next.

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
