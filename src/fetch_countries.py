"""
fetch_countries.py — replaces data/countries.csv with real data from
the REST Countries API. No API key needed.

Run it with:
    python src/fetch_countries.py

This OVERWRITES data/countries.csv. If you want to keep comparing
against the sample data, copy the old file somewhere first.
"""
import os

import pandas as pd
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# `fields=` keeps the response small — we only ask for what we use.
URL = "https://restcountries.com/v3.1/all"
FIELDS = "name,cca2,region,population,latlng"


def fetch() -> list[dict]:
    print(f"Requesting {URL} ...")
    response = requests.get(URL, params={"fields": FIELDS}, timeout=30)
    response.raise_for_status()  # stop here with a clear error if the request failed
    data = response.json()
    print(f"Got {len(data)} countries.")
    return data


def to_dataframe(raw: list[dict]) -> pd.DataFrame:
    rows = []
    for country in raw:
        latlng = country.get("latlng") or [None, None]
        rows.append(
            {
                "name": country.get("name", {}).get("common"),
                "iso2": country.get("cca2"),
                "region": country.get("region"),
                "population": country.get("population"),
                # REST Countries doesn't include GDP or urbanisation —
                # see NOTE below. fetch_tourism.py fills both in later
                # from the World Bank.
                "gdp_per_capita_usd": None,
                "urban_population_pct": None,
                "latitude": latlng[0],
                "longitude": latlng[1],
            }
        )
    return pd.DataFrame(rows)


def main():
    raw = fetch()
    df = to_dataframe(raw)

    out_path = f"{DATA_DIR}/countries.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")
    print(
        "\nNOTE: REST Countries doesn't provide GDP per capita or urban "
        "population %, so both columns are empty for every row. "
        "src/build_features.py fills missing GDP with the median so the "
        "pipeline still runs, but cost_score will be meaningless until you "
        "run fetch_tourism.py next — that script fills both columns in "
        "from the World Bank."
    )


if __name__ == "__main__":
    main()
