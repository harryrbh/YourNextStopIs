# Start from a small, official Python image.
FROM python:3.12-slim

# All commands below run inside this folder, inside the container.
WORKDIR /app

# Copy just the requirements file first and install it. Docker caches
# each step — as long as requirements.txt doesn't change, this slow
# step is skipped on future builds, even if you edit your Python code.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy everything else (this changes often, so it goes last).
COPY . .

# Build the database inside the image, from the CSV files, so the
# container is ready to run the moment it starts — no extra setup
# commands needed after `docker run`.
RUN python src/db.py && python src/load_data.py && python src/build_features.py && python src/cluster.py

# Tell Docker the app listens on this port (documentation only —
# doesn't actually open the port; the -p flag on `docker run` does that).
EXPOSE 8501

# The command that runs when the container starts.
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
