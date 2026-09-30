"""
build_culture.py — builds data/culture.csv for EVERY city in data/cities.csv
from two downloaded data extracts (no live API, so nothing to rate-limit).

THE TWO EXTRACTS YOU NEED (put them in data/raw/ — see DATA_SOURCES.md)
------------------------------------------------------------------
1. GeoNames per-country files:  data/raw/geonames/<ISO2>.txt
     e.g. FR.zip -> FR.txt.  Download from
     https://download.geonames.org/export/dump/  (one zip per country;
     `python src/download_raw_data.py` fetches the ones you need).
   Every row is a named place with a FEATURE CODE. The codes that mean
   "a thing tourists visit" are listed in SIGHT_FEATURE_CODES below
   (museum, castle, palace, monument, historic site, ruin, church,
   temple, mosque, theatre, garden, zoo, ...). Meaning of every code:
   https://download.geonames.org/export/dump/featureCodes_en.txt

2. UNESCO World Heritage List:  data/raw/unesco_whc.xml  (or .csv/.xlsx)
     https://whc.unesco.org/en/list/  ->  "Export"/download (XML, XLS).
   It has each site's name and latitude/longitude. We count how many
   sites lie within HERITAGE_RADIUS_KM of each city.

WHAT IT PRODUCES
------------------------------------------------------------------
  heritage_site_count : UNESCO sites within HERITAGE_RADIUS_KM (25 km)
  attraction_count    : GeoNames sight features within ATTRACTION_RADIUS_KM (10 km)
  attraction_1..3     : the three best-known of those.

"Best-known" = the sights with the MOST ALTERNATE NAMES in GeoNames. A
famous place is written in many languages/spellings (Eiffel Tower, Tour
Eiffel, Torre Eiffel, ...), an obscure chapel isn't — so alternate-name
count is a decent, fully offline fame proxy. It is a proxy, not a ranking
by visitors: check the top 3 for cities you know.

Counts reflect how densely GeoNames maps a country (thorough in Europe,
patchier elsewhere), so read them as a RELATIVE measure. A city with zero
sights is written as 0 and dropped by load_data.py rather than shown blank.

Run it with:
    python src/build_culture.py
"""
import os
import re
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from fetch_airports import haversine_km  # same great-circle helper used for airports

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
GEONAMES_DIR = os.path.join(RAW_DIR, "geonames")

HERITAGE_RADIUS_KM = 25
ATTRACTION_RADIUS_KM = 10
COLUMNS = ["city_name", "heritage_site_count", "attraction_count", "attraction_1", "attraction_2", "attraction_3"]

# GeoNames feature codes (feature class S = spot, building, farm; L.PRK = park).
# Definitions: featureCodes_en.txt. Deliberately NOT included: hotels, shops,
# stadiums, stations — they're places, not sights.
SIGHT_FEATURE_CODES = {
    "MUS",   # museum
    "CSTL",  # castle
    "PAL",   # palace
    "MNMT",  # monument
    "HSTS",  # historical site
    "RUIN",  # ruin(s)
    "ANS",   # ancient site
    "ARCH",  # arch
    "AMTH",  # amphitheater
    "CH",    # church
    "CTHRL", # cathedral
    "MSQE",  # mosque
    "TMPL",  # temple
    "SHRN",  # shrine
    "MSTY",  # monastery
    "SYG",   # synagogue
    "THTR",  # theater
    "OPRA",  # opera house
    "GDN",   # garden(s)
    "ZOO",   # zoo
    "TOWR",  # tower
    "LIBR",  # library
    "PRK",   # park (feature class L)
}

# GeoNames' tab-separated column order (readme.txt in the same folder as the downloads).
GEONAMES_COLS = [
    "geonameid", "name", "asciiname", "alternatenames", "latitude", "longitude",
    "feature_class", "feature_code", "country_code", "cc2", "admin1_code",
    "admin2_code", "admin3_code", "admin4_code", "population", "elevation",
    "dem", "timezone", "modification_date",
]


# ---------------------------------------------------------------- UNESCO ---

def _find_col(columns, candidates):
    lowered = {c.lower().strip(): c for c in columns}
    for cand in candidates:
        if cand in lowered:
            return lowered[cand]
    return None


def load_unesco(path: str) -> pd.DataFrame:
    """Read the UNESCO list (.xml, .csv, .xls/.xlsx) into columns site, latitude, longitude.
    Column names are matched flexibly because UNESCO's export layout has changed over time."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xml":
        rows = [{child.tag.lower(): (child.text or "").strip() for child in row}
                for row in ET.parse(path).getroot().iter("row")]
        df = pd.DataFrame(rows)
    elif ext in (".xls", ".xlsx"):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)

    site = _find_col(df.columns, ["site", "name", "name_en", "site_name", "title"])
    lat = _find_col(df.columns, ["latitude", "lat", "y"])
    lon = _find_col(df.columns, ["longitude", "lon", "long", "lng", "x"])
    if not (site and lat and lon):
        raise ValueError(
            f"Couldn't find site/latitude/longitude columns in {path}. Columns present: "
            f"{list(df.columns)}. Rename them, or add the right names to load_unesco()."
        )
    out = pd.DataFrame({
        "site": df[site].astype(str),
        "latitude": pd.to_numeric(df[lat], errors="coerce"),
        "longitude": pd.to_numeric(df[lon], errors="coerce"),
    })
    # Some sites (serial/transboundary) have no single coordinate: they can't be placed near a city.
    return out.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)


def count_heritage(cities: pd.DataFrame, unesco: pd.DataFrame, radius_km: float = HERITAGE_RADIUS_KM) -> pd.Series:
    """UNESCO sites within radius_km of each city, indexed by city name."""
    lat, lon = unesco["latitude"].to_numpy(), unesco["longitude"].to_numpy()
    counts = {}
    for _, c in cities.iterrows():
        d = haversine_km(c["latitude"], c["longitude"], lat, lon)
        counts[c["name"]] = int((d <= radius_km).sum())
    return pd.Series(counts)


# -------------------------------------------------------------- GeoNames ---

def load_geonames_sights(path: str) -> pd.DataFrame:
    """Read one GeoNames country file, keeping only sight-type features."""
    df = pd.read_csv(path, sep="\t", header=None, names=GEONAMES_COLS, usecols=range(len(GEONAMES_COLS)),
                     dtype=str, keep_default_na=False, quoting=3)  # quoting=3: names contain stray quotes
    is_park = (df["feature_class"] == "L") & (df["feature_code"] == "PRK")
    is_spot = (df["feature_class"] == "S") & df["feature_code"].isin(SIGHT_FEATURE_CODES - {"PRK"})
    df = df[is_park | is_spot].copy()
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["fame"] = df["alternatenames"].apply(lambda s: len([a for a in s.split(",") if a]))
    return df.dropna(subset=["latitude", "longitude"])[["name", "asciiname", "latitude", "longitude", "fame"]]


_GENERIC = re.compile(r"^(church|parish church|chapel|park|garden|gardens|museum|monument|tower)$", re.IGNORECASE)


def top_sights_for_city(city: pd.Series, sights: pd.DataFrame, radius_km: float = ATTRACTION_RADIUS_KM):
    """(count, up to three best-known names) of sights within radius_km of the city."""
    d = haversine_km(city["latitude"], city["longitude"], sights["latitude"].to_numpy(), sights["longitude"].to_numpy())
    near = sights[d <= radius_km]
    if near.empty:
        return 0, []
    near = near.assign(_dist=d[d <= radius_km]).sort_values(["fame", "_dist"], ascending=[False, True])
    names = []
    for n in near["name"]:
        n = n.strip()
        if n and not _GENERIC.match(n) and n not in names:
            names.append(n)
        if len(names) == 3:
            break
    return len(near), names


def build_culture(cities: pd.DataFrame, unesco: pd.DataFrame, sights_by_country: dict) -> pd.DataFrame:
    heritage = count_heritage(cities, unesco)
    rows = []
    for _, city in cities.iterrows():
        sights = sights_by_country.get(city["iso2"])
        count, names = (0, []) if sights is None else top_sights_for_city(city, sights)
        names += [""] * (3 - len(names))
        rows.append({
            "city_name": city["name"],
            "heritage_site_count": int(heritage[city["name"]]),
            "attraction_count": count,
            "attraction_1": names[0], "attraction_2": names[1], "attraction_3": names[2],
        })
    return pd.DataFrame(rows, columns=COLUMNS)


def check_feature_codes(path: str) -> None:
    """If featureCodes_en.txt is present, warn about any code we use that GeoNames doesn't list."""
    if not os.path.exists(path):
        return
    known = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            code = line.split("\t")[0].strip()  # like "S.MUS"
            if "." in code:
                known.add(code.split(".", 1)[1])
    unknown = sorted(c for c in SIGHT_FEATURE_CODES if c not in known)
    if unknown:
        print(f"  NOTE: these codes aren't in featureCodes_en.txt and will match nothing: {unknown}")


def find_unesco_file() -> str:
    for ext in (".xml", ".csv", ".xlsx", ".xls"):
        p = os.path.join(RAW_DIR, f"unesco_whc{ext}")
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        "No UNESCO file found. Download the World Heritage List from https://whc.unesco.org/en/list/ "
        "and save it as data/raw/unesco_whc.xml (or .csv/.xlsx). See DATA_SOURCES.md."
    )


def main():
    cities = pd.read_csv(f"{DATA_DIR}/cities.csv", keep_default_na=False, na_values=[""])
    check_feature_codes(os.path.join(RAW_DIR, "featureCodes_en.txt"))
    unesco = load_unesco(find_unesco_file())
    print(f"Loaded {len(unesco)} UNESCO sites with coordinates.")

    sights_by_country = {}
    for iso2 in sorted(cities["iso2"].unique()):
        path = os.path.join(GEONAMES_DIR, f"{iso2}.txt")
        if not os.path.exists(path):
            print(f"  MISSING {path} — cities in {iso2} will have no attractions "
                  f"(run: python src/download_raw_data.py)")
            continue
        sights_by_country[iso2] = load_geonames_sights(path)
        print(f"  {iso2}: {len(sights_by_country[iso2])} sight features")

    culture = build_culture(cities, unesco, sights_by_country)
    culture.to_csv(f"{DATA_DIR}/culture.csv", index=False)
    with_sights = int((culture["attraction_count"] > 0).sum())
    print(f"\nSaved {len(culture)} cities to data/culture.csv ({with_sights} have at least one sight).")
    print("Spot-check a few you know:\n", culture.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
