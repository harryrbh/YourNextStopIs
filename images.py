"""
images.py — fetches a representative photo for a city from Wikipedia.
No API key needed.

Wikipedia's REST "page summary" endpoint returns basic facts about an
article, including a thumbnail image if the article has one — we only
use the thumbnail.

This makes a real network request, cached so we only ask once per
city per session. If it fails (no internet, city not found, article
has no image), it returns None and the app shows a plain card
instead of an image — never an error.
"""
import requests
import streamlit as st

WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"


@st.cache_data(ttl=60 * 60 * 24)  # a city's photo doesn't change day to day
def get_city_image_url(city_name: str, country_name: str = "") -> str | None:
    # Some city names are ambiguous on Wikipedia (e.g. many towns
    # called "Springfield") — adding the country usually disambiguates.
    title = city_name.replace(" ", "_")
    try:
        response = requests.get(WIKIPEDIA_SUMMARY_URL.format(title=title), timeout=5)
        if response.status_code != 200:
            return None
        data = response.json()
        thumbnail = data.get("thumbnail")
        return thumbnail["source"] if thumbnail else None
    except requests.RequestException:
        return None
