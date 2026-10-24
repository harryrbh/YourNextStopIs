"""Downloads the raw data extracts into data/raw/ so the build scripts can run offline."""
import io
import os
import time
import zipfile

import pandas as pd
import requests

dataDirectory = os.path.join(os.path.dirname(__file__), "..", "data")
rawDirectory = os.path.join(dataDirectory, "raw")
geonamesBaseUrl = "https://download.geonames.org/export/dump"
openFlightsBaseUrl = "https://raw.githubusercontent.com/jpatokal/openflights/master/data"
unescoXmlUrl = "https://whc.unesco.org/en/list/xml/"
requestHeaders = {"User-Agent": "city-break-simple/1.0 (learning project)"}


def _getWithRetry(url: str, attempts: int = 4) -> bytes:
    """GET with simple in-place retry on 429/5xx/network errors."""
    last = None
    for attemptNumber in range(attempts):
        try:
            response = requests.get(url, headers=requestHeaders, timeout=180)
            if response.status_code == 200:
                return response.content
            last = f"HTTP {response.status_code}"
            if response.status_code not in (429, 500, 502, 503, 504):
                break
        except requests.RequestException as error:
            last = str(error)
        time.sleep(5 * 2 ** attemptNumber)
    raise RuntimeError(last)


def _save(path: str, content: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as outputFile:
        outputFile.write(content)


def main():
    cities = pd.read_csv(f"{dataDirectory}/cities.csv", keep_default_na=False, na_values=[""])
    jobs = []  # (label, url, destination, is_zip_of_txt)
    for countryCode in sorted(cities["iso2"].unique()):
        jobs.append((f"GeoNames {countryCode}", f"{geonamesBaseUrl}/{countryCode}.zip", f"{rawDirectory}/geonames/{countryCode}.txt", True))
    jobs += [
        ("GeoNames feature codes", f"{geonamesBaseUrl}/geonamesFeatureCodes.txt", f"{rawDirectory}/geonamesFeatureCodes.txt", False),
        ("GeoNames readme", f"{geonamesBaseUrl}/readme.txt", f"{rawDirectory}/geonamesReadme.txt", False),
        ("OpenFlights airports", f"{openFlightsBaseUrl}/airports.dat", f"{rawDirectory}/airports.dat", False),
        ("OpenFlights routes", f"{openFlightsBaseUrl}/routes.dat", f"{rawDirectory}/routes.dat", False),
        ("UNESCO World Heritage List", unescoXmlUrl, f"{rawDirectory}/unescoHeritageSites.xml", False),
    ]

    failed = []
    for label, url, dest, isZip in jobs:
        if os.path.exists(dest):
            continue
        try:
            content = _getWithRetry(url)
            if isZip:  # FR.zip contains FR.txt (and readme.txt)
                with zipfile.ZipFile(io.BytesIO(content)) as zipArchive:
                    content = zipArchive.read(os.path.basename(dest))
            _save(dest, content)
            print(f"  downloaded {label}")
        except Exception as error:  # Report and carry on: one bad file shouldn't stop the rest
            failed.append((label, url, dest, str(error)))

    have = sum(os.path.exists(destination) for _, _, destination, _ in jobs)
    print(f"\n{have} of {len(jobs)} files are in data/raw/.")
    if failed:
        print("\nCould not download these — open the URL in a browser and save it at the path shown:")
        for label, url, dest, errorMessage in failed:
            print(f"  {label}\n    URL : {url}\n    SAVE: {os.path.relpath(dest, os.path.join(dataDirectory, '..'))}   ({errorMessage})")
            if dest.endswith("unescoHeritageSites.xml"):
                print("    (On the UNESCO page use the download/export option for the full list — XML or "
                      "Excel; save Excel/CSV as unescoHeritageSites.xlsx / unescoHeritageSites.csv instead.)")
    else:
        print("Next: python src/fetchAirports.py && python src/buildCulture.py")


if __name__ == "__main__":
    main()
