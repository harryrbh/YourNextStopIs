"""
data_access.py — the one function every page needs: load every city
with its scores from the database, cached so we don't re-query the
database on every click.

This lives in its own file (rather than inside app.py) specifically so
that importing it doesn't also re-run app.py's page setup — Streamlit
only allows st.set_page_config() to be called once per page.
"""
import os
import sys

# src/*.py files import each other with plain names (e.g. `from db
# import get_engine`), which only works if src/ itself is on
# sys.path — true automatically when you run a script directly
# (`python src/build_features.py`), but not when this file is
# imported from elsewhere. So we add it here, once, for every page.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import get_engine


@st.cache_data(ttl=300)  # re-query the database at most once every 5 minutes
def load_cities() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT cf.*, c.name AS city_name, c.latitude, c.longitude,
               c.attraction_1, c.attraction_2, c.attraction_3,
               co.name AS country_name, co.iso2, co.region
        FROM city_features cf
        JOIN cities c ON c.city_id = cf.city_id
        JOIN countries co ON co.country_id = c.country_id
    """
    return pd.read_sql(query, engine)


@st.cache_data(ttl=300)
def load_direct_flights() -> pd.DataFrame:
    """One row per (origin city, destination city) with a direct
    route between them, according to the real OpenFlights data. Used
    to show "Direct flights to: ..." on a city's card and to draw
    flight-route lines on a map.
    """
    engine = get_engine()
    query = """
        SELECT DISTINCT c1.name AS from_city, c2.name AS to_city,
               c1.latitude AS from_lat, c1.longitude AS from_lon,
               c2.latitude AS to_lat, c2.longitude AS to_lon
        FROM routes r
        JOIN airports a1 ON a1.airport_id = r.source_airport_id
        JOIN airports a2 ON a2.airport_id = r.destination_airport_id
        JOIN cities c1 ON c1.city_id = a1.city_id
        JOIN cities c2 ON c2.city_id = a2.city_id
        WHERE c1.city_id != c2.city_id
    """
    return pd.read_sql(query, engine)


def direct_flights_from(flights: pd.DataFrame, city_name: str) -> list[str]:
    """Every city with at least one direct route from `city_name`."""
    return sorted(flights.loc[flights["from_city"] == city_name, "to_city"].unique().tolist())


@st.cache_data(ttl=300)
def load_country_indicators(city_id: int) -> pd.DataFrame:
    """One row: the country-level indicators for whichever country a
    given city belongs to (population, GDP per person, urbanisation).
    """
    engine = get_engine()
    query = """
        SELECT co.population, co.gdp_per_capita, co.urban_population_pct
        FROM countries co
        JOIN cities c ON c.country_id = co.country_id
        WHERE c.city_id = :city_id
    """
    return pd.read_sql(text(query), engine, params={"city_id": city_id})


@st.cache_data(ttl=300)
def load_monthly_weather(city_id: int) -> pd.DataFrame:
    """Twelve rows: one month's temperature/rainfall average each."""
    engine = get_engine()
    query = "SELECT month, temperature_c, precipitation_mm FROM weather WHERE city_id = :city_id ORDER BY month"
    return pd.read_sql(text(query), engine, params={"city_id": city_id})
