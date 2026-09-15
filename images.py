"""
images.py — fetches a representative photo for a city from Wikipedia.
No API key needed.

Wikipedia's REST "page summary" endpoint returns basic facts about an
article, including a thumbnail image if the article has one — we only
use the thumbnail.

Two things that are easy to get wrong here, and matter a lot:

1. Wikimedia's API etiquette REQUIRES a descriptive User-Agent header
   on every request — requests without one are routinely throttled or
   blocked (403), especially from data-centre / cloud IP addresses.
   This is very likely the reason a photo feature "doesn't work" even
   though the code looks fine: silently missing images, not an error.
2. City names need URL-encoding (spaces, accents, parentheses like in
   "Bali (Denpasar)") before going into the URL path.

This makes a real network request, cached so we only ask once per
city per session. If it fails for any reason (no internet, no such
article, article has no image), it returns None and the app shows a
plain card instead of an image — never an error.
"""
import urllib.parse

import requests
import streamlit as st

WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

# Wikimedia asks every API client to identify itself. Replace the
# email with your own if you fork this project — see
# https://meta.wikimedia.org/wiki/User-Agent_policy
HEADERS = {
    "User-Agent": "CityBreaksStudentProject/1.0 (https://example.com; contact@example.com)"
}


def _fetch_summary(title: str) -> dict | None:
    url = WIKIPEDIA_SUMMARY_URL.format(title=urllib.parse.quote(title.replace(" ", "_")))
    try:
        response = requests.get(url, headers=HEADERS, timeout=6)
        if response.status_code != 200:
            return None
        return response.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=60 * 60 * 24)  # a city's photo doesn't change day to day
def get_city_image_url(city_name: str, country_name: str = "") -> str | None:
    # Some city names are ambiguous on Wikipedia (e.g. many towns
    # called "Springfield"), and a couple in our sample data have
    # parenthetical disambiguators ("Bali (Denpasar)") that don't
    # match a real article title. Try the plain name first, then fall
    # back to "City, Country" if that didn't return a usable photo.
    for title in (city_name, f"{city_name}, {country_name}" if country_name else None):
        if not title:
            continue
        data = _fetch_summary(title)
        if not data:
            continue
        if data.get("type") == "disambiguation":
            continue
        thumbnail = data.get("thumbnail")
        if thumbnail and thumbnail.get("source"):
            return thumbnail["source"]
    return None
