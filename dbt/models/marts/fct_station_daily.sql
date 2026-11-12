-- One row per station per day (India time), with the PM2.5 part of the AQI.
-- CPCB needs at least 16 hourly values in a day before it will compute a
-- sub-index, so days with less data than that are left out.
with daily as (
    select
        location_id,
        station_name,
        measured_at_ist::date as reading_date,
        avg(pm25) as pm25_avg,
        max(pm25) as pm25_max,
        count(pm25) as hours_reported
    from {{ ref('fct_air_quality_hourly') }}
    group by 1, 2, 3
),
scored as (
    select
        *,
        {{ pm25_sub_index('pm25_avg') }} as pm25_sub_index
    from daily
    where hours_reported >= 16
)
select
    *,
    {{ aqi_category('pm25_sub_index') }} as aqi_category
from scored
