"""Explains why a city has (or hasn't got) an airport with flights."""
import os
import sys

import pandas as pd

from fetchAirports import airportColumns, dataDirectory, rawDirectory, routeColumns, haversineKm


def main(names):
    cities = pd.read_csv(f"{dataDirectory}/cities.csv", keep_default_na=False, na_values=[""])
    allAirports = pd.read_csv(os.path.join(rawDirectory, "airports.dat"), header=None, names=airportColumns,
                      na_values=["\\N"], keep_default_na=False)
    routes = pd.read_csv(os.path.join(rawDirectory, "routes.dat"), header=None, names=routeColumns,
                         na_values=["\\N"], keep_default_na=False)
    used = pd.concat([routes["source_iata"], routes["destination_iata"]]).value_counts()
    linked = pd.read_csv(f"{dataDirectory}/airports.csv", keep_default_na=False, na_values=[""])

    for name in names:
        row = cities[cities["name"].str.casefold() == name.casefold()]
        if row.empty:
            print(f"\n{name}: NOT in cities.csv")
            continue
        city = row.iloc[0]
        print(f"\n{city['name']} ({city['iso2']})  lat={city['latitude']:.3f} lon={city['longitude']:.3f}")
        allAirports["km"] = haversineKm(city["latitude"], city["longitude"], allAirports["latitude"].astype(float).to_numpy(),
                                 allAirports["longitude"].astype(float).to_numpy())
        near = allAirports[(allAirports["km"] <= 150) & allAirports["iata_code"].notna()].sort_values("km").head(8)
        for _, airport in near.iterrows():
            mine = linked[(linked["iata_code"] == airport["iata_code"]) & (linked["city_name"] == city["name"])]
            print(f"  {airport['iata_code']}  {airport['km']:6.1f} km  routes={int(used.get(airport['iata_code'], 0)):4d}  "
                  f"type={airport['type']:<8} linked_to_city={'YES' if len(mine) else 'no '}  {airport['airport_name']}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["Madrid"])
