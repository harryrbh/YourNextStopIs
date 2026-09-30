"""
fetch_weather.py — replaces data/weather.csv with real monthly climate
normals (temperature and rainfall) for every city in data/cities.csv.
No API key needed.

WHY THIS NO LONGER USES OPEN-METEO'S ARCHIVE API
------------------------------------------------------------------
Open-Meteo's free tier doesn't count "1 request = 1 call". Each request
is weighted by how much data it asks for — roughly (locations) x (days of
history / 14). Ten years of daily data for 30 cities is on the order of
8,000 weighted calls in a single request, against free limits of about
600 per minute / 5,000 per hour / 10,000 per day. That is why exactly one
batch got through before every other one was rejected (429), and why no
amount of retry tuning could fix it: the whole job was simply bigger than
the quota. Even one city at a time, ~300 cities would cost ~80,000
weighted calls.

NASA POWER already publishes what we were computing by hand — 30-year
MONTHLY climatology (average temperature and rainfall for each calendar
month) at any coordinate — so we need ONE small request per city (~300
in total), with nothing to average ourselves.

    https://power.larc.nasa.gov/api/temporal/climatology/point
        parameters=T2M,PRECTOTCORR  community=RE  latitude=..  longitude=..

  T2M          mean air temperature at 2 m, degrees C
  PRECTOTCORR  bias-corrected precipitation, mm PER DAY (monthly average)

RESUMABLE + POLITE
------------------------------------------------------------------
* Every request goes through http_util.get_json(): a 429/5xx retries THAT
  request in place (obeying Retry-After, else exponential backoff) and the
  request pace adapts to what the server tolerates.
* Results are appended to data/weather.csv after every city, and cities
  already in it are skipped — if you're interrupted, or a few cities fail,
  just run the script again and it carries on where it left off.
  Use --fresh to start over.

Precipitation is stored as TOTAL mm PER MONTH (daily average x days in the
month), which is what build_features.py's comfort formula and the City
Details chart ("Rainfall (mm)") both assume. The old script stored a
per-DAY average (~2 mm instead of ~60 mm), so the rain penalty in the
weather score was effectively switched off.

Run it with:
    python src/fetch_weather.py           # resume / fill in what's missing
    python src/fetch_weather.py --fresh   # start from scratch
"""
import calendar
import os
import sys

import pandas as pd

from http_util import RequestFailed, Throttle, get_json

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
COLUMNS = ["city_name", "month", "temperature_c", "precipitation_mm"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
MISSING_VALUE = -999  # NASA POWER's "no data" marker

# Minimum gap between requests; http_util widens it automatically if the
# server pushes back.
REQUEST_DELAY_SECONDS = 0.5


def parse_climatology(city_name: str, payload: dict) -> pd.DataFrame:
    """Turn NASA POWER's response into 12 rows (one per month). Raises
    ValueError if any month is missing, so we never store half a year."""
    try:
        params = payload["properties"]["parameter"]
        temps, rain = params["T2M"], params["PRECTOTCORR"]
    except (KeyError, TypeError) as e:
        raise ValueError(f"unexpected response shape (missing {e})") from e

    rows = []
    for month_number, key in enumerate(MONTHS, start=1):
        t, p = temps.get(key), rain.get(key)
        if t is None or p is None or t == MISSING_VALUE or p == MISSING_VALUE:
            raise ValueError(f"no data for {key}")
        # A 'normal' month: use 28.25 days for February (leap-year average).
        days = 28.25 if month_number == 2 else calendar.monthrange(2001, month_number)[1]
        rows.append({
            "city_name": city_name,
            "month": month_number,
            "temperature_c": round(float(t), 2),
            "precipitation_mm": round(float(p) * days, 1),
        })
    return pd.DataFrame(rows, columns=COLUMNS)


def fetch_city(city: pd.Series, throttle: Throttle) -> pd.DataFrame:
    payload = get_json(
        URL,
        params={
            "parameters": "T2M,PRECTOTCORR",
            "community": "RE",
            "latitude": round(float(city["latitude"]), 4),
            "longitude": round(float(city["longitude"]), 4),
            "format": "JSON",
        },
        throttle=throttle,
        label=city["name"],
    )
    return parse_climatology(city["name"], payload)


def main():
    fresh = "--fresh" in sys.argv
    cities = pd.read_csv(f"{DATA_DIR}/cities.csv", keep_default_na=False, na_values=[""])
    out_path = f"{DATA_DIR}/weather.csv"

    done = set()
    if os.path.exists(out_path) and not fresh:
        existing = pd.read_csv(out_path)
        counts = existing.groupby("city_name")["month"].nunique()
        done = set(counts[counts == 12].index)
        # rewrite the file with only complete cities (drops any half-written city)
        existing[existing["city_name"].isin(done)].to_csv(out_path, index=False)
    else:
        pd.DataFrame(columns=COLUMNS).to_csv(out_path, index=False)

    todo = cities[~cities["name"].isin(done)]
    print(f"{len(done)} cities already have weather; fetching {len(todo)} more.")

    throttle = Throttle(min_interval=REQUEST_DELAY_SECONDS, max_interval=30.0)
    failed = []
    for i, (_, city) in enumerate(todo.iterrows(), start=1):
        try:
            monthly = fetch_city(city, throttle)
        except (RequestFailed, ValueError) as e:
            print(f"  [{i}/{len(todo)}] {city['name']}: FAILED ({e})")
            failed.append(city["name"])
            continue
        monthly.to_csv(out_path, mode="a", header=False, index=False)  # save as we go
        if i % 25 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] done (request gap now {throttle.interval:.1f}s)")

    total = pd.read_csv(out_path)["city_name"].nunique()
    print(f"\nweather.csv now covers {total} of {len(cities)} cities.")
    if failed:
        print(
            f"{len(failed)} failed: {', '.join(failed)}\n"
            "Re-run this script to retry just those. Cities that still have no "
            "weather are dropped by load_data.py (they are never given a fake score)."
        )


if __name__ == "__main__":
    main()
