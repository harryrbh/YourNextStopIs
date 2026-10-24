"""Replaces data/countries.csv with real country data."""
import os

import pandas as pd
import requests

dataDirectory = os.path.join(os.path.dirname(__file__), "..", "data")

# `fields=` keeps the response small
countriesUrl = "https://countries.dev/countries"
countryFields = "name,alpha2Code,region,population,latlng"


def fetch() -> list[dict]:
    print(f"Requesting {countriesUrl} ...")
    response = requests.get(countriesUrl, params={"fields": countryFields}, timeout=30)
    response.raise_for_status()  # Stop here with a clear error if the request failed
    countryData = response.json()

    # The API should return a JSON *list*, one object per country
    if not isinstance(countryData, list):
        raise RuntimeError(
            "The countries API didn't return the country list we expected. "
            f"Here's exactly what it sent back instead:\n\n{countryData}\n\n"
            "This usually means either a temporary problem with the API "
            "itself, or that its request format has changed since this "
            "script was written. Try opening this URL in your browser to "
            "see the current, live response:\n"
            f"{response.url}"
        )

    print(f"Got {len(countryData)} countries.")
    return countryData


def toDataFrame(countryRecords: list[dict]) -> pd.DataFrame:
    rows = []
    for country in countryRecords:
        latlng = country.get("latlng") or [None, None]
        rows.append(
            {
                "name": country.get("name"),
                "iso2": country.get("alpha2Code"),
                "region": country.get("region"),
                "population": country.get("population"),
                # Neither this API nor REST Countries includes GDP or urbanisation
                "gdp_per_capita_usd": None,
                "urban_population_pct": None,
                "latitude": latlng[0] if len(latlng) > 0 else None,
                "longitude": latlng[1] if len(latlng) > 1 else None,
            }
        )
    return pd.DataFrame(rows)


def main():
    countryRecords = fetch()
    countriesTable = toDataFrame(countryRecords)

    outPath = f"{dataDirectory}/countries.csv"
    countriesTable.to_csv(outPath, index=False)
    print(f"Saved {len(countriesTable)} rows to {outPath}")
    print(
        "\nNOTE: this API doesn't provide GDP per capita or urban "
        "population %, so both columns are empty for every row. "
        "src/buildCityFeatures.py fills missing GDP with the median so the "
        "pipeline still runs, but cost_score will be meaningless until you "
        "run fetchTourism.py next — that script fills both columns in "
        "from the World Bank."
    )


if __name__ == "__main__":
    main()
