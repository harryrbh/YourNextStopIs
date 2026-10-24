import calendar
import os
import sys

import pandas as pd

from httpClient import RequestFailed, Throttle, getJson

dataDirectory = os.path.join(os.path.dirname(__file__), "..", "data")
weatherUrl = "https://power.larc.nasa.gov/api/temporal/climatology/point"
weatherColumns = ["city_name", "month", "temperature_c", "precipitation_mm"]
monthKeys = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
missingValue = -999  # NASA POWER's "no data" marker

# Minimum gap between requests; httpClient widens it if the server pushes back
requestDelaySeconds = 0.5


def parseClimatology(cityName: str, payload: dict) -> pd.DataFrame:
    """Turn NASA POWER's response into 12 rows (one per month)."""
    try:
        params = payload["properties"]["parameter"]
        temps, rain = params["T2M"], params["PRECTOTCORR"]
    except (KeyError, TypeError) as error:
        raise ValueError(f"unexpected response shape (missing {error})") from error

    monthlyRows = []
    for monthNumber, monthKey in enumerate(monthKeys, start=1):
        temperature, precipitation = temps.get(monthKey), rain.get(monthKey)
        if temperature is None or precipitation is None or temperature == missingValue or precipitation == missingValue:
            raise ValueError(f"no data for {monthKey}")
        # A 'normal' month: use 28.25 days for February (leap-year average)
        days = 28.25 if monthNumber == 2 else calendar.monthrange(2001, monthNumber)[1]
        monthlyRows.append({
            "city_name": cityName,
            "month": monthNumber,
            "temperature_c": round(float(temperature), 2),
            "precipitation_mm": round(float(precipitation) * days, 1),
        })
    return pd.DataFrame(monthlyRows, columns=weatherColumns)


def fetchCity(city: pd.Series, throttle: Throttle) -> pd.DataFrame:
    payload = getJson(
        weatherUrl,
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
    return parseClimatology(city["name"], payload)


def main():
    fresh = "--fresh" in sys.argv
    cities = pd.read_csv(f"{dataDirectory}/cities.csv", keep_default_na=False, na_values=[""])
    outPath = f"{dataDirectory}/weather.csv"

    done = set()
    if os.path.exists(outPath) and not fresh:
        existing = pd.read_csv(outPath)
        counts = existing.groupby("city_name")["month"].nunique()
        done = set(counts[counts == 12].index)
        # Rewrite the file with only complete cities (drops any half-written city)
        existing[existing["city_name"].isin(done)].to_csv(outPath, index=False)
    else:
        pd.DataFrame(columns=weatherColumns).to_csv(outPath, index=False)

    todo = cities[~cities["name"].isin(done)]
    print(f"{len(done)} cities already have weather; fetching {len(todo)} more.")

    throttle = Throttle(minimumInterval=requestDelaySeconds, maximumInterval=30.0)
    failed = []
    for cityNumber, (_, city) in enumerate(todo.iterrows(), start=1):
        try:
            monthly = fetchCity(city, throttle)
        except (RequestFailed, ValueError) as error:
            print(f"  [{cityNumber}/{len(todo)}] {city['name']}: FAILED ({error})")
            failed.append(city["name"])
            continue
        monthly.to_csv(outPath, mode="a", header=False, index=False)  # Save as we go
        if cityNumber % 25 == 0 or cityNumber == len(todo):
            print(f"  [{cityNumber}/{len(todo)}] done (request gap now {throttle.interval:.1f}s)")

    total = pd.read_csv(outPath)["city_name"].nunique()
    print(f"\nweather.csv now covers {total} of {len(cities)} cities.")
    if failed:
        print(
            f"{len(failed)} failed: {', '.join(failed)}\n"
            "Re-run this script to retry just those. Cities that still have no "
            "weather are dropped by loadDataToDatabase.py (they are never given a fake score)."
        )


if __name__ == "__main__":
    main()
