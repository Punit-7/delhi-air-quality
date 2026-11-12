select
    location_id,
    station_name,
    latitude,
    longitude
from {{ source('raw', 'stations') }}
