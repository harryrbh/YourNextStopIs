"""Offline tests for the fetch scripts' parsing and the retry helper (no network)."""
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import fetchWeather
import httpClient


def testWeatherParserGives12MonthsOfMonthlyTotals():
    payload = {"properties": {"parameter": {
        "T2M": {month: 10.0 for month in fetchWeather.monthKeys},
        "PRECTOTCORR": {month: 2.0 for month in fetchWeather.monthKeys}}}}
    monthlyTable = fetchWeather.parseClimatology("X", payload)
    assert len(monthlyTable) == 12
    assert monthlyTable.loc[monthlyTable["month"] == 1, "precipitation_mm"].iloc[0] == 62.0  # 2 mm/day x 31 days


def testWeatherParserRejectsMissingMonth():
    payload = {"properties": {"parameter": {
        "T2M": {month: 10.0 for month in fetchWeather.monthKeys},
        "PRECTOTCORR": {month: -999 for month in fetchWeather.monthKeys}}}}
    with pytest.raises(ValueError):
        fetchWeather.parseClimatology("X", payload)


class FakeResponse:
    def __init__(self, status, body=None):
        self.status_code, self._body, self.headers = status, body or {}, {}
    def json(self): return self._body
    def raise_for_status(self): raise requests.HTTPError(str(self.status_code))


def test429IsRetriedInPlaceUntilSuccess(monkeypatch):
    responses = iter([FakeResponse(429), FakeResponse(429), FakeResponse(200, {"ok": 1})])
    monkeypatch.setattr(httpClient.requests, "get", lambda *args, **kwargs: next(responses))
    waits = []
    assert httpClient.getJson("http://x", sleep=waits.append) == {"ok": 1}
    assert len(waits) == 2


def testGivesUpAfterMaximumAttempts(monkeypatch):
    monkeypatch.setattr(httpClient.requests, "get", lambda *args, **kwargs: FakeResponse(429))
    with pytest.raises(httpClient.RequestFailed):
        httpClient.getJson("http://x", maximumAttempts=3, sleep=lambda seconds: None)
