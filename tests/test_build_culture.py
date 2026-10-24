"""Offline tests for build_culture.py using tiny fake GeoNames/UNESCO extracts."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import build_culture as bc


def _gn_line(name, lat, lon, fclass, fcode, alts=""):
    cols = ["1", name, name, alts, str(lat), str(lon), fclass, fcode, "FR", "", "", "", "", "", "0", "", "", "Europe/Paris", "2020-01-01"]
    return "\t".join(cols)


def _write_geonames(tmp_path):
    lines = [
        _gn_line("Eiffel Tower", 48.8584, 2.2945, "S", "TOWR", "Tour Eiffel,Torre Eiffel,Eiffelturm,Tour Eiffel"),
        _gn_line("Louvre Museum", 48.8606, 2.3376, "S", "MUS", "Louvre,Le Louvre,Museo del Louvre"),
        _gn_line("Small Chapel", 48.87, 2.30, "S", "CH", ""),
        _gn_line("Some Hotel", 48.86, 2.35, "S", "HTL", "a,b,c,d,e"),      # not a sight
        _gn_line("Jardin X", 48.85, 2.34, "L", "PRK", "Garden X"),          # park counts
        _gn_line("Far Castle", 43.0, 5.0, "S", "CSTL", "Chateau"),          # too far from Paris
        _gn_line('Bad "quote" name', 48.85, 2.35, "S", "MNMT", ""),         # stray quotes must not break parsing
    ]
    p = tmp_path / "FR.txt"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def test_sights_are_counted_ranked_by_fame_and_hotels_ignored(tmp_path):
    sights = bc.load_geonames_sights(str(_write_geonames(tmp_path)))
    assert "Some Hotel" not in set(sights["name"])
    paris = pd.Series({"name": "Paris", "latitude": 48.8566, "longitude": 2.3522})
    count, names = bc.top_sights_for_city(paris, sights)
    assert count == 5  # tower, louvre, chapel, park, quoted monument; not the hotel or far castle
    assert names[:2] == ["Eiffel Tower", "Louvre Museum"]  # most alternate names first


def test_unesco_xml_and_heritage_counts(tmp_path):
    xml = tmp_path / "whc.xml"
    xml.write_text("""<query><row><site>Banks of the Seine</site><latitude>48.86</latitude><longitude>2.33</longitude></row>
    <row><site>Mont-Saint-Michel</site><latitude>48.63</latitude><longitude>-1.51</longitude></row>
    <row><site>Serial site</site><latitude></latitude><longitude></longitude></row></query>""", encoding="utf-8")
    unesco = bc.load_unesco(str(xml))
    assert len(unesco) == 2  # the row with no coordinates is dropped
    cities = pd.DataFrame({"name": ["Paris", "Lyon"], "latitude": [48.8566, 45.76], "longitude": [2.3522, 4.83]})
    counts = bc.count_heritage(cities, unesco)
    assert counts["Paris"] == 1 and counts["Lyon"] == 0


def test_city_without_geonames_file_gets_zero_sights(tmp_path):
    cities = pd.DataFrame({"name": ["Paris"], "iso2": ["FR"], "latitude": [48.8566], "longitude": [2.3522]})
    unesco = pd.DataFrame({"site": [], "latitude": [], "longitude": []})
    out = bc.build_culture(cities, unesco, {})
    assert out.loc[0, "attraction_count"] == 0 and out.loc[0, "attraction_1"] == ""


def test_unesco_xml_with_geolocations_element(tmp_path):
    """Newer UNESCO exports have no <latitude>/<longitude>; coordinates live under <geolocations>."""
    xml = tmp_path / "whc.xml"
    xml.write_text("""<query>
    <row><site>Banks of the Seine</site><geolocations><geolocation><latitude>48.86</latitude><longitude>2.33</longitude></geolocation></geolocations></row>
    <row><site>Serial A</site><geolocations><geolocation lat="48.85" lon="2.30"/><geolocation lat="10.0" lon="10.0"/></geolocations></row>
    <row><site>Text style</site><geolocations>48.87, 2.34</geolocations></row>
    <row><site>No coords</site><geolocations></geolocations></row></query>""", encoding="utf-8")
    unesco = bc.load_unesco(str(xml))
    assert set(unesco["site"]) == {"Banks of the Seine", "Serial A", "Text style"}
    cities = pd.DataFrame({"name": ["Paris"], "latitude": [48.8566], "longitude": [2.3522]})
    assert bc.count_heritage(cities, unesco)["Paris"] == 3  # serial site counted once


def test_unesco_xml_without_coordinates_explains_layout(tmp_path):
    import pytest
    xml = tmp_path / "whc.xml"
    xml.write_text("<query><row><site>X</site><geolocations>unparseable</geolocations></row></query>", encoding="utf-8")
    with pytest.raises(ValueError, match="First record"):
        bc.load_unesco(str(xml))
