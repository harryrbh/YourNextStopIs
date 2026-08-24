# Setup Guide: How This Project Works, From Scratch

This document explains two things the README doesn't:

1. **How Docker actually works** — what a container is, and what
   each line in `Dockerfile` does.
2. **How to build this entire project yourself**, starting from an
   empty folder, including every `git` command — so you understand
   how a real project gets built up commit by commit, not just how to
   run the finished thing.

---

## Part 1: How Docker works

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

---

## Part 2: Building this project from scratch

This section is a from-scratch walkthrough: an empty folder to a
working, version-controlled project. It also doubles as an
introduction to a normal `git` workflow — small, working commits, in
an order that makes sense to someone reading the history later.

### Step 0: Prerequisites

Install:
- Python 3.10+
- Git
- Docker Desktop (optional — only needed for Part 1 above)

Check they're installed:
```bash
python --version
git --version
```

Notice PostgreSQL/MySQL/any database server is **not** in this list.
SQLite ships as part of Python's standard library — there is
genuinely nothing extra to install for the database in this project.

### Step 1: Create the project folder and initialise git

```bash
mkdir city-breaks
cd city-breaks
git init
```

`git init` turns this folder into a git repository — from now on, git
can track every change you make to it. Nothing is saved yet; `git
init` just switches tracking on.

Tell git who you are (only needed once per machine):
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

### Step 2: Add a `.gitignore` before anything else

```bash
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.venv/
venv/
*.joblib
.pytest_cache/
data/city_breaks.db
EOF
```

The last line matters: the database file is *generated* from the CSVs
in `data/` by scripts you're about to write — committing it would just
bloat the repository with something anyone can recreate in seconds,
and it would drift out of sync with the CSVs over time.

Commit this first, tiny step:
```bash
git add .gitignore
git commit -m "Add .gitignore"
```

Small, working commits like this — one idea per commit — are what
make a project's history actually useful later, when you (or a
teammate) need to find *when* and *why* something changed.

### Step 3: Set up the Python environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

A **virtual environment** is a private, isolated copy of Python just
for this project — packages you install here don't affect any other
project on your machine, and vice versa. This is why `.venv/` is in
`.gitignore`: it's a local, disposable folder, often hundreds of
megabytes, that anyone can recreate in seconds from `requirements.txt`.
Committing it would bloat the repository for no benefit.

Create `requirements.txt` and install it:
```bash
cat > requirements.txt << 'EOF'
pandas
SQLAlchemy
scikit-learn
networkx
geopy
matplotlib
streamlit
pytest
requests
EOF

pip install -r requirements.txt
```

```bash
git add requirements.txt
git commit -m "Add Python dependencies"
```

### Step 4: Design the database schema

Create `sql/schema.sql` with your `CREATE TABLE` statements (see the
finished file in this project for a full example — countries, cities,
weather, airports, routes, and a `city_features` table that everything
downstream reads from).

A small habit worth having from the start: decide your table names and
column names *before* writing the code that fills them in. Renaming a
column after five scripts already depend on the old name is far more
annoying than getting it right once, up front.

```bash
git add sql/schema.sql
git commit -m "Add database schema"
```

### Step 5: Write the database connection helper

Create `src/db.py` with one function, `get_engine()`, that returns a
SQLAlchemy engine pointing at a `.db` file, plus an `init_db()`
function that runs `schema.sql` against it. Every other script imports
`get_engine()` instead of opening the file directly, so if you ever
change where the database lives, there's exactly one place to update.

```bash
mkdir src
# write src/db.py
git add src/db.py
git commit -m "Add database connection helper"
```

### Step 6: Get some data, and write the loader

Collect (or generate) your raw data as CSV files in `data/`. Then
write `src/load_data.py`: read each CSV with pandas, clean it a
little (drop rows with missing required fields, check coordinates are
physically valid, drop duplicates), and insert it into the database
with `DataFrame.to_sql()`.

```bash
mkdir data
# add your .csv files
# write src/load_data.py
git add data/ src/load_data.py
git commit -m "Add data loading script"
```

### Step 7: Feature engineering

Write `src/build_features.py`: read the raw tables back out, compute
whatever derived numbers your recommender needs (averages, counts,
ratios), rescale each one to a comparable 0–100 range, and combine
them into `city_features`. This is usually the file you'll revisit
most as you refine the project — keep it in one place rather than
scattered across many small files, so you can see the whole scoring
logic at a glance.

```bash
git add src/build_features.py
git commit -m "Add feature engineering"
```

### Step 8: The machine learning pieces

Two small, separate scripts:
- `src/cluster.py` — K-Means, to group similar cities
- `src/recommend.py` — K-Nearest-Neighbours, to match a user's
  preferences to the closest cities

Commit each separately — they're independent ideas, so they deserve
independent commits, even though both are "machine learning":

```bash
git add src/cluster.py
git commit -m "Add K-Means clustering"

git add src/recommend.py
git commit -m "Add KNN recommender"
```

### Step 9: Small shared helpers

Before building the app pages, a few small files that every page will
share are worth writing once:
- `labels.py` — plain-English names for every column, so nothing
  shown on screen is a raw database column name
- `theme.py` — one place for your app's colours
- `distance.py` — real-world distance between two coordinates, using
  `geopy.distance.geodesic()` rather than writing your own geographic
  maths

```bash
git add labels.py theme.py distance.py
git commit -m "Add shared display helpers"
```

### Step 10: Build the app

Start with `app.py` as the home page, and a `data_access.py` holding
one cached function that every page calls to load data — kept
separate from `app.py` itself because Streamlit only allows
`st.set_page_config()` to run once per page, and `app.py` calls it.

Streamlit automatically turns every file inside a `pages/` folder into
an extra sidebar page, in filename order — that's the only "magic"
involved; each page is still just a normal Python script that runs top
to bottom.

```bash
mkdir pages
mkdir .streamlit
# write .streamlit/config.toml (theme), app.py, data_access.py,
# then pages/1_Explore.py, pages/2_Recommend.py, pages/3_Compare.py
git add .streamlit app.py data_access.py pages/
git commit -m "Add Streamlit app"
```

### Step 11: Containerise it

Write `Dockerfile` (see Part 1 above for what each line does), plus
`.dockerignore` (same idea as `.gitignore`, but for what Docker should
skip when building the image).

```bash
git add Dockerfile .dockerignore
git commit -m "Add Docker deployment"
```

### Step 12: Tests

Write a handful of `pytest` tests — pure-logic ones (like checking
`normalise_0_100()` actually returns values between 0 and 100) don't
need a database and will always run; ones that need real data (like
checking the recommender) should skip gracefully if the database isn't
available, rather than failing confusingly.

```bash
mkdir tests
git add tests/
git commit -m "Add tests"
```

### Step 13: Documentation

```bash
git add README.md SETUP_GUIDE.md API_GUIDE.md
git commit -m "Add documentation"
```

### Step 14: Push to GitHub

Create an empty repository on GitHub first (no README, no
`.gitignore` — you already have those), then:

```bash
git remote add origin https://github.com/<your-username>/city-breaks.git
git branch -M main
git push -u origin main
```

`git remote add` tells your local repository where the "origin" for
this project lives online. `git branch -M main` renames your current
branch to `main` (GitHub's default). `git push -u origin main` uploads
every commit, and `-u` remembers this remote/branch pairing so future
pushes can just be `git push`.

### A note on commit habits

Looking back at the steps above, notice the pattern: each commit does
**one thing**, and the project **runs** after every single commit (or
at least, every commit that isn't purely documentation). That's the
goal to aim for — not "commit whenever you remember to," but "commit
each time you finish one working piece." It makes `git log` genuinely
useful later, and it means `git revert` or `git bisect` (tools for
undoing or finding a bug) actually work cleanly, because each commit
is a small, coherent step rather than a tangle of unrelated changes.
