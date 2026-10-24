"""Offline tests for buildCulture.py using tiny fake GeoNames/UNESCO extracts."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import buildCulture as buildCulture


def geonamesLine(name, latitude, longitude, fclass, fcode, alts=""):
    fields = ["1", name, name, alts, str(latitude), str(longitude), fclass, fcode, "FR", "", "", "", "", "", "0", "", "", "Europe/Paris", "2020-01-01"]
    return "\t".join(fields)


def _writeGeonames(tmp_path):
    lines = [
        geonamesLine("Eiffel Tower", 48.8584, 2.2945, "S", "TOWR", "Tour Eiffel,Torre Eiffel,Eiffelturm,Tour Eiffel"),
        geonamesLine("Louvre Museum", 48.8606, 2.3376, "S", "MUS", "Louvre,Le Louvre,Museo del Louvre"),
        geonamesLine("Small Chapel", 48.87, 2.30, "S", "CH", ""),
        geonamesLine("Some Hotel", 48.86, 2.35, "S", "HTL", "a,b,c,d,e"),  # Not a sight
        geonamesLine("Jardin X", 48.85, 2.34, "L", "PRK", "Garden X"),  # Park counts
        geonamesLine("Far Castle", 43.0, 5.0, "S", "CSTL", "Chateau"),  # Too far from Paris
        geonamesLine('Bad "quote" name', 48.85, 2.35, "S", "MNMT", ""),  # Stray quotes must not break parsing
    ]
    geonamesPath = tmp_path / "FR.txt"
    geonamesPath.write_text("\n".join(lines), encoding="utf-8")
    return geonamesPath


def testSightsAreCountedRankedByFameAndHotelsIgnored(tmp_path):
    sights = buildCulture.loadGeonamesSights(str(_writeGeonames(tmp_path)))
    assert "Some Hotel" not in set(sights["name"])
    paris = pd.Series({"name": "Paris", "latitude": 48.8566, "longitude": 2.3522})
    count, names = buildCulture.topSightsForCity(paris, sights)
    assert count == 5
    assert names[:2] == ["Eiffel Tower", "Louvre Museum"]  # Most alternate names first


def testUnescoXmlAndHeritageCounts(tmp_path):
    xmlPath = tmp_path / "whc.xml"
    xmlPath.write_text("""<query><row><site>Banks of the Seine</site><latitude>48.86</latitude><longitude>2.33</longitude></row>
    <row><site>Mont-Saint-Michel</site><latitude>48.63</latitude><longitude>-1.51</longitude></row>
    <row><site>Serial site</site><latitude></latitude><longitude></longitude></row></query>""", encoding="utf-8")
    unesco = buildCulture.loadUnesco(str(xmlPath))
    assert len(unesco) == 2  # The row with no coordinates is dropped
    cities = pd.DataFrame({"name": ["Paris", "Lyon"], "latitude": [48.8566, 45.76], "longitude": [2.3522, 4.83]})
    counts = buildCulture.countHeritage(cities, unesco)
    assert counts["Paris"] == 1 and counts["Lyon"] == 0


def testCityWithoutGeonamesFileGetsZeroSights(tmp_path):
    cities = pd.DataFrame({"name": ["Paris"], "iso2": ["FR"], "latitude": [48.8566], "longitude": [2.3522]})
    unesco = pd.DataFrame({"site": [], "latitude": [], "longitude": []})
    cultureTable = buildCulture.buildCulture(cities, unesco, {})
    assert cultureTable.loc[0, "attraction_count"] == 0 and cultureTable.loc[0, "attraction_1"] == ""


def testUnescoXmlWithGeolocationsElement(tmp_path):
    """Newer UNESCO exports have no <latitude>/<longitude>; coordinates live under <geolocations>."""
    xmlPath = tmp_path / "whc.xml"
    xmlPath.write_text("""<query>
    <row><site>Banks of the Seine</site><geolocations><geolocation><latitude>48.86</latitude><longitude>2.33</longitude></geolocation></geolocations></row>
    <row><site>Serial A</site><geolocations><geolocation lat="48.85" lon="2.30"/><geolocation lat="10.0" lon="10.0"/></geolocations></row>
    <row><site>Text style</site><geolocations>48.87, 2.34</geolocations></row>
    <row><site>No coords</site><geolocations></geolocations></row></query>""", encoding="utf-8")
    unesco = buildCulture.loadUnesco(str(xmlPath))
    assert set(unesco["site"]) == {"Banks of the Seine", "Serial A", "Text style"}
    cities = pd.DataFrame({"name": ["Paris"], "latitude": [48.8566], "longitude": [2.3522]})
    assert buildCulture.countHeritage(cities, unesco)["Paris"] == 3  # Serial site counted once


def testUnescoXmlWithoutCoordinatesExplainsLayout(tmp_path):
    import pytest
    xmlPath = tmp_path / "whc.xml"
    xmlPath.write_text("<query><row><site>X</site><geolocations>unparseable</geolocations></row></query>", encoding="utf-8")
    with pytest.raises(ValueError, match="First record"):
        buildCulture.loadUnesco(str(xmlPath))
