"""
fetch_weather.py — replaces data/weather.csv with real monthly climate
data from Open-Meteo. No API key needed.

This one is different from the others: it needs data/cities.csv to
already exist (so it knows which coordinates to ask about).

WHY THIS SENDS ONE REQUEST PER BATCH OF CITIES, NOT ONE PER CITY
------------------------------------------------------------------
An earlier version of this script made one HTTP request per city —
200 cities meant 200 requests, and Open-Meteo's free tier (a shared,
sometimes-congested service) started returning 429 (Too Many
Requests) partway through nearly every run, no matter how the retries
were tuned.

Open-Meteo's archive endpoint actually supports asking for MANY
locations in a single request: pass comma-separated lists for
`latitude`/`longitude` (e.g. `latitude=48.85,41.9&longitude=2.35,12.5`)
instead of one pair, and it replies with a JSON *array* of results —
one per location, in the same order you asked — instead of a single
object. Documented at https://open-meteo.com/en/features (up to 1,000
locations per call). This script batches cities into groups of
BATCH_SIZE and sends one request per batch, so 200 cities becomes
around 7 requests instead of 200 — both far less likely to be rate
limited, and far faster.

Run it with:
    python src/fetch_weather.py
"""
import os
import time

import pandas as pd
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
URL = "https://archive-api.open-meteo.com/v1/archive"

# We ask for ten years of daily history and average it ourselves into
# monthly numbers — Open-Meteo doesn't have a "monthly normals"
# endpoint, so this is the standard way to build one.
START_YEAR = 2015
END_YEAR = 2024

# How many cities go in one request. Open-Meteo allows up to 1,000,
# but the archive endpoint returns ten years of DAILY data per city,
# so a very large batch means a very large (slow to download, easy to
# time out) response. 30 is a conservative middle ground — tune it up
# if you want fewer, bigger requests, or down if a batch times out.
BATCH_SIZE = 30
# Be polite to the API between batches.
REQUEST_DELAY_SECONDS = 1.0
# If a whole batch gets rate limited (429), how many times to retry
# it, waiting longer each time.
MAX_RETRIES_PER_BATCH = 4
RETRY_BACKOFF_SECONDS = 20


def fetch_batch(cities: pd.DataFrame) -> list[dict] | None:
    """Fetch weather for every city in this batch in ONE request.
    Returns a list of Open-Meteo's per-location result objects (same
    order as `cities`), or None if the whole batch was rate limited.
    """
    params = {
        "latitude": ",".join(str(v) for v in cities["latitude"]),
        "longitude": ",".join(str(v) for v in cities["longitude"]),
        "start_date": f"{START_YEAR}-01-01",
        "end_date": f"{END_YEAR}-12-31",
        "daily": "temperature_2m_mean,precipitation_sum",
        "timezone": "UTC",
    }
    response = requests.get(URL, params=params, timeout=120)
    if response.status_code == 429:
        return None
    response.raise_for_status()
    data = response.json()

    # A single-city batch (the last, odd-sized one) gets back a plain
    # object, not a list of one — Open-Meteo only switches to a list
    # once more than one location is requested. Normalise both shapes
    # to always be a list here, so the rest of the code doesn't care.
    return data if isinstance(data, list) else [data]


def monthly_from_daily(city_name: str, daily: dict) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temperature_c": daily["temperature_2m_mean"],
            "precipitation_mm": daily["precipitation_sum"],
        }
    )
    df["month"] = df["date"].dt.month
    monthly = df.groupby("month", as_index=False).agg(
        temperature_c=("temperature_c", "mean"),
        precipitation_mm=("precipitation_mm", "mean"),
    )
    monthly.insert(0, "city_name", city_name)
    return monthly


def run_batches(cities: pd.DataFrame) -> tuple[list[pd.DataFrame], pd.DataFrame]:
    """Try every batch once. Returns (results, still_missing) — the
    monthly DataFrames for cities that succeeded, and the rows for
    cities in batches that got rate-limited and should be retried."""
    results = []
    missing_rows = []
    batches = [cities.iloc[i:i + BATCH_SIZE] for i in range(0, len(cities), BATCH_SIZE)]

    for batch_num, batch in enumerate(batches, start=1):
        print(f"  Batch {batch_num}/{len(batches)} ({len(batch)} cities)...", end=" ")
        try:
            locations = fetch_batch(batch)
        except requests.RequestException as e:
            print(f"failed ({e}) — will not retry this batch")
            continue

        if locations is None:
            print("rate limited, will retry later")
            missing_rows.append(batch)
        else:
            ok = 0
            for (_, row), location in zip(batch.iterrows(), locations):
                daily = location.get("daily")
                if daily:
                    results.append(monthly_from_daily(row["name"], daily))
                    ok += 1
            print(f"ok ({ok}/{len(batch)})")
        time.sleep(REQUEST_DELAY_SECONDS)

    still_missing = pd.concat(missing_rows, ignore_index=True) if missing_rows else cities.iloc[0:0]
    return results, still_missing


def main():
    cities = pd.read_csv(f"{DATA_DIR}/cities.csv")
    remaining = cities
    all_results = []

    for attempt in range(1, MAX_RETRIES_PER_BATCH + 1):
        if remaining.empty:
            break
        if attempt > 1:
            wait = RETRY_BACKOFF_SECONDS * attempt
            print(f"\nRetry {attempt}/{MAX_RETRIES_PER_BATCH}: waiting {wait}s before "
                  f"re-trying {len(remaining)} cities still missing...")
            time.sleep(wait)
        results, remaining = run_batches(remaining)
        all_results.extend(results)

    result = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame(
        columns=["city_name", "month", "temperature_c", "precipitation_mm"]
    )
    out_path = f"{DATA_DIR}/weather.csv"
    result.to_csv(out_path, index=False)
    fetched_cities = result["city_name"].nunique() if not result.empty else 0
    print(f"\nSaved {len(result)} monthly rows ({fetched_cities} cities) to {out_path}")

    if not remaining.empty:
        print(
            f"\n{len(remaining)} cities still have no weather data and will get a "
            f"neutral weather score (50/100) rather than a real one: "
            f"{', '.join(remaining['name'])}\n"
            "You can just re-run this script — it always rewrites the whole file, "
            "so re-fetching cities that already worked costs nothing — or lower "
            "BATCH_SIZE near the top of this file if requests are timing out rather "
            "than being rate limited."
        )


if __name__ == "__main__":
    main()
