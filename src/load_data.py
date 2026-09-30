"""
load_data.py — reads the CSV files in data/ and loads them into the
SQLite database.

This is intentionally a straight line, top to bottom: read a CSV,
clean it a little, insert it, move to the next one. No classes, no
plugin system — just five steps you can read from top to bottom.

Run it with:
    python src/load_data.py
"""
import os

import pandas as pd

from db import get_engine
from select_cities import TARGET_CITY_COUNT, select_cities

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
    return df[
        ["iso2", "name", "region", "population", "gdp_per_capita_usd", "urban_population_pct", "latitude", "longitude"]
    ].rename(columns={"gdp_per_capita_usd": "gdp_per_capita"})


def clean_cities(df: pd.DataFrame, culture: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=["name", "latitude", "longitude"])
    df = df[df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)]
    df = df.merge(culture, left_on="name", right_on="city_name", how="left")
    df["heritage_site_count"] = df["heritage_site_count"].fillna(0)
    df["attraction_count"] = df["attraction_count"].fillna(0)
    for col in ["attraction_1", "attraction_2", "attraction_3"]:
        df[col] = df[col].fillna("")
    return df


def main():
    engine = get_engine()

    print("Reading CSV files...")
    # keep_default_na=False: pandas would otherwise read Namibia's ISO code "NA" as missing.
    csv_opts = dict(keep_default_na=False, na_values=[""])
    countries_raw = pd.read_csv(f"{DATA_DIR}/countries.csv", **csv_opts)
    cities_raw = pd.read_csv(f"{DATA_DIR}/cities.csv", **csv_opts)
    weather_raw = pd.read_csv(f"{DATA_DIR}/weather.csv")
    culture_raw = pd.read_csv(f"{DATA_DIR}/culture.csv")
    tourism_raw = pd.read_csv(f"{DATA_DIR}/tourism.csv")
    airports_raw = pd.read_csv(f"{DATA_DIR}/airports.csv")
    routes_raw = pd.read_csv(f"{DATA_DIR}/routes.csv")

    print(f"Selecting up to {TARGET_CITY_COUNT} cities with complete data...")
    kept, dropped = select_cities(
        cities_raw, countries_raw, tourism_raw, weather_raw, culture_raw, airports_raw, routes_raw
    )
    if len(dropped):
        print(f"  Dropped {len(dropped)} of {len(cities_raw)} candidates for incomplete data:")
        for _, d in dropped.iterrows():
            print(f"    - {d['name']} ({d['iso2']}): {d['problem']}")
    if len(kept) < TARGET_CITY_COUNT:
        print(f"  WARNING: only {len(kept)} complete cities available (target {TARGET_CITY_COUNT}). "
              "Run the fetch_*.py scripts (see README) or add more cities to src/tourist_cities.py.")
    cities_raw = cities_raw[cities_raw["name"].isin(kept)].copy()
    cities_raw["_order"] = cities_raw["name"].map({n: i for i, n in enumerate(kept)})
    cities_raw = cities_raw.sort_values("_order").drop(columns="_order")
    weather_raw = weather_raw[weather_raw["city_name"].isin(kept)]

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
             "heritage_site_count", "attraction_count", "attraction_1", "attraction_2", "attraction_3"]
        ].rename(columns={"heritage_site_count": "heritage_sites", "attraction_count": "attractions"})
        cities_out.to_sql("cities", conn, if_exists="append", index=False)
        city_ids = pd.read_sql("SELECT city_id, name FROM cities", conn)

        # 3. Weather, linked to city
        weather = weather_raw.merge(
            city_ids.rename(columns={"name": "city_name"}), on="city_name"
        )[["city_id", "month", "temperature_c", "precipitation_mm"]]
        weather.to_sql("weather", conn, if_exists="append", index=False)

        # 4. Tourism, linked to country.
        # The sample tourism.csv only has a country_name column, so we
        # match on name. If you've run fetch_tourism.py, tourism.csv
        # also has an iso2 column — matching on that is more reliable,
        # because country *names* don't always match exactly between
        # different data sources (e.g. "United States" vs "United
        # States of America"), but ISO codes always do.
        tourism_cols = ["country_id", "year", "arrivals"]
        if "tourism_growth_pct" in tourism_raw.columns:
            tourism_cols.append("tourism_growth_pct")
        if "iso2" in tourism_raw.columns:
            tourism = tourism_raw.merge(country_ids, on="iso2")[tourism_cols]
        else:
            tourism = tourism_raw.merge(
                country_ids.merge(countries_raw[["iso2", "name"]], on="iso2").rename(
                    columns={"name": "country_name"}
                ),
                on="country_name",
            )[tourism_cols]
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
