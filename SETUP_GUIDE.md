# Setup Guide: How Docker Works in This Project

This document explains what the README doesn't: what a container
actually is, and what each line in `Dockerfile` does.

(A step-by-step, git-commit-by-commit guide to building this project
from an empty folder is intentionally not included here — that's
being put together separately.)

---

## How Docker works
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
