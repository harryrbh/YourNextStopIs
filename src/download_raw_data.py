"""
download_raw_data.py — downloads the raw data extracts into data/raw/ so
the build_* scripts can run offline and repeatably.

WHAT IT FETCHES (details and what each file means: DATA_SOURCES.md)
------------------------------------------------------------------
  data/raw/geonames/<ISO2>.txt   one GeoNames file per country in data/cities.csv
                                 (source: https://download.geonames.org/export/dump/<ISO2>.zip)
  data/raw/featureCodes_en.txt   GeoNames' dictionary of feature codes (to interpret the above)
  data/raw/geonames_readme.txt   GeoNames' column-by-column format description
  data/raw/airports.dat          OpenFlights airports   (github.com/jpatokal/openflights)
  data/raw/routes.dat            OpenFlights flight routes
  data/raw/unesco_whc.xml        UNESCO World Heritage List — see the note below

Files already present are skipped, so it is safe to re-run. Anything that
can't be downloaded (blocked network, changed URL) is listed at the end
with the address to open in a browser and the exact path to save it as.

UNESCO NOTE: UNESCO publishes its list as a downloadable export from
https://whc.unesco.org/en/list/ . The direct link below is a best guess
and may change; if it fails, download it by hand (instructions printed).

Run it with:
    python src/download_raw_data.py
"""
import io
import os
import time
import zipfile

import pandas as pd
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
GEONAMES = "https://download.geonames.org/export/dump"
OPENFLIGHTS = "https://raw.githubusercontent.com/jpatokal/openflights/master/data"
UNESCO_XML = "https://whc.unesco.org/en/list/xml/"
HEADERS = {"User-Agent": "city-break-simple/1.0 (learning project)"}


def _get(url: str, attempts: int = 4) -> bytes:
    """GET with simple in-place retry on 429/5xx/network errors."""
    last = None
    for i in range(attempts):
        try:
            r = requests.get(url, headers=HEADERS, timeout=180)
            if r.status_code == 200:
                return r.content
            last = f"HTTP {r.status_code}"
            if r.status_code not in (429, 500, 502, 503, 504):
                break
        except requests.RequestException as e:
            last = str(e)
        time.sleep(5 * 2 ** i)
    raise RuntimeError(last)


def _save(path: str, content: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(content)


def main():
    cities = pd.read_csv(f"{DATA_DIR}/cities.csv", keep_default_na=False, na_values=[""])
    jobs = []  # (label, url, destination, is_zip_of_txt)
    for iso2 in sorted(cities["iso2"].unique()):
        jobs.append((f"GeoNames {iso2}", f"{GEONAMES}/{iso2}.zip", f"{RAW_DIR}/geonames/{iso2}.txt", True))
    jobs += [
        ("GeoNames feature codes", f"{GEONAMES}/featureCodes_en.txt", f"{RAW_DIR}/featureCodes_en.txt", False),
        ("GeoNames readme", f"{GEONAMES}/readme.txt", f"{RAW_DIR}/geonames_readme.txt", False),
        ("OpenFlights airports", f"{OPENFLIGHTS}/airports.dat", f"{RAW_DIR}/airports.dat", False),
        ("OpenFlights routes", f"{OPENFLIGHTS}/routes.dat", f"{RAW_DIR}/routes.dat", False),
        ("UNESCO World Heritage List", UNESCO_XML, f"{RAW_DIR}/unesco_whc.xml", False),
    ]

    failed = []
    for label, url, dest, is_zip in jobs:
        if os.path.exists(dest):
            continue
        try:
            content = _get(url)
            if is_zip:  # FR.zip contains FR.txt (and readme.txt) — we want only <ISO2>.txt
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    content = zf.read(os.path.basename(dest))
            _save(dest, content)
            print(f"  downloaded {label}")
        except Exception as e:  # report and carry on: one bad file shouldn't stop the rest
            failed.append((label, url, dest, str(e)))

    have = sum(os.path.exists(d) for _, _, d, _ in jobs)
    print(f"\n{have} of {len(jobs)} files are in data/raw/.")
    if failed:
        print("\nCould not download these — open the URL in a browser and save it at the path shown:")
        for label, url, dest, err in failed:
            print(f"  {label}\n    URL : {url}\n    SAVE: {os.path.relpath(dest, os.path.join(DATA_DIR, '..'))}   ({err})")
            if dest.endswith("unesco_whc.xml"):
                print("    (On the UNESCO page use the download/export option for the full list — XML or "
                      "Excel; save Excel/CSV as unesco_whc.xlsx / unesco_whc.csv instead.)")
    else:
        print("Next: python src/fetch_airports.py && python src/build_culture.py")


if __name__ == "__main__":
    main()
