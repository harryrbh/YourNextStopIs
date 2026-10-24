"""An airport serves every city within range (not just its nearest city)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import fetch_airports as fa


def _airports():
    return pd.DataFrame({
        "iata_code": ["KIX", "ITM", "FAR"], "airport_name": ["Kansai", "Itami", "Far"],
        "latitude": [34.43, 34.79, 0.0], "longitude": [135.24, 135.44, 0.0], "type": ["airport"] * 3,
        "icao_code": ["a", "b", "c"],
    })


def test_airport_serves_both_nearby_cities():
    cities = pd.DataFrame({"name": ["Osaka", "Kyoto"], "latitude": [34.69, 35.01], "longitude": [135.50, 135.77]})
    out = fa.match_airports(_airports(), cities)
    kyoto = set(out[out["city_name"] == "Kyoto"]["iata_code"])
    assert kyoto == {"KIX", "ITM"}  # nearest-only would have given Kyoto nothing
    assert set(out[out["city_name"] == "Osaka"]["iata_code"]) == {"KIX", "ITM"}
    assert "FAR" not in set(out["iata_code"])  # out of range of every city


def test_nearest_flag_and_distance():
    cities = pd.DataFrame({"name": ["Osaka", "Kyoto"], "latitude": [34.69, 35.01], "longitude": [135.50, 135.77]})
    out = fa.match_airports(_airports(), cities)
    kix = out[out["iata_code"] == "KIX"].set_index("city_name")
    assert bool(kix.loc["Osaka", "is_nearest"]) and not bool(kix.loc["Kyoto", "is_nearest"])
    assert 0 < kix.loc["Kyoto", "distance_km"] <= fa.MAX_AIRPORT_KM
