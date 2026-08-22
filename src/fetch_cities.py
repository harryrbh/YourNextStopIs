"""
fetch_cities.py — replaces data/cities.csv with real data from
GeoNames. No account/API key needed for this bulk-download approach.

GeoNames publishes a free, no-signup file containing every city in
the world with population >= 15,000. We download it once, then filter
it down to something a student laptop can comfortably work with.

Run it with:
    python src/fetch_cities.py

This OVERWRITES data/cities.csv.
"""
import io
import os
import zipfile

import pandas as pd
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
URL = "https://download.geonames.org/export/dump/cities15000.zip"

# GeoNames' file has no header row — these column names come from
# https://download.geonames.org/export/dump/readme.txt
COLUMNS = [
    "geonameid", "name", "asciiname", "alternatenames", "latitude", "longitude",
    "feature_class", "feature_code", "country_code", "cc2", "admin1_code",
    "admin2_code", "admin3_code", "admin4_code", "population", "elevation",
    "dem", "timezone", "modification_date",
]

# Keeping every city over 15,000 people would be ~25,000 rows — plenty
# for a real project, but slow to work with while you're learning.
# We keep the biggest MAX_CITIES instead. Raise this number once
# everything else works and you want more coverage.
MAX_CITIES = 200


def fetch() -> pd.DataFrame:
    print(f"Downloading {URL} ...")
    response = requests.get(URL, timeout=60)
    response.raise_for_status()

    # The file we downloaded is a .zip containing one .txt file — we
    # never write the .zip to disk, just read it directly from memory.
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        inner_filename = zf.namelist()[0]  # cities15000.txt
        with zf.open(inner_filename) as f:
            df = pd.read_csv(f, sep="\t", header=None, names=COLUMNS, low_memory=False)

    print(f"Downloaded {len(df)} cities.")
    return df


def to_dataframe(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.sort_values("population", ascending=False).head(MAX_CITIES)
    return df.rename(columns={"country_code": "iso2"})[
        ["name", "iso2", "population", "latitude", "longitude"]
    ].reset_index(drop=True)


def main():
    raw = fetch()
    df = to_dataframe(raw)

    out_path = f"{DATA_DIR}/cities.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved the {len(df)} biggest cities to {out_path}")
    print(
        "\nNOTE: this drops the culture data (heritage sites/attractions) "
        "our sample cities.csv had, because GeoNames doesn't provide it — "
        "load_data.py already handles that gracefully (missing values "
        "become 0), but every city's culture_score will be identical "
        "until you add a real source. See README.md's 'Data note' section."
    )


if __name__ == "__main__":
    main()
