-- A reading stamped later than now means a timezone mistake somewhere upstream.
select *
from {{ ref('stg_air_quality') }}
where measured_at > now() + interval '1 hour'
