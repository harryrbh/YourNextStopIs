"""Offline tests for the fetch scripts' parsing and the retry helper (no network)."""
import sys
from pathlib import Path

import pytest
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import fetch_weather
import http_util


def test_weather_parser_gives_12_months_of_monthly_totals():
    payload = {"properties": {"parameter": {
        "T2M": {m: 10.0 for m in fetch_weather.MONTHS},
        "PRECTOTCORR": {m: 2.0 for m in fetch_weather.MONTHS}}}}
    df = fetch_weather.parse_climatology("X", payload)
    assert len(df) == 12
    assert df.loc[df["month"] == 1, "precipitation_mm"].iloc[0] == 62.0  # 2 mm/day x 31 days


def test_weather_parser_rejects_missing_month():
    payload = {"properties": {"parameter": {
        "T2M": {m: 10.0 for m in fetch_weather.MONTHS},
        "PRECTOTCORR": {m: -999 for m in fetch_weather.MONTHS}}}}
    with pytest.raises(ValueError):
        fetch_weather.parse_climatology("X", payload)


class _Resp:
    def __init__(self, status, body=None):
        self.status_code, self._body, self.headers = status, body or {}, {}
    def json(self): return self._body
    def raise_for_status(self): raise requests.HTTPError(str(self.status_code))


def test_429_is_retried_in_place_until_success(monkeypatch):
    responses = iter([_Resp(429), _Resp(429), _Resp(200, {"ok": 1})])
    monkeypatch.setattr(http_util.requests, "get", lambda *a, **k: next(responses))
    waits = []
    assert http_util.get_json("http://x", sleep=waits.append) == {"ok": 1}
    assert len(waits) == 2


def test_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(http_util.requests, "get", lambda *a, **k: _Resp(429))
    with pytest.raises(http_util.RequestFailed):
        http_util.get_json("http://x", max_attempts=3, sleep=lambda s: None)
