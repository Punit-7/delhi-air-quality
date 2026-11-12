"""Cleaning rules in Polars. clean_pandas.py holds the same rules in pandas."""

from datetime import UTC, datetime

import polars as pl

from airquality import config
from airquality.transform import (
    FIRE_COLUMNS,
    FIRE_KEY,
    FIRE_RAW_COLUMNS,
    WEATHER_COLUMNS,
    WEATHER_RENAME,
)

AIR_SCHEMA = {
    "sensor_id": pl.Int64,
    "location_id": pl.Int64,
    "parameter": pl.String,
    "units": pl.String,
    "measured_at": pl.String,
    "value": pl.Float64,
}
WEATHER_SCHEMA = {
    raw_name: pl.String if raw_name == "time" else pl.Float64 for raw_name in WEATHER_RENAME
}
FIRE_SCHEMA = {name: pl.String for name in FIRE_RAW_COLUMNS}


def clean_air_quality(records: list[dict]) -> pl.DataFrame:
    """Typed, de-duplicated hourly readings with impossible values removed."""
    # One row of limits per pollutant, joined on. Pollutants we do not track drop out.
    limits = pl.DataFrame(
        [
            {"parameter": name, "min_ok": low, "max_ok": high}
            for name, (low, high) in config.VALID_RANGE.items()
        ],
        schema={"parameter": pl.String, "min_ok": pl.Float64, "max_ok": pl.Float64},
    )
    return (
        pl.DataFrame(records, schema=AIR_SCHEMA, strict=False)
        .lazy()
        .with_columns(
            pl.col("measured_at").str.to_datetime("%Y-%m-%dT%H:%M:%S%#z", strict=False),
        )
        .drop_nulls(["measured_at", "value"])
        # maintain_order keeps arrival order, so keep="last" below means "last received".
        .join(limits.lazy(), on="parameter", how="inner", maintain_order="left")
        .filter(pl.col("value").is_between(pl.col("min_ok"), pl.col("max_ok")))
        .drop("min_ok", "max_ok")
        .unique(subset=["sensor_id", "measured_at"], keep="last", maintain_order=True)
        .sort("sensor_id", "measured_at")
        .collect()
    )


def clean_weather(records: list[dict], now: datetime | None = None) -> pl.DataFrame:
    """Hourly weather with our column names. Forecast hours after `now` are dropped."""
    now = now or datetime.now(UTC)
    value_columns = [name for name in WEATHER_COLUMNS if name != "measured_at"]
    return (
        pl.DataFrame(records, schema=WEATHER_SCHEMA, strict=False)
        .lazy()
        .rename(WEATHER_RENAME)
        .with_columns(
            pl.col("measured_at")
            .str.to_datetime("%Y-%m-%dT%H:%M", strict=False)
            .dt.replace_time_zone("UTC"),
        )
        .filter(pl.col("measured_at").is_not_null() & (pl.col("measured_at") <= now))
        .filter(~pl.all_horizontal(pl.col(value_columns).is_null()))
        .unique(subset=["measured_at"], keep="last", maintain_order=True)
        .sort("measured_at")
        .collect()
    )


def clean_fires(records: list[dict]) -> pl.DataFrame:
    """Fire detections with one UTC timestamp, low-confidence detections removed."""
    return (
        pl.DataFrame(records, schema=FIRE_SCHEMA, strict=False)
        .lazy()
        .with_columns(
            # FIRMS splits the moment into a date and an HHMM time that loses its
            # leading zeros: 08:12 arrives as "812". Pad it back, then parse.
            (pl.col("acq_date") + " " + pl.col("acq_time").str.zfill(4))
            .str.to_datetime("%Y-%m-%d %H%M", strict=False)
            .dt.replace_time_zone("UTC")
            .alias("detected_at"),
            pl.col("latitude", "longitude").cast(pl.Float64, strict=False),
            pl.col("frp").cast(pl.Float64, strict=False).alias("frp_mw"),
            pl.col("confidence").str.to_lowercase().str.slice(0, 1),
            pl.col("daynight").alias("day_night"),
        )
        .drop_nulls(["latitude", "longitude", "detected_at"])
        .filter(pl.col("confidence").is_in(["n", "h"]))  # nominal and high
        .select(FIRE_COLUMNS)
        .unique(subset=FIRE_KEY, keep="last", maintain_order=True)
        .sort("detected_at")
        .collect()
    )
