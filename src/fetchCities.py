import io
import os
import re
import zipfile

import pandas as pd
import requests

from touristCityList import touristCities

dataDirectory = os.path.join(os.path.dirname(__file__), "..", "data")
citiesUrl = "https://download.geonames.org/export/dump/cities15000.zip"

# GeoNames' file has no header row
geonamesColumns = [
    "geonameid", "name", "asciiname", "alternatenames", "latitude", "longitude",
    "feature_class", "feature_code", "country_code", "cc2", "admin1_code",
    "admin2_code", "admin3_code", "admin4_code", "population", "elevation",
    "dem", "timezone", "modification_date",
]


def fetch() -> pd.DataFrame:
    print(f"Downloading {citiesUrl} ...")
    response = requests.get(citiesUrl, timeout=120)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zipArchive:
        inner = zipArchive.namelist()[0]  # cities15000.txt
        with zipArchive.open(inner) as zipEntry:
            # Stop pandas reading Namibia's country code NA as missing
            geonamesCities = pd.read_csv(zipEntry, sep="\t", header=None, names=geonamesColumns, low_memory=False,
                             keep_default_na=False, na_values=[""])
    print(f"Downloaded {len(geonamesCities)} cities.")
    return geonamesCities


def findCity(rawByCountry: dict, name: str, countryCode: str):
    """Best GeoNames row for one curated (name, country), or None."""
    countryRows = rawByCountry.get(countryCode)
    if countryRows is None or countryRows.empty:
        return None
    wanted = name.casefold()
    exact = countryRows[(countryRows["name"].str.casefold() == wanted) | (countryRows["asciiname"].str.casefold() == wanted)]
    if exact.empty:
        pattern = re.compile(rf"(?:^|,){re.escape(name)}(?:,|$)", re.IGNORECASE)
        exact = countryRows[countryRows["alternatenames"].fillna("").apply(lambda alternateNames: bool(pattern.search(alternateNames)))]
    if exact.empty:
        return None
    return exact.sort_values("population", ascending=False).iloc[0]


def toDataFrame(allCities: pd.DataFrame) -> pd.DataFrame:
    allCities = allCities[allCities["feature_class"] == "P"]  # Populated places only
    rawByCountry = {code: countryGroup for code, countryGroup in allCities.groupby("country_code")}

    found, missing = [], []
    for name, countryCode in touristCities:  # Order = the pool's priority order; keep it
        row = findCity(rawByCountry, name, countryCode)
        if row is None:
            missing.append((name, countryCode))
            continue
        found.append({
            "name": name,
            "iso2": countryCode,
            "population": int(row["population"]),
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
        })

    if missing:
        print(f"Note: {len(missing)} curated cities weren't found in GeoNames (below the "
              f"15,000-population floor, or no matching name) and were skipped: {missing}")
    print(f"Matched {len(found)} of {len(touristCities)} curated tourist cities.")
    return pd.DataFrame(found)


def main():
    geonamesCities = toDataFrame(fetch())
    outPath = f"{dataDirectory}/cities.csv"
    geonamesCities.to_csv(outPath, index=False)
    print(f"Saved {len(geonamesCities)} candidate cities to {outPath}")
    print(
        "\nNext: python src/fetchCountries.py, fetchTourism.py, fetchWeather.py, "
        "downloadRawData.py, then fetchAirports.py and buildCulture.py (see dataSources.md). loadDataToDatabase.py then "
        "keeps the first 250 cities that have complete data."
    )


if __name__ == "__main__":
    main()
