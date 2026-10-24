import os
import re
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from fetchAirports import haversineKm  # Same great-circle helper used for airports

dataDirectory = os.path.join(os.path.dirname(__file__), "..", "data")
rawDirectory = os.path.join(dataDirectory, "raw")
geonamesDirectory = os.path.join(rawDirectory, "geonames")

heritageRadiusKm = 25
attractionRadiusKm = 10
cultureColumns = ["city_name", "heritage_site_count", "attraction_count", "attraction_1", "attraction_2", "attraction_3"]

# GeoNames feature codes (feature class S = spot, building, farm; L.PRK = park)
sightFeatureCodes = {
    "MUS",
    "CSTL",
    "PAL",
    "MNMT",  # Monument
    "HSTS",  # Historical site
    "RUIN",
    "ANS",  # Ancient site
    "ARCH",
    "AMTH",  # Amphitheater
    "CH",
    "MSQE",
    "TMPL",
    "SHRN",
    "MSTY",  # Monastery
    "SYG",  # Synagogue
    "THTR",
    "OPRA",  # Opera house
    "GDN",  # Garden(s)
    "ZOO",
    "TOWR",
    "LIBR",
    "PRK",  # Park (feature class L)
}

# GeoNames' tab-separated column order (readme.txt in the same folder as the downloads)
geonamesColumns = [
    "geonameid", "name", "asciiname", "alternatenames", "latitude", "longitude",
    "feature_class", "feature_code", "country_code", "cc2", "admin1_code",
    "admin2_code", "admin3_code", "admin4_code", "population", "elevation",
    "dem", "timezone", "modification_date",
]


# UNESCO

def _findColumn(columns, candidates):
    lowered = {columnName.lower().strip(): columnName for columnName in columns}
    for cand in candidates:
        if cand in lowered:
            return lowered[cand]
    return None


_number = re.compile(r"-?\d+(?:\.\d+)?")


def _pointsFromText(text: str) -> list[tuple[float, float]]:
    """Pull (lat, lon) pairs out of free text like '48.8584, 2.2945' or 'lat: 48.8 lon: 2.3'."""
    nums = [float(numberText) for numberText in _number.findall(text or "")]
    pairs = list(zip(nums[0::2], nums[1::2]))
    return [(latitudeValue, longitudeValue) for latitudeValue, longitudeValue in pairs if -90 <= latitudeValue <= 90 and -180 <= longitudeValue <= 180]


def _pointsFromElement(element) -> list[tuple[float, float]]:
    """All coordinates under an XML element."""
    points = []
    for node in element.iter():
        keyed = {itemKey.lower(): itemValue for itemKey, itemValue in node.attrib.items()}
        keyed.update({child.tag.lower(): (child.text or "").strip() for child in node if len(child) == 0})
        latitude = next((itemValue for itemKey, itemValue in keyed.items() if itemKey in ("lat", "latitude", "y")), None)
        longitude = next((itemValue for itemKey, itemValue in keyed.items() if itemKey in ("lon", "long", "lng", "longitude", "x")), None)
        try:
            points.append((float(latitude), float(longitude)))
        except (TypeError, ValueError):
            pass
    if points:
        return points
    return _pointsFromText(" ".join(textPart.strip() for textPart in element.itertext() if textPart.strip()))


def _loadUnescoXml(path: str) -> pd.DataFrame:
    """One output row per (site, coordinate)."""
    cultureTable = []
    for row in ET.parse(path).getroot().iter("row"):
        kids = {child.tag.lower(): child for child in row}
        nameEl = next((kids[tagName] for tagName in ("site", "name", "name_en", "title") if tagName in kids), None)
        if nameEl is None:
            continue
        name = (nameEl.text or "").strip()
        points = []
        # Try the dedicated coordinate fields first, then the plain location text as a last resort
        for elementName in ("geolocations", "geolocation", "coordinates", "latitude"):
            if elementName in kids:
                if elementName == "latitude" and "longitude" in kids:
                    try:
                        points = [(float((kids["latitude"].text or "").strip()), float((kids["longitude"].text or "").strip()))]
                    except ValueError:
                        points = []
                else:
                    points = _pointsFromElement(kids[elementName])
                if points:
                    break
        if not points and "location" in kids:
            points = _pointsFromElement(kids["location"])
        cultureTable.extend({"site": name, "latitude": latitudeValue, "longitude": longitudeValue} for latitudeValue, longitudeValue in points)
    return pd.DataFrame(cultureTable, columns=["site", "latitude", "longitude"])


def loadUnesco(path: str) -> pd.DataFrame:
    fileExtension = os.path.splitext(path)[1].lower()
    if fileExtension == ".xml":
        cultureTable = _loadUnescoXml(path)
        if cultureTable.empty:
            # Show the first record so the layout can be inspected, instead of failing blindly
            first = next(ET.parse(path).getroot().iter("row"), None)
            sample = ET.tostring(first, encoding="unicode")[:1500] if first is not None else "(no <row> elements)"
            raise ValueError(
                f"Found no coordinates in {path}. First record:\n{sample}\n"
                "Adapt _load_unesco_xml() to this layout, or save the list as CSV/Excel with "
                "site, latitude, longitude columns (see dataSources.md)."
            )
        return cultureTable.reset_index(drop=True)

    dataFrame = pd.read_excel(path) if fileExtension in (".xls", ".xlsx") else pd.read_csv(path)
    site = _findColumn(dataFrame.columns, ["site", "name", "name_en", "site_name", "title"])
    latitude = _findColumn(dataFrame.columns, ["latitude", "lat", "y"])
    longitude = _findColumn(dataFrame.columns, ["longitude", "lon", "long", "lng", "x"])
    if not (site and latitude and longitude):
        raise ValueError(
            f"Couldn't find site/latitude/longitude columns in {path}. Columns present: "
            f"{list(dataFrame.columns)}. Rename them, or add the right names to load_unesco()."
        )
    cultureTable = pd.DataFrame({
        "site": dataFrame[site].astype(str),
        "latitude": pd.to_numeric(dataFrame[latitude], errors="coerce"),
        "longitude": pd.to_numeric(dataFrame[longitude], errors="coerce"),
    })
    return cultureTable.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)


def countHeritage(cities: pd.DataFrame, unesco: pd.DataFrame, radiusKm: float = heritageRadiusKm) -> pd.Series:
    """DISTINCT UNESCO sites with at least one location within radius_km, indexed by city name."""
    latitude, longitude = unesco["latitude"].to_numpy(), unesco["longitude"].to_numpy()
    sites = unesco["site"].to_numpy()
    counts = {}
    for _, city in cities.iterrows():
        distances = haversineKm(city["latitude"], city["longitude"], latitude, longitude)
        counts[city["name"]] = len(set(sites[distances <= radiusKm]))
    return pd.Series(counts)


# GeoNames

def loadGeonamesSights(path: str) -> pd.DataFrame:
    """Read one GeoNames country file, keeping only sight-type features."""
    dataFrame = pd.read_csv(path, sep="\t", header=None, names=geonamesColumns, usecols=range(len(geonamesColumns)),
                     dtype=str, keep_default_na=False, quoting=3)  # Names contain stray quote characters
    isPark = (dataFrame["feature_class"] == "L") & (dataFrame["feature_code"] == "PRK")
    isSpot = (dataFrame["feature_class"] == "S") & dataFrame["feature_code"].isin(sightFeatureCodes - {"PRK"})
    dataFrame = dataFrame[isPark | isSpot].copy()
    dataFrame["latitude"] = pd.to_numeric(dataFrame["latitude"], errors="coerce")
    dataFrame["longitude"] = pd.to_numeric(dataFrame["longitude"], errors="coerce")
    dataFrame["fame"] = dataFrame["alternatenames"].apply(lambda alternateNames: len([alternateName for alternateName in alternateNames.split(",") if alternateName]))
    return dataFrame.dropna(subset=["latitude", "longitude"])[["name", "asciiname", "latitude", "longitude", "fame"]]


_generic = re.compile(r"^(church|parish church|chapel|park|garden|gardens|museum|monument|tower)$", re.IGNORECASE)


def topSightsForCity(city: pd.Series, sights: pd.DataFrame, radiusKm: float = attractionRadiusKm):
    """(count, up to three best-known names) of sights within radius_km of the city."""
    distances = haversineKm(city["latitude"], city["longitude"], sights["latitude"].to_numpy(), sights["longitude"].to_numpy())
    near = sights[distances <= radiusKm]
    if near.empty:
        return 0, []
    near = near.assign(_dist=distances[distances <= radiusKm]).sort_values(["fame", "_dist"], ascending=[False, True])
    names = []
    for sightName in near["name"]:
        sightName = sightName.strip()
        if sightName and not _generic.match(sightName) and sightName not in names:
            names.append(sightName)
        if len(names) == 3:
            break
    return len(near), names


def buildCulture(cities: pd.DataFrame, unesco: pd.DataFrame, sightsByCountry: dict) -> pd.DataFrame:
    heritage = countHeritage(cities, unesco)
    rows = []
    for _, city in cities.iterrows():
        sights = sightsByCountry.get(city["iso2"])
        count, names = (0, []) if sights is None else topSightsForCity(city, sights)
        names += [""] * (3 - len(names))
        rows.append({
            "city_name": city["name"],
            "heritage_site_count": int(heritage[city["name"]]),
            "attraction_count": count,
            "attraction_1": names[0], "attraction_2": names[1], "attraction_3": names[2],
        })
    return pd.DataFrame(rows, columns=cultureColumns)


def checkFeatureCodes(path: str) -> None:
    """If geonamesFeatureCodes.txt is present, warn about any code we use that GeoNames doesn't list."""
    if not os.path.exists(path):
        return
    known = set()
    with open(path, encoding="utf-8") as featureCodesFile:
        for line in featureCodesFile:
            code = line.split("\t")[0].strip()  # For example S.MUS
            if "." in code:
                known.add(code.split(".", 1)[1])
    unknown = sorted(city for city in sightFeatureCodes if city not in known)
    if unknown:
        print(f"  NOTE: these codes aren't in geonamesFeatureCodes.txt and will match nothing: {unknown}")


def findUnescoFile() -> str:
    for fileExtension in (".xml", ".csv", ".xlsx", ".xls"):
        candidatePath = os.path.join(rawDirectory, f"unescoHeritageSites{fileExtension}")
        if os.path.exists(candidatePath):
            return candidatePath
    raise FileNotFoundError(
        "No UNESCO file found. Download the World Heritage List from https://whc.unesco.org/en/list/ "
        "and save it as data/raw/unescoHeritageSites.xml (or .csv/.xlsx). See dataSources.md."
    )


def main():
    cities = pd.read_csv(f"{dataDirectory}/cities.csv", keep_default_na=False, na_values=[""])
    checkFeatureCodes(os.path.join(rawDirectory, "geonamesFeatureCodes.txt"))
    unesco = loadUnesco(findUnescoFile())
    print(f"Loaded {len(unesco)} UNESCO sites with coordinates.")

    sightsByCountry = {}
    for countryCode in sorted(cities["iso2"].unique()):
        path = os.path.join(geonamesDirectory, f"{countryCode}.txt")
        if not os.path.exists(path):
            print(f"  MISSING {path} — cities in {countryCode} will have no attractions "
                  f"(run: python src/downloadRawData.py)")
            continue
        sightsByCountry[countryCode] = loadGeonamesSights(path)
        print(f"  {countryCode}: {len(sightsByCountry[countryCode])} sight features")

    culture = buildCulture(cities, unesco, sightsByCountry)
    culture.to_csv(f"{dataDirectory}/culture.csv", index=False)
    withSights = int((culture["attraction_count"] > 0).sum())
    print(f"\nSaved {len(culture)} cities to data/culture.csv ({withSights} have at least one sight).")
    print("Spot-check a few you know:\n", culture.head(8).to_string(index=False))


if __name__ == "__main__":
    main()
