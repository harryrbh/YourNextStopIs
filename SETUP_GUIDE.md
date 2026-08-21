# Setup Guide: How This Project Works, From Scratch

This document explains two things the README doesn't:

1. **How Docker actually works** — what a container is, what each
   line in `Dockerfile` and `compose.yaml` does, and why we need both.
2. **How to build this entire project yourself**, starting from an
   empty folder, including every `git` command — so you understand
   how a real project gets built up commit by commit, not just how to
   run the finished thing.

---

## Part 1: How Docker works

### The problem Docker solves

"It works on my machine" is a real problem: your laptop has a
particular Python version, particular versions of pandas/scikit-learn,
a particular PostgreSQL installation, maybe even a particular
operating system. Someone else's machine has different versions of
all of that. Code that works for you can break for them for reasons
that have nothing to do with your code being wrong.

A **container** is a way of packaging your code together with
*everything it needs to run* — the exact Python version, the exact
libraries, the exact OS-level dependencies — into one self-contained
unit. That unit runs the same way on your laptop, your teammate's
laptop, and a real server, because it's not relying on whatever
happens to already be installed there.

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
`docker run` (or `docker compose up`) starts a container from an image.

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
your Dockerfile from "changes rarely" to "changes often" makes rebuilds
much faster.

```dockerfile
COPY . .
```
Now copy everything else (your actual code) into `/app`.

```dockerfile
EXPOSE 8501
```
Documents that this container listens on port 8501. This line alone
doesn't make anything reachable from outside — it's a note to humans
(and to `compose.yaml`) about which port matters.

```dockerfile
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```
The command that runs when a container starts from this image. Note
`--server.address=0.0.0.0`: inside a container, Streamlit defaults to
listening only on `localhost`, which — *inside the container* — is not
reachable from outside it. `0.0.0.0` means "listen on every network
interface," which is what lets `compose.yaml`'s port mapping work.

### Why we need `compose.yaml` as well

Our app needs **two** things running at once: PostgreSQL and the
Streamlit app. You could start two containers by hand with two long
`docker run` commands, remembering to connect them to the same
network, remembering the right environment variables, in the right
order, every single time. `compose.yaml` writes all of that down once
so `docker compose up` can do it for you.

```yaml
services:
  db:
    image: postgres:16
```
This service doesn't build anything — it just runs the official,
pre-built `postgres:16` image directly. We don't need our own
Dockerfile for the database; someone already made a good one.

```yaml
    environment:
      POSTGRES_DB: city_breaks
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
```
Environment variables passed into the container. The official Postgres
image is written to look for exactly these variable names and create a
database matching them on first startup.

```yaml
    volumes:
      - pgdata:/var/lib/postgresql/data
```
Containers are meant to be disposable — stop one, throw it away, start
a fresh one. But a *database* can't be disposable, or you'd lose all
your data every time you restarted. A **volume** is storage that lives
outside the container's own filesystem, on the host machine, so it
survives even if the container is deleted. `pgdata` here is a named
volume Docker manages for you (declared at the bottom of the file);
`/var/lib/postgresql/data` is the path *inside the container* where
Postgres actually writes its files.

```yaml
    ports:
      - "5432:5432"
```
Format is `"host_port:container_port"`. This makes Postgres reachable
at `localhost:5432` from your own machine (useful if you want to
connect a database GUI tool to peek inside), not just from other
containers.

```yaml
  app:
    build: .
```
Unlike the `db` service, this one *does* build — from the `Dockerfile`
in the current folder (`.`).

```yaml
    depends_on:
      - db
```
Tells Docker Compose to start `db` before `app`. Note this only
controls *start order*, not *readiness* — Postgres accepting
connections can take a few seconds after the container starts, which
is why a production setup would generally have `src/db.py` retry on
connection failure (out of scope for this student project, but worth
knowing).

```yaml
    environment:
      POSTGRES_HOST: db
```
This is the detail that trips people up most: inside Docker's private
network, containers reach each other **by service name**, not by
`localhost`. From the `app` container's point of view, the database
lives at a host literally called `db` — that's the name Docker Compose
gives it automatically, taken straight from `services: db:` above.
`localhost` from inside the `app` container would mean "the app
container itself," which has no database running in it.

```yaml
    ports:
      - "8501:8501"
```
Same pattern as before — makes the Streamlit app reachable at
`localhost:8501` on your own machine.

### The commands you'll actually type

| Command | What it does |
|---|---|
| `docker compose up --build` | Build the `app` image (if it changed) and start both containers, logs streaming in your terminal |
| `docker compose up -d --build` | Same, but detached — runs in the background |
| `docker compose exec app <command>` | Run a one-off command *inside* the already-running `app` container (e.g. `docker compose exec app python src/load_data.py`) |
| `docker compose down` | Stop and remove both containers (the `pgdata` volume survives) |
| `docker compose down -v` | Same, but also delete the volume — **this deletes your database** |
| `docker compose logs -f app` | Follow the app container's logs live |
| `docker compose ps` | List running containers and their status |

---

## Part 2: Building this project from scratch

This section is a from-scratch walkthrough: an empty folder to a
working, version-controlled project. It also doubles as an
introduction to a normal `git` workflow — small, working commits, in
an order that makes sense to someone reading the history later.

### Step 0: Prerequisites

Install:
- Python 3.10+
- PostgreSQL, **or** Docker Desktop (either is fine — you don't need both)
- Git

Check they're installed:
```bash
python --version
git --version
```

### Step 1: Create the project folder and initialise git

```bash
mkdir city-break-recommender
cd city-break-recommender
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
.env
*.joblib
.pytest_cache/
EOF
```

Why *before* anything else: `.env` will hold your database password
once you create it in a later step. If you commit it once, it's in
your git history forever, even if you delete it later — history
doesn't forget. Getting `.gitignore` in place first means you never
have the chance to make that mistake.

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
psycopg2-binary
scikit-learn
networkx
plotly
streamlit
python-dotenv
pytest
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

Create `src/db.py` with one function, `get_engine()`, that reads
connection details from environment variables and returns a
SQLAlchemy engine. Every other script imports this instead of
connecting to Postgres directly — so if your connection details ever
change, there's exactly one place to update them.

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
physically valid, drop duplicates), and insert it into Postgres with
`DataFrame.to_sql()`.

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

### Step 9: Build the app

Start with `app.py` as the home page. Streamlit automatically turns
every file inside a `pages/` folder into an extra sidebar page, in
filename order — that's the only "magic" involved; each page is still
just a normal Python script that runs top to bottom.

```bash
mkdir pages
# write app.py, then pages/1_Explore.py, pages/2_Recommend.py, ...
git add app.py data_access.py pages/
git commit -m "Add Streamlit app"
```

### Step 10: Containerise it

Write `Dockerfile` and `compose.yaml` (see Part 1 above for what each
line does), plus `.dockerignore` (same idea as `.gitignore`, but for
what Docker should skip when building the image).

```bash
git add Dockerfile compose.yaml .dockerignore
git commit -m "Add Docker deployment"
```

### Step 11: Tests

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

### Step 12: Documentation

```bash
git add README.md SETUP_GUIDE.md
git commit -m "Add documentation"
```

### Step 13: Push to GitHub

Create an empty repository on GitHub first (no README, no
`.gitignore` — you already have those), then:

```bash
git remote add origin https://github.com/<your-username>/city-break-recommender.git
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
