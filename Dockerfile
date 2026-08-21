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

# Tell Docker the app listens on this port (documentation only —
# doesn't actually open the port; compose.yaml/docker run does that).
EXPOSE 8501

# The command that runs when the container starts.
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
