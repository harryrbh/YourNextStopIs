"""
http_util.py — one shared, careful way to call rate-limited public APIs.

WHY THIS EXISTS
------------------------------------------------------------------
The old fetch_weather.py retried in ROUNDS: send every batch once, collect
the ones that got a 429 (Too Many Requests), wait, then send every failed
batch again... capped at 4 rounds. Once the API started rejecting us,
each round could only get roughly ONE request through before the rest
were rejected again — so 4 rounds meant ~4 batches in total, no matter
how many were needed.

The fix is to retry each request IN PLACE, and to slow the *whole run
down* when the server pushes back:

  * a 429 (or 5xx / timeout / dropped connection) makes THAT request wait
    and try again — it never gets abandoned just because it was unlucky
    once;
  * if the server sends a Retry-After header, we obey it exactly;
    otherwise we back off exponentially (with a little random jitter);
  * the Throttle spaces requests out, and permanently widens the gap
    after every 429 (then slowly narrows it again after successes), so we
    settle at whatever pace the server will actually tolerate.
"""
import random
import time

import requests

RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class RequestFailed(RuntimeError):
    """Raised when a request still fails after every retry."""


class Throttle:
    """Enforces a minimum gap between requests, and adapts it: every
    rate-limit response widens the gap, every success narrows it a bit."""

    def __init__(self, min_interval: float = 1.0, max_interval: float = 30.0):
        self.base = min_interval
        self.interval = min_interval
        self.max_interval = max_interval
        self._last = 0.0

    def wait(self):
        remaining = self.interval - (time.monotonic() - self._last)
        if remaining > 0:
            time.sleep(remaining)
        self._last = time.monotonic()

    def slow_down(self):
        self.interval = min(self.max_interval, self.interval * 1.5)

    def speed_up(self):
        self.interval = max(self.base, self.interval * 0.95)


def _retry_after_seconds(response: requests.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None  # HTTP-date form: ignore and use our own backoff


def get_json(
    url: str,
    params: dict | None = None,
    *,
    headers: dict | None = None,
    throttle: Throttle | None = None,
    max_attempts: int = 8,
    base_delay: float = 5.0,
    max_delay: float = 300.0,
    timeout: float = 60.0,
    sleep=time.sleep,
    label: str = "",
):
    """GET `url` and return parsed JSON, retrying transient failures in place.
    Raises RequestFailed only after `max_attempts` genuine attempts."""
    throttle = throttle or Throttle(0.0)
    last_problem = "no attempt made"

    for attempt in range(1, max_attempts + 1):
        throttle.wait()
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        except (requests.Timeout, requests.ConnectionError) as e:
            last_problem = f"{type(e).__name__}: {e}"
            retry_after = None
        else:
            if response.status_code == 200:
                throttle.speed_up()
                return response.json()
            if response.status_code not in RETRYABLE_STATUS:
                response.raise_for_status()  # 400/403/404...: retrying won't help
            last_problem = f"HTTP {response.status_code}"
            retry_after = _retry_after_seconds(response)

        if attempt == max_attempts:
            break
        throttle.slow_down()
        delay = retry_after if retry_after is not None else min(max_delay, base_delay * 2 ** (attempt - 1))
        delay += random.uniform(0, 1.0)
        print(f"    {label or url}: {last_problem} — waiting {delay:.0f}s "
              f"(attempt {attempt}/{max_attempts})")
        sleep(delay)

    raise RequestFailed(f"{label or url}: gave up after {max_attempts} attempts ({last_problem})")
