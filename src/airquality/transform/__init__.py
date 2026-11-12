"""Transform: the same cleaning rules written twice, once in pandas and once in Polars.

The column names below are the contract with the database. Both engines must return
exactly these columns, which is what the tests check.
"""

AIR_COLUMNS = ["sensor_id", "location_id", "parameter", "units", "measured_at", "value"]

# Open-Meteo's names on the left, our warehouse names on the right.
WEATHER_RENAME = {
    "time": "measured_at",
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "relative_humidity_pct",
    "wind_speed_10m": "wind_speed_kmh",
    "wind_direction_10m": "wind_direction_deg",
    "precipitation": "precipitation_mm",
    "boundary_layer_height": "boundary_layer_height_m",
}
WEATHER_COLUMNS = list(WEATHER_RENAME.values())

FIRE_RAW_COLUMNS = [
    "latitude",
    "longitude",
    "acq_date",
    "acq_time",
    "satellite",
    "confidence",
    "frp",
    "daynight",
]
FIRE_COLUMNS = [
    "latitude",
    "longitude",
    "detected_at",
    "satellite",
    "confidence",
    "frp_mw",
    "day_night",
]
FIRE_KEY = ["latitude", "longitude", "detected_at", "satellite"]
