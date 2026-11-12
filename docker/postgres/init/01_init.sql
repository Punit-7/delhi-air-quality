-- Runs once, the first time the PostgreSQL container starts on an empty volume.
-- To run it again: docker compose down -v (this deletes the database)

-- Airflow keeps its own bookkeeping in a separate database.
CREATE DATABASE airflow;

-- Three layers. Python writes to raw. dbt builds staging and marts from it.
CREATE SCHEMA raw;
CREATE SCHEMA staging;
CREATE SCHEMA marts;

CREATE TABLE raw.stations (
    location_id integer PRIMARY KEY,
    station_name text NOT NULL,
    latitude double precision,
    longitude double precision,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE raw.air_quality_hourly (
    sensor_id integer NOT NULL,
    location_id integer NOT NULL,
    parameter text NOT NULL,          -- pm25, pm10, no2
    units text,
    measured_at timestamptz NOT NULL, -- start of the hour
    value double precision NOT NULL,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (sensor_id, measured_at)
);
CREATE INDEX air_quality_hourly_measured_at ON raw.air_quality_hourly (measured_at);

CREATE TABLE raw.weather_hourly (
    measured_at timestamptz PRIMARY KEY,
    temperature_c double precision,
    relative_humidity_pct double precision,
    wind_speed_kmh double precision,
    wind_direction_deg double precision,
    precipitation_mm double precision,
    boundary_layer_height_m double precision,
    loaded_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE raw.fire_detections (
    latitude double precision NOT NULL,
    longitude double precision NOT NULL,
    detected_at timestamptz NOT NULL,
    satellite text NOT NULL,
    confidence text,                  -- n = nominal, h = high
    frp_mw double precision,          -- fire radiative power, megawatts
    day_night text,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (latitude, longitude, detected_at, satellite)
);

-- A read-only login for Grafana. It can see the marts and nothing else.
-- The password comes from the GRAFANA_DB_PASSWORD variable in .env.
\set grafana_password `echo "$GRAFANA_DB_PASSWORD"`
CREATE ROLE grafana_reader LOGIN PASSWORD :'grafana_password';
GRANT USAGE ON SCHEMA marts TO grafana_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT SELECT ON TABLES TO grafana_reader;
