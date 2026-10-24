"""
fetch_airports.py — rebuilds data/airports.csv and data/routes.csv from
the OpenFlights dataset, matched to YOUR cities by DISTANCE.

WHY THIS EXISTS
------------------------------------------------------------------
The shipped airports.csv linked airports to cities by a hand-typed
`city_name`, so it only worked for the ~46 sample cities. Any other city
got airport_count = 0, route_count = 0, connectivity = 0 — the "Ease of
Travel" score was empty for them. Here every real airport with a 3-letter
IATA code is attached to EVERY city in data/cities.csv within MAX_AIRPORT_KM
(so Kansai airport serves both Osaka and Kyoto; nearest-only left the smaller
neighbour with nothing). A city with no airport in range simply
has none (and load_data.py drops it, since ease of travel can't be
scored honestly).

Data: https://github.com/jpatokal/openflights (data/airports.dat and
data/routes.dat) — free, no key. Save both files into data/raw/ to work
offline; if they're not there the script downloads them itself. Only routes whose source AND destination
airports were both matched to a city are kept, since those are the only
ones the app can place.

Run it with:
    python src/fetch_airports.py
"""
import io
import os

import numpy as np
import pandas as pd
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
BASE = "https://raw.githubusercontent.com/jpatokal/openflights/master/data"
MAX_AIRPORT_KM = 100

AIRPORT_COLS = ["airport_id", "airport_name", "city", "country", "iata_code", "icao_code",
                "latitude", "longitude", "altitude", "tz_offset", "dst", "tz", "type", "source"]
ROUTE_COLS = ["airline", "airline_id", "source_iata", "source_id", "destination_iata",
              "destination_id", "codeshare", "stops", "equipment"]


RAW_DIR = os.path.join(DATA_DIR, "raw")


def _download(name: str, columns: list[str]) -> pd.DataFrame:
    """Read data/raw/<name> if you've saved it there (manual download); otherwise fetch it."""
    local = os.path.join(RAW_DIR, name)
    if os.path.exists(local):
        print(f"Reading {local} ...")
        text = open(local, encoding="utf-8").read()
    else:
        print(f"Downloading {name} ...")
        r = requests.get(f"{BASE}/{name}", timeout=120)
        r.raise_for_status()
        text = r.text
    # OpenFlights writes missing values as \N; keep_default_na=False so a code like "NA" survives.
    return pd.read_csv(io.StringIO(text), header=None, names=columns, na_values=["\\N"],
                       keep_default_na=False)


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance; lat/lon may be numpy arrays (vectorised)."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(a))


def match_airports(airports: pd.DataFrame, cities: pd.DataFrame, max_km: float = MAX_AIRPORT_KM) -> pd.DataFrame:
    """Link airports to cities: an airport serves EVERY city within max_km.

    One output row per (airport, city) pair, so the same IATA code can appear
    several times — e.g. Osaka's Kansai (KIX) is a row for Osaka AND for Kyoto.
    The old rule (each airport belongs only to its single nearest city) left
    Kyoto, Cannes, Lucerne, Padua, Siena... with no airport at all, because a
    bigger neighbour always won. Extra columns:
      distance_km : airport to city centre
      is_nearest  : True for the one city this airport is closest to
    """
    airports = airports.dropna(subset=["iata_code", "latitude", "longitude"]).copy()
    airports = airports[airports["iata_code"].str.fullmatch(r"[A-Z]{3}", na=False)]
    if "type" in airports.columns:
        airports = airports[airports["type"].isin(["airport"])]
    airports = airports.drop_duplicates("iata_code")

    city_lat, city_lon = cities["latitude"].to_numpy(), cities["longitude"].to_numpy()
    city_names = cities["name"].to_numpy()
    rows = []
    for _, a in airports.iterrows():
        d = haversine_km(a["latitude"], a["longitude"], city_lat, city_lon)
        nearest = int(np.argmin(d))
        for i in np.flatnonzero(d <= max_km):
            row = a.to_dict()
            row.update(city_name=city_names[i], distance_km=round(float(d[i]), 1), is_nearest=bool(i == nearest))
            rows.append(row)
    out = pd.DataFrame(rows, columns=list(airports.columns) + ["city_name", "distance_km", "is_nearest"])
    return out.reset_index(drop=True)


def main():
    cities = pd.read_csv(f"{DATA_DIR}/cities.csv", keep_default_na=False, na_values=[""])
    airports = match_airports(_download("airports.dat", AIRPORT_COLS), cities)
    routes = _download("routes.dat", ROUTE_COLS)

    keep = set(airports["iata_code"])  # an airport counts once here, however many cities it serves
    routes = routes[routes["source_iata"].isin(keep) & routes["destination_iata"].isin(keep)]
    routes = routes[["source_iata", "destination_iata", "airline", "stops"]].drop_duplicates()

    airports[["iata_code", "icao_code", "airport_name", "city_name", "latitude", "longitude",
              "distance_km", "is_nearest"]].to_csv(
        f"{DATA_DIR}/airports.csv", index=False)
    routes.to_csv(f"{DATA_DIR}/routes.csv", index=False)

    covered = airports["city_name"].nunique()
    shared = int((airports.groupby("iata_code")["city_name"].nunique() > 1).sum())
    print(f"Matched {airports['iata_code'].nunique()} airports to {covered} of {len(cities)} cities "
          f"(every city within {MAX_AIRPORT_KM} km of an airport; {shared} airports serve more than one city); "
          f"kept {len(routes)} routes between them.")
    uncovered = sorted(set(cities["name"]) - set(airports["city_name"]))
    if uncovered:
        print(f"No airport within {MAX_AIRPORT_KM} km: {', '.join(uncovered)}")


if __name__ == "__main__":
    main()
