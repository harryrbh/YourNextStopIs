"""
distance.py — real-world distances between two coordinates, using
geopy instead of writing our own geographic maths.

Straight-line ("as the crow flies") distance between two points on a
sphere isn't simple arithmetic — the Earth is curved, so you can't
just use Pythagoras on latitude/longitude. geopy's `geodesic()`
function does this properly, using a well-tested formula (Karney's
algorithm on the WGS-84 ellipsoid, if you want to look it up), so we
don't need to.
"""
import pandas as pd
from geopy.distance import geodesic


def km_between(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Straight-line distance between two coordinates, in kilometres."""
    return geodesic((lat1, lon1), (lat2, lon2)).km


def add_distance_column(df: pd.DataFrame, from_lat: float, from_lon: float) -> pd.DataFrame:
    """Add a `distance_km` column: how far each row's (latitude,
    longitude) is from the given reference point."""
    df = df.copy()
    df["distance_km"] = df.apply(
        lambda row: km_between(from_lat, from_lon, row["latitude"], row["longitude"]), axis=1
    )
    return df
