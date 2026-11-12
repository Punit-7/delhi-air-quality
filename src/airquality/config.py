"""Every setting the pipeline needs, in one place.

No other module reads environment variables or hard-codes a coordinate.
When a number changes, it changes here and nowhere else.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Reads .env on your computer. Inside Docker there is no .env file and the
# variables are already set, so this line quietly does nothing there.
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
DBT_DIR = PROJECT_ROOT / "dbt"

# --- Air quality -----------------------------------------------------------
DELHI_LAT = 28.6139
DELHI_LON = 77.2090
SEARCH_RADIUS_M = 25_000  # the largest radius OpenAQ accepts
PARAMETERS = ("pm25", "pm10", "no2")
STATION_MAX_AGE_DAYS = 7  # ignore stations that stopped reporting

# Readings outside these limits are instrument faults, not air.
# Set them from what you saw in the exploration notebook.
VALID_RANGE = {
    "pm25": (0.0, 1000.0),
    "pm10": (0.0, 2000.0),
    "no2": (0.0, 1000.0),
}

# --- Farm fires ------------------------------------------------------------
# west, south, east, north: a box around Punjab and Haryana
FIRE_BBOX = (73.8, 27.6, 77.7, 32.6)
FIRMS_SOURCE = "VIIRS_NOAA20_NRT"
FIRMS_MAX_DAYS = 5  # the most days one request may cover

LOCAL_TZ = "Asia/Kolkata"


def require_env(name: str) -> str:
    """Return an environment variable, or stop with a message that says how to fix it."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not set. Add it to {PROJECT_ROOT / '.env'}")
    return value
