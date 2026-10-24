import os

import pandas as pd
import requests

dataDirectory = os.path.join(os.path.dirname(__file__), "..", "data")
baseUrl = "https://api.worldbank.org/v2/country/all/indicator"


def fetchIndicator(code: str, mostRecent: int = 1) -> pd.DataFrame:
    """World Bank's API always returns a list of two things: [metadata, records]."""
    requestUrl = f"{baseUrl}/{code}"
    print(f"Requesting {requestUrl} ...")
    response = requests.get(
        requestUrl, params={"format": "json", "per_page": "20000", "mrnev": str(mostRecent)}, timeout=30
    )
    response.raise_for_status()
    payload = response.json()

    # A healthy response is [metadata, records]
    if not (isinstance(payload, list) and len(payload) == 2 and isinstance(payload[1], list)):
        raise RuntimeError(
            f"World Bank didn't return the [metadata, records] shape we expected "
            f"for indicator '{code}'. Here's exactly what it sent back instead:\n\n"
            f"{payload}\n\nOpen this URL in your browser to see the current, live "
            f"response:\n{response.url}"
        )

    records = payload[1] or []

    countryRows = [
        {
            "iso2": record["country"]["id"],
            "country_name": record["country"]["value"],
            "year": int(record["date"]),
            "value": record["value"],
        }
        for record in records
        if record["value"] is not None
    ]
    print(f"Got {len(countryRows)} rows with data for {code}.")
    return pd.DataFrame(countryRows)


def updateCountriesCsv(gdpRecords: pd.DataFrame, urbanisation: pd.DataFrame):
    countriesPath = f"{dataDirectory}/countries.csv"
    countries = pd.read_csv(countriesPath)

    countries = countries.merge(
        gdpRecords[["iso2", "value"]].rename(columns={"value": "gdp_new"}), on="iso2", how="left"
    )
    countries["gdp_per_capita_usd"] = countries["gdp_new"].combine_first(countries["gdp_per_capita_usd"])
    countries = countries.drop(columns=["gdp_new"])

    countries = countries.merge(
        urbanisation[["iso2", "value"]].rename(columns={"value": "urban_new"}), on="iso2", how="left"
    )
    countries["urban_population_pct"] = countries["urban_new"].combine_first(countries["urban_population_pct"])
    countries = countries.drop(columns=["urban_new"])

    countries.to_csv(countriesPath, index=False)
    print(
        f"Updated gdp_per_capita_usd for {countries['gdp_per_capita_usd'].notna().sum()} countries, "
        f"urban_population_pct for {countries['urban_population_pct'].notna().sum()} countries, "
        f"in {countriesPath}"
    )


def main():
    arrivals = fetchIndicator("ST.INT.ARVL")
    gdpRecords = fetchIndicator("NY.GDP.PCAP.CD")
    urbanisation = fetchIndicator("SP.URB.TOTL.IN.ZS")

    tourism = arrivals.rename(columns={"value": "arrivals"})[["iso2", "country_name", "year", "arrivals"]]
    tourismPath = f"{dataDirectory}/tourism.csv"
    tourism.to_csv(tourismPath, index=False)
    print(f"Saved {len(tourism)} rows to {tourismPath}")

    updateCountriesCsv(gdpRecords, urbanisation)


def fetchTwoYearsSketch():
    """Not called by main()."""
    twoYears = fetchIndicator("ST.INT.ARVL", mostRecent=2)
    pivoted = twoYears.sort_values("year").pivot_table(
        index=["iso2", "country_name"], columns="year", values="value"
    )
    print(pivoted.head())


if __name__ == "__main__":
    main()
