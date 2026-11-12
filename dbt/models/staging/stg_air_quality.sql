-- One row per sensor per hour.
-- OpenAQ hours run from :30 to :30 UTC (for example 23:30-00:30, which is 05:00-06:00 IST).
-- Weather is on whole hours. So each reading is also labelled with the whole hour
-- it is centred on (00:00 UTC here), which is what the join to weather uses.
select
    sensor_id,
    location_id,
    parameter,
    measured_at,
    measured_at at time zone '{{ var("local_timezone") }}' as measured_at_ist,
    date_trunc('hour', measured_at + interval '30 minutes') as hour_utc,
    date_trunc('hour', measured_at + interval '30 minutes') at time zone '{{ var("local_timezone") }}' as hour_ist,
    value
from {{ source('raw', 'air_quality_hourly') }}
