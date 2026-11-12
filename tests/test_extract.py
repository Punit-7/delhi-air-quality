"""Offline checks for the extract helpers. No network: these run in CI and offline.

Run: python -m pytest tests/test_extract.py
"""

from datetime import UTC, date, datetime

import pytest

from airquality.extract import fires, openaq
from airquality.extract._http import _suggested_wait


def test_fires_csv_without_header_is_an_error():
    # FIRMS answers bad keys with plain text and status 200.
    with pytest.raises(RuntimeError, match="did not return fire data"):
        fires._parse_csv("Invalid MAP_KEY.")


def test_fires_csv_keeps_only_known_columns():
    text = "latitude,longitude,acq_date,acq_time,satellite,confidence,frp,daynight,extra\n" \
           "29.4,76.9,2026-11-08,658,N20,n,3.6,D,ignored\n"
    [row] = fires._parse_csv(text)
    assert row["acq_time"] == "658"  # kept as text, leading zeros not guessed
    assert "extra" not in row


def test_chunks_cover_the_whole_period(monkeypatch):
    # 12 days with a 5-day limit must come back as 3 requests: 5 + 5 + 2.
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url.rsplit("/", 2)[-2:])

        class Reply:
            text = "latitude,longitude,acq_date,acq_time,satellite,confidence,frp,daynight\n"

        return Reply()

    monkeypatch.setenv("FIRMS_MAP_KEY", "test-key")
    monkeypatch.setattr(fires, "get", fake_get)
    fires.fetch_detections(days=12, end_date=date(2026, 11, 12))
    assert [span for span, _ in calls] == ["5", "5", "2"]
    assert calls[0][1] == "2026-11-01"  # 12 days ending 12 Nov, inclusive, starts 1 Nov


def test_live_sensor_wins_over_dead_one(monkeypatch):
    payload = {"results": [
        {"id": 35, "parameter": {"name": "pm25", "units": "µg/m³"},
         "datetimeLast": {"utc": "2018-02-21T21:15:00Z"}},
        {"id": 12234787, "parameter": {"name": "pm25", "units": "µg/m³"},
         "datetimeLast": {"utc": "2026-11-12T05:30:00Z"}},
        {"id": 9, "parameter": {"name": "o3", "units": "µg/m³"},
         "datetimeLast": {"utc": "2026-11-12T05:30:00Z"}},
    ]}

    class Reply:
        def json(self):
            return payload

    monkeypatch.setenv("OPENAQ_API_KEY", "test-key")
    monkeypatch.setattr(openaq, "get", lambda *a, **k: Reply())
    assert openaq._live_sensors(1) == [
        {"sensor_id": 12234787, "parameter": "pm25", "units": "µg/m³"},
    ]


def test_retry_wait_uses_server_advice_and_caps_it():
    class Resp:
        def __init__(self, header):
            self.headers = {"retry-after": header} if header else {}

    assert _suggested_wait(Resp("7"), attempt=1) == 7.0
    assert _suggested_wait(Resp("100000"), attempt=1) == 90  # capped
    assert _suggested_wait(Resp(None), attempt=3) == 8  # back off 2**attempt


def test_iso_time_is_utc_with_z():
    moment = datetime(2026, 11, 8, 12, 30, tzinfo=UTC)
    assert openaq._iso(moment) == "2026-11-08T12:30:00Z"
