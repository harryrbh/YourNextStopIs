"""
fetch_countries.py — replaces data/countries.csv with real country
data. No API key needed.

A NOTE ON WHICH API THIS USES, AND WHY
------------------------------------------------------------------
This originally used REST Countries (restcountries.com) v3.1, which
was genuinely free and keyless. As of 2026, REST Countries v1-v4 are
deprecated — the old endpoint now returns an error instead of data —
and the replacement, v5, requires creating an account and an API key
(a free tier exists, 500 requests/month, but it's no longer a
no-signup API). Since this project is specifically built so nobody
needs to create any accounts, this script now uses countries.dev
instead: a free, keyless API that returns equivalent country data
with a simpler, flatter JSON shape than REST Countries ever had.

IMPORTANT — I (the assistant who wrote this) verified countries.dev's
"list all countries" endpoint and response shape against its own live
documentation pages, but could not execute a real request against it
from the environment this code was written in (the same network
restriction that applies to every other API in this project — see
the other fetch_*.py docstrings). Run this script yourself and check
the output; if the shape has changed since, the error message below
will show you exactly what came back so you can fix the field names.

If you'd rather use the "official" REST Countries v5 (more
established, but needs a free account): sign up at
restcountries.com/sign-up, then change URL/FIELDS below to
"https://api.restcountries.com/countries/v5" and
"names.common,codes.alpha_2,region,population,geo.latitude,geo.longitude",
and add an "Authorization: Bearer YOUR_KEY" header to the request.

Run it with:
    python src/fetch_countries.py

This OVERWRITES data/countries.csv. If you want to keep comparing
against the sample data, copy the old file somewhere first.
"""
import os

import pandas as pd
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# `fields=` keeps the response small — we only ask for what we use.
URL = "https://countries.dev/countries"
FIELDS = "name,alpha2Code,region,population,latlng"


def fetch() -> list[dict]:
    print(f"Requesting {URL} ...")
    response = requests.get(URL, params={"fields": FIELDS}, timeout=30)
    response.raise_for_status()  # stop here with a clear error if the request failed
    data = response.json()

    # The API should return a JSON *list*, one object per country. If
    # something went wrong (a bad request, a rate limit, a temporary
    # error, or the API's shape has changed since this was written),
    # it may instead return a JSON *object* — and without this check,
    # the code below would silently iterate over that object's keys
    # as if they were countries and crash confusingly several calls
    # later. Catching it here means you see the server's own
    # explanation immediately instead.
    if not isinstance(data, list):
        raise RuntimeError(
            "The countries API didn't return the country list we expected. "
            f"Here's exactly what it sent back instead:\n\n{data}\n\n"
            "This usually means either a temporary problem with the API "
            "itself, or that its request format has changed since this "
            "script was written. Try opening this URL in your browser to "
            "see the current, live response:\n"
            f"{response.url}"
        )

    print(f"Got {len(data)} countries.")
    return data


def to_dataframe(raw: list[dict]) -> pd.DataFrame:
    rows = []
    for country in raw:
        latlng = country.get("latlng") or [None, None]
        rows.append(
            {
                "name": country.get("name"),
                "iso2": country.get("alpha2Code"),
                "region": country.get("region"),
                "population": country.get("population"),
                # Neither this API nor REST Countries includes GDP or
                # urbanisation — see NOTE below. fetch_tourism.py
                # fills both in later from the World Bank.
                "gdp_per_capita_usd": None,
                "urban_population_pct": None,
                "latitude": latlng[0] if len(latlng) > 0 else None,
                "longitude": latlng[1] if len(latlng) > 1 else None,
            }
        )
    return pd.DataFrame(rows)


def main():
    raw = fetch()
    df = to_dataframe(raw)

    out_path = f"{DATA_DIR}/countries.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} rows to {out_path}")
    print(
        "\nNOTE: this API doesn't provide GDP per capita or urban "
        "population %, so both columns are empty for every row. "
        "src/build_features.py fills missing GDP with the median so the "
        "pipeline still runs, but cost_score will be meaningless until you "
        "run fetch_tourism.py next — that script fills both columns in "
        "from the World Bank."
    )


if __name__ == "__main__":
    main()
