"""
fetch_cities.py — replaces data/cities.csv with real data from
GeoNames. No account/API key needed for this bulk-download approach.

GeoNames publishes a free, no-signup file containing every city in
the world with population >= 15,000. We download it once, then pick
a mix of cities from it — see "HOW CITIES ARE CHOSEN" below.

HOW CITIES ARE CHOSEN — AND WHY, HONESTLY
------------------------------------------------------------------
Sorting by population alone (what an earlier version of this script
did) fills the list with the absolute biggest cities in the world —
Shanghai, Lagos, Kinshasa, Dhaka — most of which are huge
administrative/industrial centres, not the kind of place a "city
break" app is about. GeoNames has no "how popular is this with
tourists" field at all, so there's no dataset to sort by instead.

Rather than pretend population size IS a tourism signal, this script
is upfront that it isn't, and uses two different, disclosed rules:

1. TOURIST_CITIES below is a hand-picked list of destinations broadly
   known for tourism, written by whoever set up this project — a
   genuine editorial judgement call, not a measured statistic. Every
   one of these is matched against the real GeoNames data (by name
   and country) so its population/coordinates are still real, live
   data — only the *selection* is curated, nothing about any
   individual city's facts is invented.
2. The remaining slots (up to MAX_CITIES) are filled from GeoNames by
   population, but only within a population BAND
   (MIN_FILLER_POPULATION to MAX_FILLER_POPULATION) — this is what
   stops the biggest megacities crowding out everything else, without
   pretending a mid-sized-city filter is a tourism measurement either.

Both rules are knobs, not ground truth — change TOURIST_CITIES or the
population band to suit what you're building. See API_GUIDE.md for
more on this trade-off, and for how you'd swap in a real
tourism-popularity signal (e.g. Wikipedia pageviews) instead.

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

MAX_CITIES = 200

# Hand-picked (name, ISO 3166-1 alpha-2 country code) pairs — see the
# module docstring. The country code disambiguates names that exist
# in more than one country (there's a "Valencia" in both Spain and
# Venezuela, a "Cambridge" in both the UK and the US, and so on).
# These are matched against real GeoNames rows below; nothing here is
# a fabricated population or coordinate.
TOURIST_CITIES = [
    # Europe
    ("Bruges", "BE"), ("Ghent", "BE"), ("Antwerp", "BE"),
    ("Salzburg", "AT"), ("Innsbruck", "AT"), ("Graz", "AT"),
    ("Ljubljana", "SI"),
    ("Split", "HR"), ("Zadar", "HR"), ("Dubrovnik", "HR"),
    ("Kotor", "ME"),
    ("Sarajevo", "BA"), ("Mostar", "BA"),
    ("Tallinn", "EE"), ("Riga", "LV"), ("Vilnius", "LT"),
    ("Gdansk", "PL"), ("Wroclaw", "PL"), ("Krakow", "PL"),
    ("San Sebastian", "ES"), ("Granada", "ES"), ("Cordoba", "ES"),
    ("Toledo", "ES"), ("Bilbao", "ES"), ("Valencia", "ES"), ("Seville", "ES"),
    ("Siena", "IT"), ("Verona", "IT"), ("Bologna", "IT"), ("Palermo", "IT"),
    ("Bergen", "NO"), ("Reykjavik", "IS"),
    ("Porto", "PT"), ("Coimbra", "PT"),
    ("York", "GB"), ("Bath", "GB"), ("Edinburgh", "GB"),
    ("Galway", "IE"), ("Cork", "IE"),
    # Asia
    ("Kyoto", "JP"), ("Nara", "JP"), ("Kanazawa", "JP"),
    ("Chiang Mai", "TH"),
    ("Luang Prabang", "LA"),
    ("Hoi An", "VN"), ("Hue", "VN"),
    ("Siem Reap", "KH"),
    ("Kandy", "LK"), ("Galle", "LK"),
    ("Udaipur", "IN"), ("Jaipur", "IN"), ("Jaisalmer", "IN"), ("Varanasi", "IN"),
    ("Gyeongju", "KR"), ("Busan", "KR"), ("Jeju-si", "KR"),
    # Middle East / Africa
    ("Wadi Musa", "JO"), ("Luxor", "EG"), ("Aswan", "EG"),
    ("Essaouira", "MA"), ("Fes", "MA"), ("Chefchaouen", "MA"), ("Marrakesh", "MA"),
    ("Zanzibar", "TZ"), ("Stellenbosch", "ZA"), ("Cape Town", "ZA"),
    # Americas
    ("Antigua Guatemala", "GT"), ("Cartagena", "CO"),
    ("Valparaiso", "CL"), ("Salta", "AR"), ("Mendoza", "AR"),
    ("San Carlos de Bariloche", "AR"), ("Cusco", "PE"),
    ("Charleston", "US"), ("Savannah", "US"), ("Santa Fe", "US"),
    ("Quebec City", "CA"), ("Victoria", "CA"),
    # Oceania
    ("Queenstown", "NZ"), ("Rotorua", "NZ"), ("Cairns", "AU"), ("Hobart", "AU"),
]

# Filler slots (everything not in TOURIST_CITIES) are chosen from
# GeoNames by population, but only within this band — this is what
# keeps the biggest megacities from crowding out everything else.
# Change these to change the flavour of the "filler" portion; they
# have no effect on TOURIST_CITIES, which is included regardless of
# size.
MIN_FILLER_POPULATION = 20_000
MAX_FILLER_POPULATION = 3_000_000


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


def match_tourist_cities(raw: pd.DataFrame) -> pd.DataFrame:
    """Find each (name, country) pair from TOURIST_CITIES in the real
    GeoNames data. A name can appear more than once within a country
    (a big city and an obscure suburb can share a name) — we keep the
    most populous match, since that's almost always the real place
    being referred to.
    """
    wanted = pd.DataFrame(TOURIST_CITIES, columns=["name", "iso2"])
    matches = raw.merge(
        wanted, left_on=["name", "country_code"], right_on=["name", "iso2"], how="inner"
    )
    matches = matches.drop(columns=["iso2"])  # duplicate of country_code from the merge — keep one
    matches = matches.sort_values("population", ascending=False).drop_duplicates(subset=["name", "country_code"])
    found = set(zip(matches["name"], matches["country_code"]))
    missing = [pair for pair in TOURIST_CITIES if pair not in found]
    if missing:
        print(
            f"Note: {len(missing)} curated cities weren't found in this GeoNames "
            f"download (below the 15,000-population floor, or the name doesn't "
            f"match exactly) and were skipped: {missing}"
        )
    return matches


def pick_filler_cities(raw: pd.DataFrame, already_chosen: pd.DataFrame, n: int) -> pd.DataFrame:
    """The rest of the list: real cities from a population band, most
    populous first, excluding anything already picked via
    TOURIST_CITIES."""
    chosen_ids = set(already_chosen["geonameid"])
    band = raw[
        raw["population"].between(MIN_FILLER_POPULATION, MAX_FILLER_POPULATION)
        & ~raw["geonameid"].isin(chosen_ids)
    ]
    return band.sort_values("population", ascending=False).head(n)


def to_dataframe(raw: pd.DataFrame) -> pd.DataFrame:
    tourist_matches = match_tourist_cities(raw)
    filler_needed = max(0, MAX_CITIES - len(tourist_matches))
    filler = pick_filler_cities(raw, tourist_matches, filler_needed)

    combined = pd.concat([tourist_matches, filler], ignore_index=True)
    print(
        f"Selected {len(tourist_matches)} curated tourist cities and "
        f"{len(filler)} filler cities (population {MIN_FILLER_POPULATION:,}-"
        f"{MAX_FILLER_POPULATION:,}), for {len(combined)} total."
    )
    return combined.rename(columns={"country_code": "iso2"})[
        ["name", "iso2", "population", "latitude", "longitude"]
    ].reset_index(drop=True)


def main():
    raw = fetch()
    df = to_dataframe(raw)

    out_path = f"{DATA_DIR}/cities.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} cities to {out_path}")
    print(
        "\nNOTE: this drops the culture data (heritage sites/attractions) "
        "our sample cities.csv had, because GeoNames doesn't provide it — "
        "load_data.py already handles that gracefully (missing values "
        "become 0), but every city's culture_score will be identical "
        "until you add a real source. See README.md's 'Data note' section."
    )


if __name__ == "__main__":
    main()
