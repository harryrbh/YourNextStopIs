"""
load_data.py — reads the CSV files in data/ and loads them into
PostgreSQL.

This is intentionally a straight line, top to bottom: read a CSV,
clean it a little, insert it, move to the next one. No classes, no
plugin system — just five steps you can read from top to bottom.

Run it with:
    python src/load_data.py
"""
import os

import pandas as pd

from db import get_engine

# Always resolve data/ relative to this file, not the current working
# directory — so `python src/load_data.py` works the same whether you
# run it from the project root or from inside src/.
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def clean_countries(df: pd.DataFrame) -> pd.DataFrame:
    # Drop any row missing something we can't do without, and make sure
    # coordinates are physically possible. This is "data cleaning":
    # real-world CSVs almost always have a few bad rows.
    df = df.dropna(subset=["name", "iso2", "latitude", "longitude"])
    df = df[df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)]
    df = df.drop_duplicates(subset=["iso2"])
    return df[["iso2", "name", "region", "population", "gdp_per_capita_usd", "latitude", "longitude"]].rename(
        columns={"gdp_per_capita_usd": "gdp_per_capita"}
    )


def clean_cities(df: pd.DataFrame, culture: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["name", "latitude", "longitude"])
    df = df[df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)]
    df = df.merge(culture, left_on="name", right_on="city_name", how="left")
    df["heritage_site_count"] = df["heritage_site_count"].fillna(0)
    df["attraction_count"] = df["attraction_count"].fillna(0)
    return df


def main():
    engine = get_engine()

    print("Reading CSV files...")
    countries_raw = pd.read_csv(f"{DATA_DIR}/countries.csv")
    cities_raw = pd.read_csv(f"{DATA_DIR}/cities.csv")
    weather_raw = pd.read_csv(f"{DATA_DIR}/weather.csv")
    culture_raw = pd.read_csv(f"{DATA_DIR}/culture.csv")
    tourism_raw = pd.read_csv(f"{DATA_DIR}/tourism.csv")
    airports_raw = pd.read_csv(f"{DATA_DIR}/airports.csv")
    routes_raw = pd.read_csv(f"{DATA_DIR}/routes.csv")

    print("Cleaning...")
    countries = clean_countries(countries_raw)
    cities = clean_cities(cities_raw, culture_raw)

    with engine.begin() as conn:
        # 1. Countries first (cities reference them via country_id)
        countries.to_sql("countries", conn, if_exists="append", index=False)
        country_ids = pd.read_sql("SELECT country_id, iso2 FROM countries", conn)

        # 2. Cities, linked to their country
        cities = cities.merge(country_ids, on="iso2", how="left")
        cities_out = cities[
            ["name", "country_id", "population", "latitude", "longitude",
             "heritage_site_count", "attraction_count"]
        ].rename(columns={"heritage_site_count": "heritage_sites", "attraction_count": "attractions"})
        cities_out.to_sql("cities", conn, if_exists="append", index=False)
        city_ids = pd.read_sql("SELECT city_id, name FROM cities", conn)

        # 3. Weather, linked to city
        weather = weather_raw.merge(
            city_ids.rename(columns={"name": "city_name"}), on="city_name"
        )[["city_id", "month", "temperature_c", "precipitation_mm"]]
        weather.to_sql("weather", conn, if_exists="append", index=False)

        # 4. Tourism, linked to country
        tourism = tourism_raw.merge(
            country_ids.merge(countries_raw[["iso2", "name"]], on="iso2").rename(
                columns={"name": "country_name"}
            ),
            on="country_name",
        )[["country_id", "year", "arrivals"]]
        tourism.to_sql("tourism", conn, if_exists="append", index=False)

        # 5. Airports, linked to city by name (data/airports.csv already
        #    has a city_name column — see NOTES.md for how it was made)
        airports = airports_raw.dropna(subset=["iata_code"]).merge(
            city_ids.rename(columns={"name": "city_name"}), on="city_name", how="inner"
        )
        airports_out = airports[["iata_code", "airport_name", "city_id", "latitude", "longitude"]].rename(
            columns={"airport_name": "name"}
        )
        airports_out.to_sql("airports", conn, if_exists="append", index=False)
        airport_ids = pd.read_sql("SELECT airport_id, iata_code FROM airports", conn)

        # 6. Routes, linked to airports by IATA code
        routes = routes_raw.merge(
            airport_ids.rename(columns={"airport_id": "source_airport_id", "iata_code": "source_iata"}),
            on="source_iata",
        ).merge(
            airport_ids.rename(
                columns={"airport_id": "destination_airport_id", "iata_code": "destination_iata"}
            ),
            on="destination_iata",
        )
        routes_out = routes[["source_airport_id", "destination_airport_id", "airline"]]
        routes_out.to_sql("routes", conn, if_exists="append", index=False)

    print(
        f"Loaded {len(countries)} countries, {len(cities_out)} cities, "
        f"{len(weather)} weather rows, {len(airports_out)} airports, {len(routes_out)} routes."
    )


if __name__ == "__main__":
    main()
