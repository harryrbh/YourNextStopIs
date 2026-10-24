import os
import sys

# Modules in src import each other by plain name
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd
import streamlit as st
from sqlalchemy import text

from database import getEngine


@st.cache_data(ttl=300)  # Re-query the database at most once every 5 minutes
def loadCities() -> pd.DataFrame:
    engine = getEngine()
    query = """
        SELECT cf.*, c.name AS city_name, c.population, c.latitude, c.longitude,
               c.attraction_1, c.attraction_2, c.attraction_3,
               COALESCE(co.name, 'Unknown') AS country_name,
               co.iso2, COALESCE(co.region, 'Unknown') AS region
        FROM city_features cf
        JOIN cities c ON c.city_id = cf.city_id
        LEFT JOIN countries co ON co.country_id = c.country_id
    """
    return pd.read_sql(query, engine)


@st.cache_data(ttl=300)
def loadDirectFlights() -> pd.DataFrame:
    engine = getEngine()
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


def directFlightsFrom(flights: pd.DataFrame, cityName: str) -> list[str]:
    """Every city with at least one direct route from `city_name`."""
    return sorted(flights.loc[flights["from_city"] == cityName, "to_city"].unique().tolist())


@st.cache_data(ttl=300)
def loadCountryIndicators(cityId: int) -> pd.DataFrame:
    engine = getEngine()
    query = """
        SELECT co.population, co.gdp_per_capita, co.urban_population_pct
        FROM countries co
        JOIN cities c ON c.country_id = co.country_id
        WHERE c.city_id = :city_id
    """
    return pd.read_sql(text(query), engine, params={"city_id": cityId})


@st.cache_data(ttl=300)
def loadMonthlyWeather(cityId: int) -> pd.DataFrame:
    """Twelve rows: one month's temperature/rainfall average each."""
    engine = getEngine()
    query = "SELECT month, temperature_c, precipitation_mm FROM weather WHERE city_id = :city_id ORDER BY month"
    return pd.read_sql(text(query), engine, params={"city_id": cityId})
