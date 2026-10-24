"""Reads the CSV files in data/ and loads them into the SQLite database."""
import os

import pandas as pd

from database import getEngine
from selectCompleteCities import targetCityCount, selectCities

# Resolve data/ relative to this file
dataDirectory = os.path.join(os.path.dirname(__file__), "..", "data")


def cleanCountries(dataFrame: pd.DataFrame) -> pd.DataFrame:
    dataFrame = dataFrame.dropna(subset=["name", "iso2", "latitude", "longitude"])
    dataFrame = dataFrame[dataFrame["latitude"].between(-90, 90) & dataFrame["longitude"].between(-180, 180)]
    dataFrame = dataFrame.drop_duplicates(subset=["iso2"])
    return dataFrame[
        ["iso2", "name", "region", "population", "gdp_per_capita_usd", "urban_population_pct", "latitude", "longitude"]
    ].rename(columns={"gdp_per_capita_usd": "gdp_per_capita"})


def cleanCities(dataFrame: pd.DataFrame, culture: pd.DataFrame) -> pd.DataFrame:
    dataFrame = dataFrame.dropna(subset=["name", "latitude", "longitude"])
    dataFrame = dataFrame[dataFrame["latitude"].between(-90, 90) & dataFrame["longitude"].between(-180, 180)]
    dataFrame = dataFrame.merge(culture, left_on="name", right_on="city_name", how="left")
    dataFrame["heritage_site_count"] = dataFrame["heritage_site_count"].fillna(0)
    dataFrame["attraction_count"] = dataFrame["attraction_count"].fillna(0)
    for attractionColumn in ["attraction_1", "attraction_2", "attraction_3"]:
        dataFrame[attractionColumn] = dataFrame[attractionColumn].fillna("")
    return dataFrame


def main():
    engine = getEngine()

    print("Reading CSV files...")
    # Stop pandas reading Namibia's country code NA as missing
    csvOptions = dict(keep_default_na=False, na_values=[""])
    countriesRaw = pd.read_csv(f"{dataDirectory}/countries.csv", **csvOptions)
    citiesRaw = pd.read_csv(f"{dataDirectory}/cities.csv", **csvOptions)
    weatherRaw = pd.read_csv(f"{dataDirectory}/weather.csv", **csvOptions)
    cultureRaw = pd.read_csv(f"{dataDirectory}/culture.csv", **csvOptions)
    tourismRaw = pd.read_csv(f"{dataDirectory}/tourism.csv", **csvOptions)
    airportsRaw = pd.read_csv(f"{dataDirectory}/airports.csv", **csvOptions)
    routesRaw = pd.read_csv(f"{dataDirectory}/routes.csv", **csvOptions)

    print(f"Selecting up to {targetCityCount} cities with complete data...")
    kept, dropped = selectCities(
        citiesRaw, countriesRaw, tourismRaw, weatherRaw, cultureRaw, airportsRaw, routesRaw
    )
    if len(dropped):
        print(f"  Dropped {len(dropped)} of {len(citiesRaw)} candidates for incomplete data:")
        for _, droppedCity in dropped.iterrows():
            print(f"    - {droppedCity['name']} ({droppedCity['iso2']}): {droppedCity['problem']}")
    if len(kept) < targetCityCount:
        print(f"  WARNING: only {len(kept)} complete cities available (target {targetCityCount}). "
              "Run the fetch_*.py scripts (see README) or add more cities to src/touristCityList.py.")
    citiesRaw = citiesRaw[citiesRaw["name"].isin(kept)].copy()
    citiesRaw["_order"] = citiesRaw["name"].map({cityName: position for position, cityName in enumerate(kept)})
    citiesRaw = citiesRaw.sort_values("_order").drop(columns="_order")
    weatherRaw = weatherRaw[weatherRaw["city_name"].isin(kept)]

    print("Cleaning...")
    countries = cleanCountries(countriesRaw)
    cities = cleanCities(citiesRaw, cultureRaw)

    with engine.begin() as conn:
        countries.to_sql("countries", conn, if_exists="append", index=False)
        countryIds = pd.read_sql("SELECT country_id, iso2 FROM countries", conn)

        cities = cities.merge(countryIds, on="iso2", how="left")
        citiesForDatabase = cities[
            ["name", "country_id", "population", "latitude", "longitude",
             "heritage_site_count", "attraction_count", "attraction_1", "attraction_2", "attraction_3"]
        ].rename(columns={"heritage_site_count": "heritage_sites", "attraction_count": "attractions"})
        citiesForDatabase.to_sql("cities", conn, if_exists="append", index=False)
        cityIds = pd.read_sql("SELECT city_id, name FROM cities", conn)

        weather = weatherRaw.merge(
            cityIds.rename(columns={"name": "city_name"}), on="city_name"
        )[["city_id", "month", "temperature_c", "precipitation_mm"]]
        weather.to_sql("weather", conn, if_exists="append", index=False)

        tourismColumns = ["country_id", "year", "arrivals"]
        if "tourism_growth_pct" in tourismRaw.columns:
            tourismColumns.append("tourism_growth_pct")
        if "iso2" in tourismRaw.columns:
            tourism = tourismRaw.merge(countryIds, on="iso2")[tourismColumns]
        else:
            tourism = tourismRaw.merge(
                countryIds.merge(countriesRaw[["iso2", "name"]], on="iso2").rename(
                    columns={"name": "country_name"}
                ),
                on="country_name",
            )[tourismColumns]
        tourism.to_sql("tourism", conn, if_exists="append", index=False)

        airports = airportsRaw.dropna(subset=["iata_code"]).merge(
            cityIds.rename(columns={"name": "city_name"}), on="city_name", how="inner"
        )
        airportsForDatabase = airports[["iata_code", "airport_name", "city_id", "latitude", "longitude"]].rename(
            columns={"airport_name": "name"}
        )
        airportsForDatabase.to_sql("airports", conn, if_exists="append", index=False)
        airportIds = pd.read_sql("SELECT airport_id, iata_code, city_id FROM airports", conn)

        routes = routesRaw.merge(
            airportIds.rename(columns={"airport_id": "source_airport_id", "iata_code": "source_iata", "city_id": "source_city"}),
            on="source_iata",
        ).merge(
            airportIds.rename(
                columns={"airport_id": "destination_airport_id", "iata_code": "destination_iata", "city_id": "destination_city"}
            ),
            on="destination_iata",
        )
        # Drop routes between airports serving the same city
        routes = routes[routes["source_city"] != routes["destination_city"]]
        routesForDatabase = routes[["source_airport_id", "destination_airport_id", "airline"]]
        routesForDatabase.to_sql("routes", conn, if_exists="append", index=False)

    print(
        f"Loaded {len(countries)} countries, {len(citiesForDatabase)} cities, "
        f"{len(weather)} weather rows, {len(airportsForDatabase)} airports, {len(routesForDatabase)} routes."
    )


if __name__ == "__main__":
    main()
