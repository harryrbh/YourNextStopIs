"""
fetch_tourism.py — replaces data/tourism.csv with real data from the
World Bank, AND fills in the gdp_per_capita_usd and
urban_population_pct columns in data/countries.csv, which
fetch_countries.py leaves empty (REST Countries doesn't provide
either). No API key needed.

Run it AFTER fetch_countries.py:
    python src/fetch_countries.py
    python src/fetch_tourism.py

World Bank indicators used:
    ST.INT.ARVL        — international tourist arrivals (tourism.csv)
    NY.GDP.PCAP.CD      — GDP per capita, current US$ (countries.csv)
    SP.URB.TOTL.IN.ZS    — urban population, % of total (countries.csv)

A known gap: this only fetches ONE year per indicator (`mrnev=1`, the
most recent value each country reported), so tourism.csv won't have
`tourism_growth_pct` or let build_features.py calculate
previous_arrivals the way it can with the sample data. To get real
growth figures, request two years instead — see the fetch_two_years()
sketch at the bottom of this file for how you'd extend it.
"""
import os

import pandas as pd
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
BASE_URL = "https://api.worldbank.org/v2/country/all/indicator"


def fetch_indicator(code: str, most_recent: int = 1) -> pd.DataFrame:
    """World Bank's API always returns a list of two things:
    [metadata, records] — hence data[1] below. `mrnev=N` means "the N
    most recent non-empty values", so with most_recent=1 each country
    appears once, with whichever year it last reported.
    """
    url = f"{BASE_URL}/{code}"
    print(f"Requesting {url} ...")
    response = requests.get(
        url, params={"format": "json", "per_page": "20000", "mrnev": str(most_recent)}, timeout=30
    )
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
    print(f"Got {len(rows)} rows with data for {code}.")
    return pd.DataFrame(rows)


def update_countries_csv(gdp: pd.DataFrame, urbanisation: pd.DataFrame):
    countries_path = f"{DATA_DIR}/countries.csv"
    countries = pd.read_csv(countries_path)

    countries = countries.merge(
        gdp[["iso2", "value"]].rename(columns={"value": "gdp_new"}), on="iso2", how="left"
    )
    countries["gdp_per_capita_usd"] = countries["gdp_new"].combine_first(countries["gdp_per_capita_usd"])
    countries = countries.drop(columns=["gdp_new"])

    countries = countries.merge(
        urbanisation[["iso2", "value"]].rename(columns={"value": "urban_new"}), on="iso2", how="left"
    )
    countries["urban_population_pct"] = countries["urban_new"].combine_first(countries["urban_population_pct"])
    countries = countries.drop(columns=["urban_new"])

    countries.to_csv(countries_path, index=False)
    print(
        f"Updated gdp_per_capita_usd for {countries['gdp_per_capita_usd'].notna().sum()} countries, "
        f"urban_population_pct for {countries['urban_population_pct'].notna().sum()} countries, "
        f"in {countries_path}"
    )


def main():
    arrivals = fetch_indicator("ST.INT.ARVL")
    gdp = fetch_indicator("NY.GDP.PCAP.CD")
    urbanisation = fetch_indicator("SP.URB.TOTL.IN.ZS")

    tourism = arrivals.rename(columns={"value": "arrivals"})[["iso2", "country_name", "year", "arrivals"]]
    tourism_path = f"{DATA_DIR}/tourism.csv"
    tourism.to_csv(tourism_path, index=False)
    print(f"Saved {len(tourism)} rows to {tourism_path}")

    update_countries_csv(gdp, urbanisation)


def fetch_two_years_sketch():
    """Not called by main() — a starting point if you want real
    year-on-year tourism growth instead of the single-year figure
    above. `mrnev=2` asks for the two most recent values per country;
    from there you'd pivot so each country has one row with both
    years' arrivals as separate columns, then compute:
        tourism_growth_pct = (this_year - last_year) / last_year * 100
    exactly like the sample data's growth figure, but from two real,
    independently reported numbers instead of one number backed out
    algebraically. See src/regression.py's docstring for why that
    distinction matters.
    """
    two_years = fetch_indicator("ST.INT.ARVL", most_recent=2)
    pivoted = two_years.sort_values("year").pivot_table(
        index=["iso2", "country_name"], columns="year", values="value"
    )
    print(pivoted.head())


if __name__ == "__main__":
    main()
