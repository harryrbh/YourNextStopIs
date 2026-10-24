"""
diagnose_airports.py — explains why a city has (or hasn't got) an airport
with flights. Run after fetch_airports.py:

    python src/diagnose_airports.py Madrid Kyoto Cannes

For each city it prints its coordinates (from data/cities.csv), every
OpenFlights airport within 150 km (data/raw/airports.dat), whether that
airport has any scheduled route in routes.dat, and whether data/airports.csv
links it to the city.
"""
import os
import sys

import pandas as pd

from fetch_airports import AIRPORT_COLS, DATA_DIR, RAW_DIR, ROUTE_COLS, haversine_km


def main(names):
    cities = pd.read_csv(f"{DATA_DIR}/cities.csv", keep_default_na=False, na_values=[""])
    raw = pd.read_csv(os.path.join(RAW_DIR, "airports.dat"), header=None, names=AIRPORT_COLS,
                      na_values=["\\N"], keep_default_na=False)
    routes = pd.read_csv(os.path.join(RAW_DIR, "routes.dat"), header=None, names=ROUTE_COLS,
                         na_values=["\\N"], keep_default_na=False)
    used = pd.concat([routes["source_iata"], routes["destination_iata"]]).value_counts()
    linked = pd.read_csv(f"{DATA_DIR}/airports.csv", keep_default_na=False, na_values=[""])

    for name in names:
        row = cities[cities["name"].str.casefold() == name.casefold()]
        if row.empty:
            print(f"\n{name}: NOT in cities.csv")
            continue
        c = row.iloc[0]
        print(f"\n{c['name']} ({c['iso2']})  lat={c['latitude']:.3f} lon={c['longitude']:.3f}")
        raw["km"] = haversine_km(c["latitude"], c["longitude"], raw["latitude"].astype(float).to_numpy(),
                                 raw["longitude"].astype(float).to_numpy())
        near = raw[(raw["km"] <= 150) & raw["iata_code"].notna()].sort_values("km").head(8)
        for _, a in near.iterrows():
            mine = linked[(linked["iata_code"] == a["iata_code"]) & (linked["city_name"] == c["name"])]
            print(f"  {a['iata_code']}  {a['km']:6.1f} km  routes={int(used.get(a['iata_code'], 0)):4d}  "
                  f"type={a['type']:<8} linked_to_city={'YES' if len(mine) else 'no '}  {a['airport_name']}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["Madrid"])
