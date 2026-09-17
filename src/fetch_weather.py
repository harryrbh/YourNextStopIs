"""
fetch_weather.py — replaces data/weather.csv with real monthly climate
data from Open-Meteo. No API key needed.

This one is different from the others: it needs data/cities.csv to
already exist (so it knows which coordinates to ask about), and it
makes ONE request per city. Run fetch_cities.py first.

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

# Be polite to the free API between successful requests.
REQUEST_DELAY_SECONDS = 0.5
# If Open-Meteo responds 429 (Too Many Requests), wait this long and
# try again, up to this many times, backing off further each time.
# With 200 cities and only a 0.2s gap, a plain run genuinely hits this
# limit partway through and — without retrying — permanently skips
# roughly half the cities rather than just running a bit slower.
MAX_RETRIES = 4
RETRY_BACKOFF_SECONDS = 10


def fetch_one_city(name: str, lat: float, lon: float) -> pd.DataFrame:
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": f"{START_YEAR}-01-01",
        "end_date": f"{END_YEAR}-12-31",
        "daily": "temperature_2m_mean,precipitation_sum",
        "timezone": "UTC",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        response = requests.get(URL, params=params, timeout=30)
        if response.status_code == 429:
            wait = RETRY_BACKOFF_SECONDS * attempt
            print(f"  Rate limited — waiting {wait}s before retrying ({attempt}/{MAX_RETRIES})...")
            time.sleep(wait)
            continue
        response.raise_for_status()
        daily = response.json()["daily"]

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
        monthly.insert(0, "city_name", name)
        return monthly

    raise requests.RequestException(f"Still rate-limited after {MAX_RETRIES} retries")


def main():
    cities = pd.read_csv(f"{DATA_DIR}/cities.csv")

    all_months = []
    skipped = []
    for i, row in cities.iterrows():
        print(f"[{i + 1}/{len(cities)}] Fetching weather for {row['name']}...")
        try:
            all_months.append(fetch_one_city(row["name"], row["latitude"], row["longitude"]))
        except requests.RequestException as e:
            # One bad city shouldn't kill the whole run — skip and carry on.
            print(f"  Skipped {row['name']}: {e}")
            skipped.append(row["name"])
        time.sleep(REQUEST_DELAY_SECONDS)

    result = pd.concat(all_months, ignore_index=True)
    out_path = f"{DATA_DIR}/weather.csv"
    result.to_csv(out_path, index=False)
    print(f"\nSaved {len(result)} monthly rows ({result['city_name'].nunique()} cities) to {out_path}")
    if skipped:
        print(
            f"\n{len(skipped)} cities have no weather data and will get a neutral "
            f"weather score (50/100) rather than a real one: {', '.join(skipped)}\n"
            "If a lot of cities ended up here, Open-Meteo's rate limit is stricter "
            "right now than usual — try raising REQUEST_DELAY_SECONDS and "
            "RETRY_BACKOFF_SECONDS near the top of this file, or just re-run the "
            "script (it doesn't matter that it'll re-fetch cities that already "
            "worked; it always rewrites the whole file)."
        )


if __name__ == "__main__":
    main()
