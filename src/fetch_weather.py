"""
fetch_weather.py — replaces data/weather.csv with real monthly climate
data from Open-Meteo. No API key needed.

This one is different from the others: it needs data/cities.csv to
already exist (so it knows which coordinates to ask about), and it
makes ONE request per city. Run fetch_cities.py first.

A NOTE ON RATE LIMITING, AND WHY THIS SCRIPT RETRIES IN ROUNDS
------------------------------------------------------------------
Open-Meteo's published free-tier limit is generous (600 calls/minute,
per their terms page), but the "archive" endpoint this script uses is
much heavier per call than a normal forecast request — it's pulling
ten years of daily history each time — and it's a shared, sometimes
congested free service, so 429 (Too Many Requests) responses can
happen even at a modest pace.

The natural first instinct is "retry the same city a few times before
giving up" — but if the *whole* window (e.g. the last minute) is rate
limited, retrying the SAME city four times in the next thirty seconds
just burns through those retries inside the same still-limited window
and gives up anyway, taking a long time to fail. This script instead
does a full PASS over every city first (skipping — not retrying — any
that get a 429, so the pass stays quick), then does further ROUNDS
that retry only the cities still missing, with a real cooldown before
each round starts. That cooldown is what actually lets the rate limit
recover, which repeatedly retrying in place doesn't.

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

# Be polite to the API between requests within a pass.
REQUEST_DELAY_SECONDS = 0.5
# How many times to sweep back through the cities that are still
# missing weather data. Each round after the first starts with a real
# wait, giving the rate limit time to actually reset.
MAX_ROUNDS = 4
# Cooldown before round 2, 3, 4, ... — increasing, since if the first
# retry round still hits 429s, the window needs longer to clear.
COOLDOWN_SECONDS = [0, 45, 90, 150]


def fetch_one_city(name: str, lat: float, lon: float) -> pd.DataFrame | None:
    """Returns a DataFrame of monthly weather for this city, or None
    if the request was rate-limited (429) — the caller decides whether
    to retry it in a later round. Any other failure (a genuine HTTP
    error, a network problem) is raised normally rather than silently
    treated the same as a 429, since those aren't fixed by waiting.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": f"{START_YEAR}-01-01",
        "end_date": f"{END_YEAR}-12-31",
        "daily": "temperature_2m_mean,precipitation_sum",
        "timezone": "UTC",
    }
    response = requests.get(URL, params=params, timeout=30)
    if response.status_code == 429:
        return None
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


def run_one_round(cities: pd.DataFrame, round_num: int) -> tuple[list[pd.DataFrame], pd.DataFrame]:
    """Try every city in `cities`. Returns (results, still_missing) —
    the DataFrames for cities that succeeded, and the rows for cities
    that got rate-limited and should be tried again next round."""
    results = []
    missing_rows = []
    for i, row in cities.iterrows():
        print(f"  [round {round_num}] [{i + 1}/{len(cities)}] {row['name']}...", end=" ")
        try:
            monthly = fetch_one_city(row["name"], row["latitude"], row["longitude"])
        except requests.RequestException as e:
            # A real error, not a rate limit — no point retrying this
            # one in a later round, so just skip it for good.
            print(f"failed ({e})")
            continue
        if monthly is None:
            print("rate limited, will retry later")
            missing_rows.append(row)
        else:
            print("ok")
            results.append(monthly)
        time.sleep(REQUEST_DELAY_SECONDS)
    still_missing = pd.DataFrame(missing_rows) if missing_rows else cities.iloc[0:0]
    return results, still_missing


def main():
    cities = pd.read_csv(f"{DATA_DIR}/cities.csv")
    remaining = cities
    all_results = []

    for round_num in range(1, MAX_ROUNDS + 1):
        if remaining.empty:
            break
        cooldown = COOLDOWN_SECONDS[round_num - 1] if round_num - 1 < len(COOLDOWN_SECONDS) else COOLDOWN_SECONDS[-1]
        if cooldown:
            print(f"\nCooling down {cooldown}s before round {round_num} ({len(remaining)} cities left)...")
            time.sleep(cooldown)
        results, remaining = run_one_round(remaining, round_num)
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
            f"\n{len(remaining)} cities still have no weather data after {MAX_ROUNDS} rounds "
            f"and will get a neutral weather score (50/100) rather than a real one: "
            f"{', '.join(remaining['name'])}\n"
            "Open-Meteo's free tier is especially congested right now if this list is "
            "long. You can just re-run this script — it always rewrites the whole "
            "file, so re-fetching cities that already worked costs nothing — or raise "
            "MAX_ROUNDS / COOLDOWN_SECONDS near the top of this file for a longer, "
            "more patient run."
        )


if __name__ == "__main__":
    main()
