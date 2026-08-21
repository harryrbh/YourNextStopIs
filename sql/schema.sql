-- ============================================================
-- City Break Recommender — Database Schema
-- ============================================================
-- One file, one job: create every table the app needs.
-- Run it with:  python src/db.py --init
-- or directly:  psql -U postgres -d city_breaks -f sql/schema.sql
--
-- Table order matters here because of foreign keys: countries
-- must exist before cities, cities before airports, etc.
-- ============================================================

-- Drop tables first so this script is safe to re-run while you're
-- learning (DROP ... CASCADE removes anything that depends on them).
DROP TABLE IF EXISTS city_features CASCADE;
DROP TABLE IF EXISTS routes CASCADE;
DROP TABLE IF EXISTS airports CASCADE;
DROP TABLE IF EXISTS weather CASCADE;
DROP TABLE IF EXISTS tourism CASCADE;
DROP TABLE IF EXISTS cities CASCADE;
DROP TABLE IF EXISTS countries CASCADE;

-- One row per country.
CREATE TABLE countries (
    country_id      SERIAL PRIMARY KEY,
    iso2            CHAR(2) UNIQUE NOT NULL,   -- e.g. 'FR'
    name            TEXT NOT NULL,
    region          TEXT,
    population      BIGINT,
    gdp_per_capita  DOUBLE PRECISION,          -- used as a "cost" proxy
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION
);

-- One row per city. Every city belongs to one country.
CREATE TABLE cities (
    city_id         SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    country_id      INTEGER REFERENCES countries(country_id),
    population      BIGINT,
    latitude        DOUBLE PRECISION NOT NULL,
    longitude       DOUBLE PRECISION NOT NULL,
    heritage_sites  INTEGER DEFAULT 0,          -- from data/culture.csv
    attractions     INTEGER DEFAULT 0,          -- from data/culture.csv
    CHECK (latitude BETWEEN -90 AND 90),
    CHECK (longitude BETWEEN -180 AND 180)
);

-- Twelve rows per city: one average per calendar month.
CREATE TABLE weather (
    weather_id       SERIAL PRIMARY KEY,
    city_id          INTEGER REFERENCES cities(city_id),
    month            SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    temperature_c    DOUBLE PRECISION,
    precipitation_mm DOUBLE PRECISION,
    UNIQUE (city_id, month)
);

-- One row per country per year (our sample data only has one year).
CREATE TABLE tourism (
    tourism_id  SERIAL PRIMARY KEY,
    country_id  INTEGER REFERENCES countries(country_id),
    year        INTEGER NOT NULL,
    arrivals    BIGINT
);

-- Real airports, from the OpenFlights dataset, matched to our cities.
CREATE TABLE airports (
    airport_id  SERIAL PRIMARY KEY,
    iata_code   CHAR(3),
    name        TEXT,
    city_id     INTEGER REFERENCES cities(city_id),
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION
);

-- Real flight routes between two airports (also from OpenFlights).
CREATE TABLE routes (
    route_id                SERIAL PRIMARY KEY,
    source_airport_id       INTEGER REFERENCES airports(airport_id),
    destination_airport_id  INTEGER REFERENCES airports(airport_id),
    airline                 TEXT
);

-- The "ML-ready" table: one row per city with every engineered
-- feature and score. Everything in the app reads from here.
CREATE TABLE city_features (
    city_id              INTEGER PRIMARY KEY REFERENCES cities(city_id),

    -- raw numbers, aggregated from the tables above
    avg_temperature_c    DOUBLE PRECISION,
    avg_precipitation_mm DOUBLE PRECISION,
    airport_count        INTEGER DEFAULT 0,
    route_count          INTEGER DEFAULT 0,
    connectivity         DOUBLE PRECISION DEFAULT 0,  -- from NetworkX, see build_features.py
    heritage_sites       INTEGER DEFAULT 0,
    attractions          INTEGER DEFAULT 0,
    gdp_per_capita        DOUBLE PRECISION,
    tourist_arrivals      BIGINT,

    -- every score below is normalised 0-100, higher = better
    weather_score        DOUBLE PRECISION,
    accessibility_score  DOUBLE PRECISION,
    culture_score        DOUBLE PRECISION,
    cost_score            DOUBLE PRECISION,   -- higher score = cheaper
    tourism_score         DOUBLE PRECISION,

    -- the transparent weighted-average baseline (see build_features.py)
    overall_score         DOUBLE PRECISION,

    -- filled in later by cluster.py
    cluster                INTEGER
);
