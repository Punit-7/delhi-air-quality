"""Satellite fire detections over Punjab and Haryana, from NASA FIRMS."""

import csv
import io
import logging
from datetime import UTC, date, datetime, timedelta

from airquality import config
from airquality.extract._http import get

log = logging.getLogger(__name__)

BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
KEEP = (
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "satellite",
    "confidence",
    "frp",
    "daynight",
)


def fetch_detections(days: int, end_date: date | None = None) -> list[dict]:
    """Fire detections for the `days` days that end on `end_date` (default: today, UTC).

    FIRMS serves only a few days per request, so longer periods are fetched in chunks.
    """
    key = config.require_env("FIRMS_MAP_KEY")
    bbox = ",".join(str(edge) for edge in config.FIRE_BBOX)
    end_date = end_date or datetime.now(UTC).date()
    chunk_start = end_date - timedelta(days=days - 1)

    records: list[dict] = []
    while chunk_start <= end_date:
        span = min(config.FIRMS_MAX_DAYS, (end_date - chunk_start).days + 1)
        # The key sits inside the URL, which is why _http.get never logs URLs.
        url = f"{BASE_URL}/{key}/{config.FIRMS_SOURCE}/{bbox}/{span}/{chunk_start.isoformat()}"
        text = get(url, label=f"FIRMS {chunk_start} +{span}d", timeout=60).text
        records.extend(_parse_csv(text))
        chunk_start += timedelta(days=span)

    log.info("FIRMS: %d fire detections over %d days", len(records), days)
    return records


def _parse_csv(text: str) -> list[dict]:
    """FIRMS reports problems as plain text with status 200, so check the header."""
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    if "latitude" not in first_line:
        raise RuntimeError(f"FIRMS did not return fire data. It said: {first_line[:80]!r}")
    return [{name: row.get(name) for name in KEEP} for row in csv.DictReader(io.StringIO(text))]
