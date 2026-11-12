-- The table that answers the project question: one row per hour for the whole
-- city, with pollution next to everything that might explain it.
with city as (
    select
        measured_at,
        measured_at_ist,
        avg(pm25) as pm25_city_avg,
        max(pm25) as pm25_city_max,
        count(pm25) as stations_reporting,
        avg(pm10) as pm10_city_avg,
        avg(no2) as no2_city_avg
    from {{ ref('fct_air_quality_hourly') }}
    group by 1, 2
)
select
    c.measured_at,
    c.measured_at_ist,
    extract(hour from c.measured_at_ist)::int as hour_ist,
    c.pm25_city_avg,
    c.pm25_city_max,
    c.pm10_city_avg,
    c.no2_city_avg,
    c.stations_reporting,
    w.temperature_c,
    w.relative_humidity_pct,
    w.wind_speed_kmh,
    w.wind_direction_deg,
    w.precipitation_mm,
    w.boundary_layer_height_m,
    -- wind blowing from Punjab and Haryana towards Delhi
    coalesce(w.wind_direction_deg between 270 and 360, false) as wind_from_northwest,
    -- smoke needs time to travel, so pair each hour with yesterday's fires
    f.fire_count as fires_previous_day,
    -- 6 pm on Diwali to 6 am the next morning, India time
    (
        c.measured_at_ist >= timestamp '{{ var("diwali_date") }} 18:00'
        and c.measured_at_ist < timestamp '{{ var("diwali_date") }} 18:00' + interval '12 hours'
    ) as is_diwali_night
from city as c
left join {{ ref('stg_weather') }} as w on w.measured_at = c.measured_at
left join {{ ref('fct_fires_daily') }} as f on f.fire_date = c.measured_at_ist::date - 1
where c.stations_reporting >= {{ var('min_stations_for_city_average') }}
