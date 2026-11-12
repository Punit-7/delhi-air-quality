-- One row per station per whole hour (UTC), with each pollutant in its own column.
-- The raw table is "long" (one row per pollutant); dashboards want it "wide".
-- measured_at here is the aligned whole hour, so it joins to weather.
select
    a.location_id,
    s.station_name,
    a.hour_utc as measured_at,
    a.hour_ist as measured_at_ist,
    avg(a.value) filter (where a.parameter = 'pm25') as pm25,
    avg(a.value) filter (where a.parameter = 'pm10') as pm10,
    avg(a.value) filter (where a.parameter = 'no2') as no2
from {{ ref('stg_air_quality') }} as a
inner join {{ ref('stg_stations') }} as s on s.location_id = a.location_id
group by 1, 2, 3, 4
