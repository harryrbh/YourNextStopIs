"""
data_access.py — the one function every page needs: load every city
with its scores from the database, cached so we don't re-query
Postgres on every click.

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

from db import get_engine


@st.cache_data(ttl=300)  # re-query the database at most once every 5 minutes
def load_cities() -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT cf.*, c.name AS city_name, c.latitude, c.longitude, co.name AS country_name
        FROM city_features cf
        JOIN cities c ON c.city_id = cf.city_id
        JOIN countries co ON co.country_id = c.country_id
    """
    return pd.read_sql(query, engine)
