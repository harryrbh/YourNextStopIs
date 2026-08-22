"""
fetch_tourism.py — replaces data/tourism.csv with real data from the
World Bank, AND fills in the gdp_per_capita_usd column in
data/countries.csv, which fetch_countries.py leaves empty (REST
Countries doesn't provide GDP). No API key needed.

Run it AFTER fetch_countries.py:
    python src/fetch_countries.py
    python src/fetch_tourism.py

World Bank indicators used:
    ST.INT.ARVL     — international tourist arrivals (tourism.csv)
    NY.GDP.PCAP.CD   — GDP per capita, current US$ (countries.csv)
"""
import os

import pandas as pd
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
BASE_URL = "https://api.worldbank.org/v2/country/all/indicator"


def fetch_indicator(code: str) -> pd.DataFrame:
    """World Bank's API always returns a list of two things:
    [metadata, records] — hence data[1] below. `mrnev=1` means "most
    recent non-empty value", so each country appears once, with
    whichever year it last reported.
    """
    url = f"{BASE_URL}/{code}"
    print(f"Requesting {url} ...")
    response = requests.get(url, params={"format": "json", "per_page": "20000", "mrnev": "1"}, timeout=30)
    response.raise_for_status()
    records = response.json()[1] or []

    rows = [
        {
            "iso2": r["country"]["id"],
            "country_name": r["country"]["value"],
            "year": int(r["date"]),
            "value": r["value"],
        }
        for r in records
        if r["value"] is not None
    ]
    print(f"Got {len(rows)} countries with data for {code}.")
    return pd.DataFrame(rows)


def update_gdp_in_countries_csv(gdp: pd.DataFrame):
    countries_path = f"{DATA_DIR}/countries.csv"
    countries = pd.read_csv(countries_path)

    countries = countries.merge(
        gdp[["iso2", "value"]].rename(columns={"value": "gdp_new"}), on="iso2", how="left"
    )
    countries["gdp_per_capita_usd"] = countries["gdp_new"].combine_first(countries["gdp_per_capita_usd"])
    countries = countries.drop(columns=["gdp_new"])

    countries.to_csv(countries_path, index=False)
    print(f"Updated gdp_per_capita_usd for {countries['gdp_per_capita_usd'].notna().sum()} countries in {countries_path}")


def main():
    arrivals = fetch_indicator("ST.INT.ARVL")
    gdp = fetch_indicator("NY.GDP.PCAP.CD")

    tourism = arrivals.rename(columns={"value": "arrivals"})[["iso2", "country_name", "year", "arrivals"]]
    tourism_path = f"{DATA_DIR}/tourism.csv"
    tourism.to_csv(tourism_path, index=False)
    print(f"Saved {len(tourism)} rows to {tourism_path}")

    update_gdp_in_countries_csv(gdp)


if __name__ == "__main__":
    main()
