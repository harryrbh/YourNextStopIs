"""An airport serves every city within range (not just its nearest city)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import fetchAirports as fetchAirports


def _airports():
    return pd.DataFrame({
        "iata_code": ["KIX", "ITM", "FAR"], "airport_name": ["Kansai", "Itami", "Far"],
        "latitude": [34.43, 34.79, 0.0], "longitude": [135.24, 135.44, 0.0], "type": ["airport"] * 3,
        "icao_code": ["a", "b", "c"],
    })


def testAirportServesBothNearbyCities():
    cities = pd.DataFrame({"name": ["Osaka", "Kyoto"], "latitude": [34.69, 35.01], "longitude": [135.50, 135.77]})
    matchedAirports = fetchAirports.matchAirports(_airports(), cities)
    kyoto = set(matchedAirports[matchedAirports["city_name"] == "Kyoto"]["iata_code"])
    assert kyoto == {"KIX", "ITM"}  # Nearest-only would have given Kyoto nothing
    assert set(matchedAirports[matchedAirports["city_name"] == "Osaka"]["iata_code"]) == {"KIX", "ITM"}
    assert "FAR" not in set(matchedAirports["iata_code"])  # Out of range of every city


def testNearestFlagAndDistance():
    cities = pd.DataFrame({"name": ["Osaka", "Kyoto"], "latitude": [34.69, 35.01], "longitude": [135.50, 135.77]})
    matchedAirports = fetchAirports.matchAirports(_airports(), cities)
    kansaiRows = matchedAirports[matchedAirports["iata_code"] == "KIX"].set_index("city_name")
    assert bool(kansaiRows.loc["Osaka", "is_nearest"]) and not bool(kansaiRows.loc["Kyoto", "is_nearest"])
    assert 0 < kansaiRows.loc["Kyoto", "distance_km"] <= fetchAirports.maximumAirportKm
