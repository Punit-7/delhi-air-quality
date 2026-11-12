-- One row per monitoring station, with the period it has data for.
select
    s.location_id,
    s.station_name,
    s.latitude,
    s.longitude,
    min(a.measured_at) as first_reading_at,
    max(a.measured_at) as last_reading_at
from {{ ref('stg_stations') }} as s
left join {{ ref('stg_air_quality') }} as a on a.location_id = s.location_id
group by 1, 2, 3, 4
