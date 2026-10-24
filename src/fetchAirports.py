import io
import os

import numpy as np
import pandas as pd
import requests

dataDirectory = os.path.join(os.path.dirname(__file__), "..", "data")
openFlightsBaseUrl = "https://raw.githubusercontent.com/jpatokal/openflights/master/data"
maximumAirportKm = 100

airportColumns = ["airport_id", "airport_name", "city", "country", "iata_code", "icao_code",
                "latitude", "longitude", "altitude", "tz_offset", "dst", "tz", "type", "source"]
routeColumns = ["airline", "airline_id", "source_iata", "source_id", "destination_iata",
              "destination_id", "codeshare", "stops", "equipment"]


rawDirectory = os.path.join(dataDirectory, "raw")


def _download(name: str, columns: list[str]) -> pd.DataFrame:
    """Read data/raw/<name> if you've saved it there (manual download); otherwise fetch it."""
    local = os.path.join(rawDirectory, name)
    if os.path.exists(local):
        print(f"Reading {local} ...")
        text = open(local, encoding="utf-8").read()
    else:
        print(f"Downloading {name} ...")
        response = requests.get(f"{openFlightsBaseUrl}/{name}", timeout=120)
        response.raise_for_status()
        text = response.text
    return pd.read_csv(io.StringIO(text), header=None, names=columns, na_values=["\\N"],
                       keep_default_na=False)


def haversineKm(latitudeA, longitudeA, latitudeB, longitudeB):
    """Great-circle distance; lat/lon may be numpy arrays (vectorised)."""
    latitudeA, longitudeA, latitudeB, longitudeB = map(np.radians, (latitudeA, longitudeA, latitudeB, longitudeB))
    haversineTerm = np.sin((latitudeB - latitudeA) / 2) ** 2 + np.cos(latitudeA) * np.cos(latitudeB) * np.sin((longitudeB - longitudeA) / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(haversineTerm))


def matchAirports(airports: pd.DataFrame, cities: pd.DataFrame, maximumKm: float = maximumAirportKm) -> pd.DataFrame:
    """Link airports to cities: an airport serves EVERY city within max_km."""
    airports = airports.dropna(subset=["iata_code", "latitude", "longitude"]).copy()
    airports = airports[airports["iata_code"].str.fullmatch(r"[A-Z]{3}", na=False)]
    if "type" in airports.columns:
        airports = airports[airports["type"].isin(["airport"])]
    airports = airports.drop_duplicates("iata_code")

    cityLatitude, cityLongitude = cities["latitude"].to_numpy(), cities["longitude"].to_numpy()
    cityNames = cities["name"].to_numpy()
    matchedRows = []
    for _, airport in airports.iterrows():
        distances = haversineKm(airport["latitude"], airport["longitude"], cityLatitude, cityLongitude)
        nearest = int(np.argmin(distances))
        for cityIndex in np.flatnonzero(distances <= maximumKm):
            row = airport.to_dict()
            row.update(city_name=cityNames[cityIndex], distance_km=round(float(distances[cityIndex]), 1), is_nearest=bool(cityIndex == nearest))
            matchedRows.append(row)
    matchedAirports = pd.DataFrame(matchedRows, columns=list(airports.columns) + ["city_name", "distance_km", "is_nearest"])
    return matchedAirports.reset_index(drop=True)


def main():
    cities = pd.read_csv(f"{dataDirectory}/cities.csv", keep_default_na=False, na_values=[""])
    airports = matchAirports(_download("airports.dat", airportColumns), cities)
    routes = _download("routes.dat", routeColumns)

    keep = set(airports["iata_code"])  # An airport counts once here, however many cities it serves
    routes = routes[routes["source_iata"].isin(keep) & routes["destination_iata"].isin(keep)]
    routes = routes[["source_iata", "destination_iata", "airline", "stops"]].drop_duplicates()

    airports[["iata_code", "icao_code", "airport_name", "city_name", "latitude", "longitude",
              "distance_km", "is_nearest"]].to_csv(
        f"{dataDirectory}/airports.csv", index=False)
    routes.to_csv(f"{dataDirectory}/routes.csv", index=False)

    covered = airports["city_name"].nunique()
    shared = int((airports.groupby("iata_code")["city_name"].nunique() > 1).sum())
    print(f"Matched {airports['iata_code'].nunique()} airports to {covered} of {len(cities)} cities "
          f"(every city within {maximumAirportKm} km of an airport; {shared} airports serve more than one city); "
          f"kept {len(routes)} routes between them.")
    uncovered = sorted(set(cities["name"]) - set(airports["city_name"]))
    if uncovered:
        print(f"No airport within {maximumAirportKm} km: {', '.join(uncovered)}")


if __name__ == "__main__":
    main()
