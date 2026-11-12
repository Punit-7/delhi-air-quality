"""Hourly pollutant readings for Delhi monitors, from the OpenAQ v3 API."""

import logging
import time
from datetime import UTC, datetime, timedelta

from airquality import config
from airquality.extract._http import get

log = logging.getLogger(__name__)

BASE_URL = "https://api.openaq.org/v3"
PAGE_SIZE = 1000
SECONDS_BETWEEN_CALLS = 1.1  # the free tier allows 60 requests a minute
MIN_TIME = datetime.min.replace(tzinfo=UTC)


def fetch_stations() -> list[dict]:
    """Reference monitors around Delhi that reported recently, each with its live sensors."""
    found: list[dict] = []
    page = 1
    while True:
        payload = get(
            f"{BASE_URL}/locations",
            label="OpenAQ locations",
            headers=_headers(),
            params={
                "coordinates": f"{config.DELHI_LAT},{config.DELHI_LON}",
                "radius": config.SEARCH_RADIUS_M,
                "limit": PAGE_SIZE,
                "page": page,
            },
        ).json()
        results = payload.get("results", [])
        found.extend(_parse_station(item) for item in results)
        if len(results) < PAGE_SIZE:
            break
        page += 1
        time.sleep(SECONDS_BETWEEN_CALLS)

    cutoff = datetime.now(UTC) - timedelta(days=config.STATION_MAX_AGE_DAYS)
    active = [
        station
        for station in found
        if station["is_monitor"]
        and station["last_seen"] is not None
        and station["last_seen"] >= cutoff
    ]
    for station in active:
        station["sensors"] = _live_sensors(station["location_id"])
        time.sleep(SECONDS_BETWEEN_CALLS)

    log.info("OpenAQ: %d of %d locations are active reference monitors", len(active), len(found))
    return [station for station in active if station["sensors"]]


def fetch_hourly(stations: list[dict], start: datetime, end: datetime) -> list[dict]:
    """Hourly averages for every sensor of every station between two UTC times."""
    records: list[dict] = []
    for station in stations:
        for sensor in station["sensors"]:
            records.extend(_fetch_sensor_hours(station, sensor, start, end))
            time.sleep(SECONDS_BETWEEN_CALLS)
    log.info("OpenAQ: %d hourly readings from %d stations", len(records), len(stations))
    return records


def _live_sensors(location_id: int) -> list[dict]:
    """One sensor per pollutant: the one that reported most recently.

    A location can keep old sensors next to a new one (step 3 found dead pm25 sensors
    from 2018), so the newest `datetimeLast` wins.
    """
    payload = get(
        f"{BASE_URL}/locations/{location_id}/sensors",
        label=f"OpenAQ sensors of location {location_id}",
        headers=_headers(),
    ).json()

    newest: dict[str, tuple[datetime, dict]] = {}
    for item in payload.get("results", []):
        parameter = item["parameter"]["name"]
        if parameter not in config.PARAMETERS:
            continue
        last = _parse_utc((item.get("datetimeLast") or {}).get("utc")) or MIN_TIME
        if parameter not in newest or last > newest[parameter][0]:
            newest[parameter] = (last, item)

    return [
        {
            "sensor_id": item["id"],
            "parameter": parameter,
            "units": item["parameter"].get("units"),
        }
        for parameter, (_, item) in newest.items()
    ]


def _fetch_sensor_hours(station: dict, sensor: dict, start: datetime, end: datetime) -> list[dict]:
    rows: list[dict] = []
    page = 1
    while True:
        payload = get(
            f"{BASE_URL}/sensors/{sensor['sensor_id']}/hours",
            label=f"OpenAQ sensor {sensor['sensor_id']}",
            headers=_headers(),
            params={
                "datetime_from": _iso(start),
                "datetime_to": _iso(end),
                "limit": PAGE_SIZE,
                "page": page,
            },
        ).json()
        results = payload.get("results", [])
        for item in results:
            rows.append(
                {
                    "sensor_id": sensor["sensor_id"],
                    "location_id": station["location_id"],
                    "parameter": sensor["parameter"],
                    "units": sensor["units"],
                    "measured_at": item["period"]["datetimeFrom"]["utc"],
                    "value": item.get("value"),
                }
            )
        if len(results) < PAGE_SIZE:
            return rows
        page += 1
        time.sleep(SECONDS_BETWEEN_CALLS)


def _parse_station(item: dict) -> dict:
    """Keep the handful of fields we use from one location in the API response."""
    coordinates = item.get("coordinates") or {}
    last_seen = (item.get("datetimeLast") or {}).get("utc")
    return {
        "location_id": item["id"],
        "station_name": item.get("name") or f"Station {item['id']}",
        "provider": (item.get("provider") or {}).get("name"),
        "is_monitor": bool(item.get("isMonitor")),
        "latitude": coordinates.get("latitude"),
        "longitude": coordinates.get("longitude"),
        "last_seen": _parse_utc(last_seen),
    }


def _headers() -> dict:
    return {"X-API-Key": config.require_env("OPENAQ_API_KEY")}


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(text: str | None) -> datetime | None:
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))
