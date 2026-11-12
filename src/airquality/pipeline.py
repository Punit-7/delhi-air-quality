"""Command line entry point. Each sub-command is one job a scheduler can run.

python -m airquality.pipeline air-quality --hours 6
python -m airquality.pipeline weather --days 2
python -m airquality.pipeline fires --days 2
python -m airquality.pipeline backfill --days 40
python -m airquality.pipeline dbt build

To clean with Polars instead of pandas, put --engine polars before the job:
python -m airquality.pipeline --engine polars weather --days 2
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from airquality import config

log = logging.getLogger("airquality.pipeline")


def run_air_quality(hours: int, engine_name: str) -> None:
    from airquality.extract import openaq
    from airquality.load import postgres

    end = datetime.now(UTC)
    stations = openaq.fetch_stations()
    records = openaq.fetch_hourly(stations, end - timedelta(hours=hours), end)
    _land_raw("openaq", records)

    cleaned = _cleaner(engine_name).clean_air_quality(records)
    _check("air quality", records, cleaned)

    engine = postgres.get_engine()
    station_rows = [
        {name: station[name] for name in ("location_id", "station_name", "latitude", "longitude")}
        for station in stations
    ]
    postgres.upsert(station_rows, "stations", ["location_id"], engine)
    postgres.upsert(cleaned, "air_quality_hourly", ["sensor_id", "measured_at"], engine)


def run_weather(days: int, engine_name: str) -> None:
    from airquality.extract import weather
    from airquality.load import postgres

    records = weather.fetch_hourly(past_days=days)
    _land_raw("weather", records)

    cleaned = _cleaner(engine_name).clean_weather(records)
    _check("weather", records, cleaned)
    postgres.upsert(cleaned, "weather_hourly", ["measured_at"], postgres.get_engine())


def run_fires(days: int, engine_name: str) -> None:
    from airquality.extract import fires
    from airquality.load import postgres
    from airquality.transform import FIRE_KEY

    records = fires.fetch_detections(days=days)
    _land_raw("fires", records)

    cleaned = _cleaner(engine_name).clean_fires(records)
    log.info("fires: %d raw rows, %d after cleaning", len(records), len(cleaned))
    postgres.upsert(cleaned, "fire_detections", FIRE_KEY, postgres.get_engine())


def run_dbt(arguments: list[str]) -> int:
    """Run dbt with the settings from .env, from any folder."""
    command = [
        "dbt",
        *arguments,
        "--project-dir",
        str(config.DBT_DIR),
        "--profiles-dir",
        str(config.DBT_DIR),
    ]
    return subprocess.run(command, check=False).returncode


def _cleaner(engine_name: str):
    """Pick the module that holds the cleaning functions."""
    if engine_name == "polars":
        from airquality.transform import clean_polars

        return clean_polars
    from airquality.transform import clean_pandas

    return clean_pandas


def _land_raw(source: str, records: list[dict]) -> Path:
    """Keep an untouched copy of what the API sent, so any run can be replayed."""
    folder = config.RAW_DIR / source
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}.json"
    path.write_text(json.dumps(records, default=str), encoding="utf-8")
    return path


def _check(source: str, records: list[dict], cleaned) -> None:
    """Stop the run when cleaning throws away everything: that means a format changed."""
    log.info("%s: %d raw rows, %d after cleaning", source, len(records), len(cleaned))
    if records and len(cleaned) == 0:
        raise RuntimeError(
            f"{source}: cleaning removed every row. Open the newest file in "
            f"{config.RAW_DIR} and compare it with what the cleaning code expects."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Delhi air quality pipeline")
    parser.add_argument(
        "--engine",
        choices=["pandas", "polars"],
        default=os.getenv("CLEAN_ENGINE", "pandas"),
        help="library used for cleaning (default: pandas)",
    )
    jobs = parser.add_subparsers(dest="job", required=True)

    air = jobs.add_parser("air-quality", help="extract, clean and load pollutant readings")
    air.add_argument("--hours", type=int, default=6)
    weather = jobs.add_parser("weather", help="extract, clean and load weather")
    weather.add_argument("--days", type=int, default=2)
    fires = jobs.add_parser("fires", help="extract, clean and load fire detections")
    fires.add_argument("--days", type=int, default=2)
    backfill = jobs.add_parser("backfill", help="load history for all three sources")
    backfill.add_argument("--days", type=int, default=40)
    dbt = jobs.add_parser("dbt", help="run a dbt command, for example: dbt build")
    dbt.add_argument("dbt_arguments", nargs=argparse.REMAINDER)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    if args.job == "air-quality":
        run_air_quality(args.hours, args.engine)
    elif args.job == "weather":
        run_weather(args.days, args.engine)
    elif args.job == "fires":
        run_fires(args.days, args.engine)
    elif args.job == "backfill":
        run_weather(args.days, args.engine)
        run_fires(args.days, args.engine)
        run_air_quality(args.days * 24, args.engine)
    elif args.job == "dbt":
        return run_dbt(args.dbt_arguments)
    return 0


if __name__ == "__main__":
    sys.exit(main())
