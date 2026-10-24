"""Real-world distances between two coordinates, using geopy instead of writing our own geographic maths."""
import pandas as pd
from geopy.distance import geodesic


def distanceBetweenKm(latitudeA: float, longitudeA: float, latitudeB: float, longitudeB: float) -> float:
    """Straight-line distance between two coordinates, in kilometres."""
    return geodesic((latitudeA, longitudeA), (latitudeB, longitudeB)).km


def addDistanceColumn(dataFrame: pd.DataFrame, fromLatitude: float, fromLongitude: float) -> pd.DataFrame:
    """Add a `distance_km` column: how far each row's (latitude, longitude) is from the given reference point."""
    dataFrame = dataFrame.copy()
    dataFrame["distance_km"] = dataFrame.apply(
        lambda row: distanceBetweenKm(fromLatitude, fromLongitude, row["latitude"], row["longitude"]), axis=1
    )
    return dataFrame
