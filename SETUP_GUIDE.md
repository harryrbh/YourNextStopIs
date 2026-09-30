# Setup Guide: build this project from scratch

This guide takes you from an empty folder to the finished app, one git
commit at a time, then explains how Docker packages it. Each step says
what to create, why it exists, how to check it worked, and the commit
message to use. Stuck? Compare with the finished repo.

Prerequisites: Python 3.12, git, and (optional, for the last part) Docker.

---

## Final file structure

```
city-break-simple/
├── app.py                      # Streamlit home page
├── pages/                      # one file per page: 1_Explore, 2_Recommend, 3_Compare, 4_Tourism, 5_City_Details
├── components.py labels.py theme.py images.py distance.py data_access.py   # UI helpers
├── src/
│   ├── db.py                   # creates the SQLite database from sql/schema.sql
│   ├── load_data.py            # CSVs -> database (calls select_cities.py first)
│   ├── select_cities.py        # keeps only cities with COMPLETE data, up to 250
│   ├── build_features.py       # 0-100 scores per city
│   ├── cluster.py classify.py regression.py recommend.py   # analytics
│   ├── tourist_cities.py       # curated pool of ~370 candidate cities
│   ├── http_util.py            # retrying, rate-limit-aware HTTP GET
│   ├── fetch_cities.py fetch_countries.py fetch_tourism.py fetch_weather.py   # online data
│   ├── download_raw_data.py    # downloads GeoNames / OpenFlights / UNESCO extracts to data/raw/
│   ├── fetch_airports.py       # airports + routes from OpenFlights (by distance)
│   └── build_culture.py        # heritage + attractions from UNESCO + GeoNames
├── sql/schema.sql
├── data/                       # CSVs (sample shipped); data/raw/ = downloaded extracts (git-ignored)
├── tests/
├── .streamlit/config.toml
├── requirements.txt  pytest.ini  Dockerfile  .dockerignore  .gitignore
└── README.md  API_GUIDE.md  DATA_SOURCES.md  SETUP_GUIDE.md
```

---

## Part A — Build it commit by commit

### 0. Start the repository
```bash
mkdir city-break-simple && cd city-break-simple
git init
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
```
Create `.gitignore` (`__pycache__/`, `*.pyc`, `.venv/`, `.pytest_cache/`, `.DS_Store`, `data/city_breaks.db`,
`data/raw/`) and `requirements.txt` (`pandas SQLAlchemy scikit-learn networkx geopy plotly streamlit pytest requests openpyxl`), then `pip install -r requirements.txt`.
```bash
git add . && git commit -m "Project skeleton: gitignore and requirements"
```
*Why ignore the `.db` file?* It is generated from the CSVs, so committing it only lets the two drift apart.

### 1. Database schema and sample data
Create `sql/schema.sql` (tables: `countries, cities, weather, tourism, airports, routes, city_features`), `src/db.py`
(builds `data/city_breaks.db`), and the sample CSVs in `data/`: `countries, cities, weather, tourism, culture, airports, routes`.
Column layouts: see the headers of the shipped sample files.
Check: `python src/db.py` prints "Database tables created".
```bash
git add . && git commit -m "SQLite schema, db helper and sample CSV data"
```

### 2. Loader
`src/load_data.py` reads the CSVs, links rows by id (city -> country, weather -> city, airports -> city,
routes -> airports) and writes to SQLite. Read CSVs with `keep_default_na=False, na_values=[""]`, otherwise pandas turns
Namibia's country code `NA` into "missing".
Check: `python src/load_data.py` prints the counts loaded.
```bash
git add . && git commit -m "CSV loader"
```

### 3. Feature engineering
`src/build_features.py` turns raw tables into 0-100 scores: weather comfort (temperature fit minus a rain penalty),
accessibility (airports, routes, network centrality with networkx), culture (`heritage*3 + attractions/20`),
affordability (from GDP per person), popularity (tourist arrivals). Precipitation must be **monthly totals in mm** — the
rain penalty divides by 20 assuming that.
Check: `python src/build_features.py`; there must be no nulls in any score.
```bash
git add . && git commit -m "Feature engineering: 0-100 scores per city"
```

### 4. Analytics
`src/cluster.py` (K-Means into travel-style categories; duplicate names get numbered), `src/classify.py` (price tier,
model comparison), `src/regression.py`, `src/recommend.py` (nearest-neighbour "similar cities"). Add `tests/` for
features and recommendations, plus `pytest.ini`.
Check: `python -m pytest -q`.
```bash
git add . && git commit -m "Clustering, classification, regression and recommender with tests"
```

### 5. The Streamlit app
`.streamlit/config.toml` and `theme.py` (colours), `data_access.py` (queries), `components.py`/`labels.py`/`images.py`/`distance.py`
(helpers), `app.py` and the five files in `pages/`.
Check: `streamlit run app.py`, open http://localhost:8501, click through every page.
```bash
git add . && git commit -m "Streamlit app: home, explore, recommend, compare, tourism, city details"
```

### 6. Real data: the candidate city pool
`src/tourist_cities.py` (the curated list of ~370 `(name, iso2)` pairs, most famous first) and `src/fetch_cities.py`,
which matches each entry against GeoNames `cities15000` by name/asciiname/alternate names within the right country. There is deliberately no
population "filler": filler towns have no sights, which is what produced empty culture data.
Check: `python src/fetch_cities.py` reports how many of the pool were matched.
```bash
git add . && git commit -m "Curated tourist-city pool; match against GeoNames"
```

### 7. Real data: countries, tourism, weather
`src/http_util.py` (retry each request **in place**, obey `Retry-After`, back off exponentially, slow the whole run
after a 429) is used by `src/fetch_countries.py`, `src/fetch_tourism.py` and `src/fetch_weather.py`.
Weather comes from NASA POWER monthly normals — one request per city, saved as it goes, resumable. (Open-Meteo's
archive API weighs a request by locations x days, so ten years for 30 cities blows the free quota in one call —
retries can't fix that.)
Check: `python src/fetch_weather.py` — re-run it if it stops; it continues where it left off.
```bash
git add . && git commit -m "Rate-limit-aware HTTP helper; countries, tourism and NASA POWER weather fetchers"
```

### 8. Real data: airports and flights
Follow `DATA_SOURCES.md` #7-8. `src/download_raw_data.py` saves OpenFlights `airports.dat` and `routes.dat` into `data/raw/`
(or download them by hand). `src/fetch_airports.py` attaches each airport to its **nearest** city within 100 km and keeps routes between
matched airports, writing `data/airports.csv` and `data/routes.csv`.
Check: it prints "Matched N airports to M of K cities".
```bash
git add . && git commit -m "Airports and routes from OpenFlights, matched to cities by distance"
```

### 9. Real data: culture
Follow `DATA_SOURCES.md` #5-6: GeoNames per-country files (`data/raw/geonames/<ISO2>.txt`), `featureCodes_en.txt`, and the UNESCO
list (`data/raw/unesco_whc.xml`). `src/build_culture.py` counts sights within 10 km, UNESCO sites within 25 km, and names the three best-known
sights (most alternate names).
Check: `python src/build_culture.py` shows the first cities; spot-check ones you know (Paris should list the Eiffel Tower/Louvre area).
```bash
git add . && git commit -m "Culture data from UNESCO and GeoNames extracts"
```

### 10. Select 250 complete cities
`src/select_cities.py` + a call in `load_data.py`: keep the first 250 pool cities (in priority order) with **all** of: country GDP,
urbanisation and arrivals; 12 weather months; >=1 attraction, 3 attraction names, a heritage count; an airport with >=1 route.
Dropped cities are printed with the reason. Add `tests/test_select_cities.py`.
Check: `python src/db.py && python src/load_data.py` — expect "Selecting up to 250 cities..." and the list of dropped cities.
```bash
git add . && git commit -m "Select 250 cities with complete data; report why others were dropped"
```

### 11. Docs, tests and Docker
Write `README.md`, `API_GUIDE.md`, `DATA_SOURCES.md`, this guide, the `Dockerfile` and `.dockerignore` (Part B).
Check: `python -m pytest -q` passes; `docker build -t city-breaks .` succeeds.
```bash
git add . && git commit -m "Docs and Docker"
```

---

## Part B — Rebuilding the real dataset later

```bash
python src/fetch_cities.py            # 1. candidate cities (overwrites data/cities.csv)
python src/fetch_countries.py         # 2.
python src/fetch_tourism.py           # 3.
python src/fetch_weather.py           # 4. resumable; --fresh restarts
python src/download_raw_data.py       # 5. extracts into data/raw/
python src/fetch_airports.py          # 6.
python src/build_culture.py           # 7.
rm -f data/city_breaks.db
python src/db.py && python src/load_data.py && python src/build_features.py
python src/cluster.py && python src/classify.py
streamlit run app.py
```
If `load_data.py` says fewer than 250 complete cities are available, look at the "Dropped" list: missing GeoNames
country files, a UNESCO file that didn't parse, or countries the World Bank has no arrivals for are the usual causes.
Add more names to `src/tourist_cities.py` to widen the pool.

---

# Part C — How Docker works

### The problem Docker solves

"It works on my machine" is a real problem: your laptop has a
particular Python version, particular versions of pandas/scikit-learn,
maybe even a particular operating system. Someone else's machine has
different versions of all of that. Code that works for you can break
for them for reasons that have nothing to do with your code being
wrong.

A **container** is a way of packaging your code together with
*everything it needs to run* — the exact Python version, the exact
libraries — into one self-contained unit. That unit runs the same way
on your laptop, your teammate's laptop, and a real server, because
it's not relying on whatever happens to already be installed there.

A container is **not** a virtual machine. A VM emulates an entire
computer, including its own operating system kernel, which is slow to
start and heavy on resources. A container shares the host machine's
kernel and only packages the application layer — it starts in
milliseconds and uses a fraction of the resources of a VM.

### Image vs. container — the two words people mix up

- An **image** is the packaged, frozen recipe: "Python 3.12, plus
  these pip packages, plus this code." It's a file (well, a set of
  layered files) sitting on disk. It doesn't run — it just exists.
- A **container** is a *running instance* of an image. You can start
  ten containers from the same image, the same way you can open ten
  copies of the same document.

`docker build` turns a `Dockerfile` into an image.
`docker run` starts a container from an image.

### Why this project only needs ONE container

Projects that use a database server (PostgreSQL, MySQL, ...) need
*two* containers running together — one for the app, one for the
database — usually coordinated with a second tool called Docker
Compose. This project uses SQLite instead, which stores its entire
database as a single file rather than running as a separate server.
That means there's nothing else to coordinate: **one container is the
whole application.** This is exactly the same reason `src/db.py`
needs no host/port/password to connect to anything — a file doesn't
have any of those.

### Reading our `Dockerfile` line by line

```dockerfile
FROM python:3.12-slim
```
Every image starts from a **base image** — you don't build Python
itself from scratch. `python:3.12-slim` is an official image that
already has Python 3.12 installed on a small Linux base.

```dockerfile
WORKDIR /app
```
Sets the "current folder" *inside the container* to `/app`. Every
command after this runs from there. This `/app` only exists inside the
container — it has nothing to do with any folder on your computer.

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
Copies just `requirements.txt` in first, then installs it. This looks
odd — why not copy everything at once? Docker builds images in
**layers**, and caches each layer. If you later change a `.py` file
but not `requirements.txt`, Docker reuses the cached "pip install"
layer instead of re-downloading every package from scratch. Ordering
your Dockerfile from "changes rarely" to "changes often" makes
rebuilds much faster.

```dockerfile
COPY . .
```
Now copy everything else (your actual code and CSV data) into `/app`.

```dockerfile
RUN python src/db.py && python src/load_data.py && python src/build_features.py && python src/cluster.py
```
Builds the database **while the image itself is being built**, not
when the container later starts. This means the resulting image is
immediately ready to serve the app the moment someone runs it — no
"now run these four extra commands" step is needed afterwards. This
only works because the data (`data/*.csv`) was already copied in by
the line above.

```dockerfile
EXPOSE 8501
```
Documents that this container listens on port 8501. This line alone
doesn't make anything reachable from outside — it's a note to humans
(and to the `-p` flag on `docker run`) about which port matters.

```dockerfile
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```
The command that runs when a container starts from this image. Note
`--server.address=0.0.0.0`: inside a container, Streamlit defaults to
listening only on `localhost`, which — *inside the container* — is not
reachable from outside it. `0.0.0.0` means "listen on every network
interface," which is what lets `docker run -p` actually work.

### The commands you'll actually type

| Command | What it does |
|---|---|
| `docker build -t city-breaks .` | Build an image from the `Dockerfile` in this folder, and name it `city-breaks` |
| `docker run -p 8501:8501 city-breaks` | Start a container from that image, mapping container port 8501 to `localhost:8501` on your machine |
| `docker run -p 8501:8501 -v $(pwd)/data:/app/data city-breaks` | Same, but use *your* `data/` folder instead of the one baked into the image — so changes (like a fresh database) persist after the container stops |
| `docker ps` | List running containers |
| `docker stop <container-id>` | Stop a running container (get the ID from `docker ps`) |
| `docker images` | List images you've built or downloaded |

### A note on volumes, since you'll see the term around Docker

A **volume** is storage that lives outside a container's own
filesystem, so it survives even after the container is deleted —
useful for a database you don't want to lose. The `-v $(pwd)/data:/app/data`
example above is technically a *bind mount* (mapping a folder on your
own machine directly into the container) rather than a Docker-managed
named volume, but it solves the same problem and is simpler to
understand when you're starting out: whatever's in your local `data/`
folder is what the container sees, and whatever the container writes
to `/app/data` shows up in your local folder too.
