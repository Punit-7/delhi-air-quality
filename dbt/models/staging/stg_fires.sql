-- One row per satellite detection, with the calendar day it fell on in India.
select
    latitude,
    longitude,
    detected_at,
    (detected_at at time zone '{{ var("local_timezone") }}')::date as fire_date,
    satellite,
    confidence,
    frp_mw,
    day_night
from {{ source('raw', 'fire_detections') }}
