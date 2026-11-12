"""Time the pandas and Polars cleaners on the same synthetic readings.

python scripts/compare_engines.py            # 500,000 rows
python scripts/compare_engines.py 2000000    # pick your own size

Readings shaped like the OpenAQ extract, with realistic mess mixed in.
"""

import random
import sys
import time
from datetime import UTC, datetime, timedelta


def make_records(count: int, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    start = datetime(2026, 10, 1, tzinfo=UTC)
    records = []
    for i in range(count):
        sensor = rng.randrange(120)
        value = rng.lognormvariate(4.6, 0.7)
        roll = rng.random()
        if roll < 0.01:
            value = -999.0  # instrument error code
        elif roll < 0.02:
            value = None  # gap
        records.append(
            {
                "sensor_id": sensor,
                "location_id": sensor // 3,
                "parameter": ("pm25", "pm10", "no2")[sensor % 3],
                "units": "µg/m³",
                "measured_at": (start + timedelta(hours=i % 960)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "value": value,
            }
        )
    return records


def best_of(function, records: list[dict], repeats: int = 3) -> tuple[float, int]:
    """Fastest of a few runs, and the number of rows that came out."""
    timings = []
    rows = 0
    for _ in range(repeats):
        started = time.perf_counter()
        rows = len(function(records))
        timings.append(time.perf_counter() - started)
    return min(timings), rows


def main() -> None:
    from airquality.transform import clean_pandas, clean_polars

    count = int(sys.argv[1]) if len(sys.argv) > 1 else 500_000
    records = make_records(count)
    print(f"{count:,} raw readings\n")

    results = {
        "pandas": best_of(clean_pandas.clean_air_quality, records),
        "polars": best_of(clean_polars.clean_air_quality, records),
    }
    for name, (seconds, rows) in results.items():
        print(f"{name:<8}{seconds:>8.3f} s {rows:>10,} rows kept")

    if results["pandas"][1] != results["polars"][1]:
        print("\nThe engines kept different numbers of rows. Find out why before trusting either.")
    else:
        ratio = results["pandas"][0] / results["polars"][0]
        print(f"\nSame rows from both. pandas took {ratio:.1f}x as long as Polars.")


if __name__ == "__main__":
    main()
