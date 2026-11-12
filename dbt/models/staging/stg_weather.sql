select
    measured_at,
    temperature_c,
    relative_humidity_pct,
    wind_speed_kmh,
    wind_direction_deg,
    precipitation_mm,
    boundary_layer_height_m
from {{ source('raw', 'weather_hourly') }}
