"""Hourly weather for central Delhi, from Open-Meteo. No API key needed."""

import logging

from airquality import config
from airquality.extract._http import get

log = logging.getLogger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "precipitation",
    "boundary_layer_height",
)
MAX_PAST_DAYS = 92


def fetch_hourly(past_days: int) -> list[dict]:
    """One record per hour for the last `past_days` days, plus today."""
    payload = get(
        BASE_URL,
        label="Open-Meteo weather",
        params={
            "latitude": config.DELHI_LAT,
            "longitude": config.DELHI_LON,
            "hourly": ",".join(HOURLY_VARIABLES),
            "past_days": min(past_days, MAX_PAST_DAYS),
            "forecast_days": 1,
            "timezone": "GMT",
        },
    ).json()

    # The API answers column by column: {"time": [...], "temperature_2m": [...]}.
    # Turn that into one dictionary per hour.
    hourly = payload["hourly"]
    records = [
        dict(zip(hourly.keys(), row, strict=True))
        for row in zip(*hourly.values(), strict=True)
    ]
    log.info("Open-Meteo: %d hourly records", len(records))
    return records
