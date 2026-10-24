"""Fetches a representative photo for a city from Wikipedia."""
import urllib.parse

import requests
import streamlit as st

wikipediaSummaryUrl = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

# Wikimedia asks every API client to identify itself
requestHeaders = {
    "User-Agent": "CityBreaksStudentProject/1.0 (https://example.com; contact@example.com)"
}


def _fetchSummary(title: str) -> dict | None:
    url = wikipediaSummaryUrl.format(title=urllib.parse.quote(title.replace(" ", "_")))
    try:
        response = requests.get(url, headers=requestHeaders, timeout=6)
        if response.status_code != 200:
            return None
        return response.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=60 * 60 * 24)  # A city's photo doesn't change day to day
def getCityImageUrl(cityName: str, countryName: str = "") -> str | None:
    # Retry with the country name for ambiguous city names
    for title in (cityName, f"{cityName}, {countryName}" if countryName else None):
        if not title:
            continue
        imageData = _fetchSummary(title)
        if not imageData:
            continue
        if imageData.get("type") == "disambiguation":
            continue
        thumbnail = imageData.get("thumbnail")
        if thumbnail and thumbnail.get("source"):
            return thumbnail["source"]
    return None
