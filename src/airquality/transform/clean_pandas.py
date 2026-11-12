"""Cleaning rules in pandas. clean_polars.py holds the same rules in Polars."""

from datetime import datetime

import pandas as pd

from airquality import config
from airquality.transform import (
    AIR_COLUMNS,
    FIRE_COLUMNS,
    FIRE_KEY,
    FIRE_RAW_COLUMNS,
    WEATHER_COLUMNS,
    WEATHER_RENAME,
)


def clean_air_quality(records: list[dict]) -> pd.DataFrame:
    """Typed, de-duplicated hourly readings with impossible values removed."""
    df = pd.DataFrame(records, columns=AIR_COLUMNS)
    df["measured_at"] = pd.to_datetime(df["measured_at"], utc=True, errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["measured_at", "value"])

    # One row of limits per pollutant, joined on. Pollutants we do not track drop out.
    limits = pd.DataFrame(
        [
            {"parameter": name, "min_ok": low, "max_ok": high}
            for name, (low, high) in config.VALID_RANGE.items()
        ]
    )
    df = df.merge(limits, on="parameter", how="inner")
    df = df[df["value"].between(df["min_ok"], df["max_ok"])]

    return (
        df.drop(columns=["min_ok", "max_ok"])
        .drop_duplicates(subset=["sensor_id", "measured_at"], keep="last")
        .sort_values(["sensor_id", "measured_at"])
        .reset_index(drop=True)
    )


def clean_weather(records: list[dict], now: datetime | None = None) -> pd.DataFrame:
    """Hourly weather with our column names. Forecast hours after `now` are dropped."""
    df = pd.DataFrame(records).rename(columns=WEATHER_RENAME).reindex(columns=WEATHER_COLUMNS)
    df["measured_at"] = pd.to_datetime(df["measured_at"], utc=True, errors="coerce")
    value_columns = [name for name in WEATHER_COLUMNS if name != "measured_at"]
    df[value_columns] = df[value_columns].apply(pd.to_numeric, errors="coerce")

    now = now or pd.Timestamp.now(tz="UTC")
    df = df[df["measured_at"].notna() & (df["measured_at"] <= now)]
    df = df.dropna(subset=value_columns, how="all")

    return (
        df.drop_duplicates(subset=["measured_at"], keep="last")
        .sort_values("measured_at")
        .reset_index(drop=True)
    )


def clean_fires(records: list[dict]) -> pd.DataFrame:
    """Fire detections with one UTC timestamp, low-confidence detections removed."""
    df = pd.DataFrame(records, columns=FIRE_RAW_COLUMNS)

    # FIRMS splits the moment into a date and an HHMM time that loses its
    # leading zeros: 08:12 arrives as "812". Pad it back, then parse.
    stamp = df["acq_date"].astype("string") + " " + df["acq_time"].astype("string").str.zfill(4)
    df["detected_at"] = pd.to_datetime(stamp, format="%Y-%m-%d %H%M", utc=True, errors="coerce")

    for column in ("latitude", "longitude", "frp"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["confidence"] = df["confidence"].astype("string").str.lower().str[0]

    df = df.dropna(subset=["latitude", "longitude", "detected_at"])
    df = df[df["confidence"].isin(["n", "h"])]  # nominal and high
    df = df.rename(columns={"frp": "frp_mw", "daynight": "day_night"})

    return (
        df[FIRE_COLUMNS]
        .drop_duplicates(subset=FIRE_KEY, keep="last")
        .sort_values("detected_at")
        .reset_index(drop=True)
    )
