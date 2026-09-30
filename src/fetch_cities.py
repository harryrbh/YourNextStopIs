"""
fetch_cities.py — replaces data/cities.csv with the candidate tourist
cities from src/tourist_cities.py, matched against real GeoNames data.
No account/API key needed.

WHAT CHANGED, AND WHY
------------------------------------------------------------------
Earlier versions topped the list up with "filler" cities chosen purely by
population. GeoNames has no tourism signal, so many fillers were
industrial/administrative towns with no sights at all — they came back
with empty culture data and dragged the scores down. There is no filler
any more: every city comes from the curated pool in tourist_cities.py.

Matching also used to compare only GeoNames' `name` column, which holds
local spellings ("Kraków", "Córdoba", "Gdańsk"), so those curated cities
were silently skipped. Now each entry is matched against name, asciiname
and alternatenames (exact names first, alternates as a fallback), always
within the right country, taking the most populous match.

Cities under GeoNames' 15,000-person floor can't be found and are
reported. The pool is larger than the number the app finally shows
(TARGET_CITY_COUNT), so a few misses — or cities later dropped for
incomplete data by select_cities.py — don't leave the app short.

Run it with:
    python src/fetch_cities.py

This OVERWRITES data/cities.csv.
"""
import io
import os
import re
import zipfile

import pandas as pd
import requests

from tourist_cities import TOURIST_CITIES

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
URL = "https://download.geonames.org/export/dump/cities15000.zip"

# GeoNames' file has no header row — column names from
# https://download.geonames.org/export/dump/readme.txt
COLUMNS = [
    "geonameid", "name", "asciiname", "alternatenames", "latitude", "longitude",
    "feature_class", "feature_code", "country_code", "cc2", "admin1_code",
    "admin2_code", "admin3_code", "admin4_code", "population", "elevation",
    "dem", "timezone", "modification_date",
]


def fetch() -> pd.DataFrame:
    print(f"Downloading {URL} ...")
    response = requests.get(URL, timeout=120)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        inner = zf.namelist()[0]  # cities15000.txt
        with zf.open(inner) as f:
            # keep_default_na=False: otherwise Namibia's country code "NA" is read as "missing"
            df = pd.read_csv(f, sep="\t", header=None, names=COLUMNS, low_memory=False,
                             keep_default_na=False, na_values=[""])
    print(f"Downloaded {len(df)} cities.")
    return df


def find_city(raw_by_country: dict, name: str, iso2: str):
    """Best GeoNames row for one curated (name, country), or None."""
    rows = raw_by_country.get(iso2)
    if rows is None or rows.empty:
        return None
    wanted = name.casefold()
    exact = rows[(rows["name"].str.casefold() == wanted) | (rows["asciiname"].str.casefold() == wanted)]
    if exact.empty:
        pattern = re.compile(rf"(?:^|,){re.escape(name)}(?:,|$)", re.IGNORECASE)
        exact = rows[rows["alternatenames"].fillna("").apply(lambda s: bool(pattern.search(s)))]
    if exact.empty:
        return None
    return exact.sort_values("population", ascending=False).iloc[0]


def to_dataframe(raw: pd.DataFrame) -> pd.DataFrame:
    raw = raw[raw["feature_class"] == "P"]  # populated places only
    raw_by_country = {code: grp for code, grp in raw.groupby("country_code")}

    found, missing = [], []
    for name, iso2 in TOURIST_CITIES:  # order = the pool's priority order; keep it
        row = find_city(raw_by_country, name, iso2)
        if row is None:
            missing.append((name, iso2))
            continue
        found.append({
            "name": name,  # the curated name: unique, and what the other CSVs are keyed on
            "iso2": iso2,
            "population": int(row["population"]),
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
        })

    if missing:
        print(f"Note: {len(missing)} curated cities weren't found in GeoNames (below the "
              f"15,000-population floor, or no matching name) and were skipped: {missing}")
    print(f"Matched {len(found)} of {len(TOURIST_CITIES)} curated tourist cities.")
    return pd.DataFrame(found)


def main():
    df = to_dataframe(fetch())
    out_path = f"{DATA_DIR}/cities.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} candidate cities to {out_path}")
    print(
        "\nNext: python src/fetch_countries.py, fetch_tourism.py, fetch_weather.py, "
        "download_raw_data.py, then fetch_airports.py and build_culture.py (see DATA_SOURCES.md). load_data.py then "
        "keeps the first 250 cities that have complete data."
    )


if __name__ == "__main__":
    main()
