-- One row per day: how many fires the satellite saw over Punjab and Haryana.
-- Days with no fires inside the loaded period get an explicit zero, so a quiet
-- day and a day we never loaded are not confused.
with detections as (
    select
        fire_date,
        count(*) as fire_count,
        count(*) filter (where confidence = 'h') as high_confidence_count,
        sum(frp_mw) as total_frp_mw
    from {{ ref('stg_fires') }}
    group by 1
),
calendar as (
    select generate_series(min(fire_date), max(fire_date), interval '1 day')::date as fire_date
    from detections
)
select
    c.fire_date,
    coalesce(d.fire_count, 0) as fire_count,
    coalesce(d.high_confidence_count, 0) as high_confidence_count,
    coalesce(d.total_frp_mw, 0) as total_frp_mw
from calendar as c
left join detections as d on d.fire_date = c.fire_date
