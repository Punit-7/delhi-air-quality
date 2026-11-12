"""The one place that talks to the network: timeouts, retries, polite waiting."""

import logging
import time

import requests

log = logging.getLogger(__name__)

RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_WAIT_SECONDS = 90


def get(
    url: str,
    *,
    label: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 30,
    attempts: int = 4,
) -> requests.Response:
    """GET a URL, retrying on rate limits and temporary server errors.

    `label` is what appears in the logs. The URL itself is never logged,
    because some APIs carry the key inside it.
    """
    for attempt in range(1, attempts + 1):
        last_try = attempt == attempts
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout):
            if last_try:
                raise RuntimeError(f"{label}: network error after {attempts} attempts") from None
            _pause(label, attempt, 2**attempt)
            continue

        if response.status_code not in RETRY_STATUS:
            if response.status_code >= 400:
                raise RuntimeError(f"{label}: request failed with status {response.status_code}")
            return response

        if last_try:
            raise RuntimeError(f"{label}: still failing with status {response.status_code}")
        _pause(label, attempt, _suggested_wait(response, attempt))

    raise AssertionError("unreachable")


def _suggested_wait(response: requests.Response, attempt: int) -> float:
    """Use the server's own advice when it gives any, otherwise back off."""
    advice = response.headers.get("x-ratelimit-reset") or response.headers.get("retry-after")
    try:
        return min(float(advice), MAX_WAIT_SECONDS)
    except (TypeError, ValueError):
        return 2**attempt


def _pause(label: str, attempt: int, seconds: float) -> None:
    log.warning("%s: attempt %d failed, waiting %.0f s", label, attempt, seconds)
    time.sleep(seconds)
