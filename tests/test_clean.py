"""Every cleaning rule, tested against both engines with the same expectations.

If pandas and Polars ever disagree, one of these tests fails for one engine and passes
for the other, which tells you exactly where to look.
"""

from datetime import UTC, datetime

import pytest


@pytest.fixture(params=["pandas", "polars"])
def clean(request):
    """The cleaning module for each engine in turn."""
    if request.param == "polars":
        pytest.importorskip("polars")
        from airquality.transform import clean_polars

        return clean_polars
    from airquality.transform import clean_pandas

    return clean_pandas


def rows(table) -> list[dict]:
    """Rows as dictionaries, whichever library produced the table."""
    if hasattr(table, "to_dicts"):
        return table.to_dicts()
    return table.to_dict("records")


def reading(**changes) -> dict:
    base = {
        "sensor_id": 101,
        "location_id": 1,
        "parameter": "pm25",
        "units": "µg/m³",
        "measured_at": "2026-11-08T16:00:00Z",
        "value": 412.0,
    }
    return base | changes


def test_air_quality_keeps_a_good_reading_as_utc(clean):
    result = rows(clean.clean_air_quality([reading()]))
    assert len(result) == 1
    assert result[0]["value"] == 412.0
    assert result[0]["measured_at"] == datetime(2026, 11, 8, 16, 0, tzinfo=UTC)


def test_air_quality_drops_readings_that_cannot_be_real(clean):
    records = [
        reading(sensor_id=1, value=-999),  # instrument error code
        reading(sensor_id=2, value=5000),  # above the instrument's range
        reading(sensor_id=3, value=None),  # missing
        reading(sensor_id=4, measured_at="not a date"),
        reading(sensor_id=5, parameter="so2"),  # a pollutant we do not track
        reading(sensor_id=6, value=88.5),  # the only good one
    ]
    result = rows(clean.clean_air_quality(records))
    assert [row["sensor_id"] for row in result] == [6]


def test_air_quality_keeps_the_last_of_two_duplicates(clean):
    records = [reading(value=100.0), reading(value=120.0)]
    result = rows(clean.clean_air_quality(records))
    assert [row["value"] for row in result] == [120.0]


def test_air_quality_accepts_no_records(clean):
    assert len(clean.clean_air_quality([])) == 0


def test_weather_renames_columns_and_drops_forecast_hours(clean):
    records = [
        {"time": "2026-11-08T10:00", "temperature_2m": 24.1, "wind_speed_10m": 3},
        {"time": "2026-11-08T11:00", "temperature_2m": 25.0, "wind_speed_10m": 4},
        {"time": "2026-11-08T15:00", "temperature_2m": 22.0, "wind_speed_10m": 6},  # future
    ]
    now = datetime(2026, 11, 8, 12, 0, tzinfo=UTC)
    result = rows(clean.clean_weather(records, now=now))
    assert len(result) == 2
    assert result[0]["measured_at"] == datetime(2026, 11, 8, 10, 0, tzinfo=UTC)
    assert result[0]["temperature_c"] == 24.1
    assert result[1]["wind_speed_kmh"] == 4.0
    assert "boundary_layer_height_m" in result[0]


def fire(**changes) -> dict:
    base = {
        "latitude": "30.512",
        "longitude": "75.204",
        "acq_date": "2026-11-05",
        "acq_time": "812",
        "satellite": "N20",
        "confidence": "n",
        "frp": "4.2",
        "daynight": "D",
    }
    return base | changes


def test_fires_builds_one_timestamp_from_date_and_time(clean):
    result = rows(clean.clean_fires([fire(), fire(latitude="30.9", acq_time="30")]))
    stamps = sorted(row["detected_at"] for row in result)
    assert stamps == [
        datetime(2026, 11, 5, 0, 30, tzinfo=UTC),
        datetime(2026, 11, 5, 8, 12, tzinfo=UTC),
    ]


def test_fires_drops_low_confidence_and_duplicates(clean):
    records = [fire(), fire(), fire(latitude="31.0", confidence="l")]
    result = rows(clean.clean_fires(records))
    assert len(result) == 1
    assert result[0]["frp_mw"] == 4.2
    assert result[0]["day_night"] == "D"
