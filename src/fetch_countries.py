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
                # REST Countries doesn't include GDP — see NOTE below.
                "gdp_per_capita_usd": None,
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
        "\nNOTE: REST Countries doesn't provide GDP per capita, so "
        "gdp_per_capita_usd is empty for every row. src/build_features.py "
        "handles missing values by filling them with the median, so the "
        "pipeline still runs — but cost_score will be meaningless until "
        "you fill this column in. See fetch_tourism.py's docstring for "
        "where World Bank GDP data would plug in instead."
    )


if __name__ == "__main__":
    main()
