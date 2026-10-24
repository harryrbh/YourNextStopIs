"""One shared, careful way to call rate-limited public APIs."""
import random
import time

import requests

retryableStatus = {429, 500, 502, 503, 504}


class RequestFailed(RuntimeError):
    """Raised when a request still fails after every retry."""


class Throttle:

    def __init__(self, minimumInterval: float = 1.0, maximumInterval: float = 30.0):
        self.base = minimumInterval
        self.interval = minimumInterval
        self.maximumInterval = maximumInterval
        self._last = 0.0

    def wait(self):
        remaining = self.interval - (time.monotonic() - self._last)
        if remaining > 0:
            time.sleep(remaining)
        self._last = time.monotonic()

    def slowDown(self):
        self.interval = min(self.maximumInterval, self.interval * 1.5)

    def speedUp(self):
        self.interval = max(self.base, self.interval * 0.95)


def _retryAfterSeconds(response: requests.Response) -> float | None:
    retryAfterHeader = response.headers.get("Retry-After")
    if retryAfterHeader is None:
        return None
    try:
        return max(0.0, float(retryAfterHeader))
    except ValueError:
        return None  # HTTP-date form: ignore and use our own backoff


def getJson(
    url: str,
    params: dict | None = None,
    *,
    headers: dict | None = None,
    throttle: Throttle | None = None,
    maximumAttempts: int = 8,
    baseDelay: float = 5.0,
    maximumDelay: float = 300.0,
    timeout: float = 60.0,
    sleep=time.sleep,
    label: str = "",
):
    """GET `url` and return parsed JSON, retrying transient failures in place."""
    throttle = throttle or Throttle(0.0)
    lastProblem = "no attempt made"

    for attempt in range(1, maximumAttempts + 1):
        throttle.wait()
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        except (requests.Timeout, requests.ConnectionError) as error:
            lastProblem = f"{type(error).__name__}: {error}"
            retryAfter = None
        else:
            if response.status_code == 200:
                throttle.speedUp()
                return response.json()
            if response.status_code not in retryableStatus:
                response.raise_for_status()  # 400/403/404...: retrying won't help
            lastProblem = f"HTTP {response.status_code}"
            retryAfter = _retryAfterSeconds(response)

        if attempt == maximumAttempts:
            break
        throttle.slowDown()
        delay = retryAfter if retryAfter is not None else min(maximumDelay, baseDelay * 2 ** (attempt - 1))
        delay += random.uniform(0, 1.0)
        print(f"    {label or url}: {lastProblem} — waiting {delay:.0f}s "
              f"(attempt {attempt}/{maximumAttempts})")
        sleep(delay)

    raise RequestFailed(f"{label or url}: gave up after {maximumAttempts} attempts ({lastProblem})")
