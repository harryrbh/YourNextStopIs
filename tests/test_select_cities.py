"""Checks select_cities.py drops incomplete cities and fills up to the target in order."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from select_cities import select_cities


def _data():
    cities = pd.DataFrame({"name": ["A", "B", "C", "D"], "iso2": ["FR", "FR", "FR", "XX"]})
    countries = pd.DataFrame({"iso2": ["FR"], "name": ["France"],
                              "gdp_per_capita_usd": [40000.0], "urban_population_pct": [80.0]})
    tourism = pd.DataFrame({"iso2": ["FR"], "arrivals": [1e6]})
    weather = pd.DataFrame([{"city_name": n, "month": m, "temperature_c": 10.0, "precipitation_mm": 50.0}
                            for n in ["A", "B", "C", "D"] for m in range(1, 13)])
    culture = pd.DataFrame({
        "city_name": ["A", "B", "C", "D"], "heritage_site_count": [1, 0, 0, 0],
        "attraction_count": [10, 0, 5, 5],  # B has no attractions
        "attraction_1": ["x"] * 4, "attraction_2": ["y"] * 4, "attraction_3": ["z"] * 4,
    })
    airports = pd.DataFrame({"iata_code": ["AAA", "BBB"], "city_name": ["A", "B"]})
    routes = pd.DataFrame({"source_iata": ["AAA"], "destination_iata": ["BBB"]})
    return cities, countries, tourism, weather, culture, airports, routes


def test_drops_cities_with_no_attractions_airports_or_country():
    kept, dropped = select_cities(*_data())
    assert kept == ["A"]  # B: no attractions, C: no airport, D: unknown country
    reasons = dict(zip(dropped["name"], dropped["problem"]))
    assert "no tourist attractions" in reasons["B"]
    assert "no airport" in reasons["C"]
    assert "country not in countries.csv" in reasons["D"]


def test_respects_target_and_priority_order():
    cities, countries, tourism, weather, culture, airports, routes = _data()
    culture["attraction_count"] = [10, 10, 10, 10]
    airports = pd.DataFrame({"iata_code": list("ABC"), "city_name": ["A", "B", "C"]})
    routes = pd.DataFrame({"source_iata": ["A"], "destination_iata": ["B"]})
    routes = pd.DataFrame({"source_iata": ["A", "B"], "destination_iata": ["B", "C"]})
    kept, _ = select_cities(cities, countries, tourism, weather, culture, airports, routes, target=2)
    assert kept == ["A", "B"]


def test_incomplete_weather_drops_city():
    cities, countries, tourism, weather, culture, airports, routes = _data()
    weather = weather[~((weather["city_name"] == "A") & (weather["month"] == 7))]
    kept, dropped = select_cities(cities, countries, tourism, weather, culture, airports, routes)
    assert "A" not in kept
    assert "incomplete weather data" in dropped.set_index("name").loc["A", "problem"]
