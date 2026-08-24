-- ============================================================
-- City Break Recommender — Database Schema (SQLite)
-- ============================================================
-- One file, one job: create every table the app needs.
-- Run it with:  python src/db.py
--
-- Table order matters here because of foreign keys: countries
-- must exist before cities, cities before airports, etc.
--
-- Note: SQLite's types are more relaxed than PostgreSQL's — it
-- doesn't strictly enforce that a REAL column always holds a number,
-- for example. We still declare types (INTEGER, TEXT, REAL) because
-- it documents what each column is *for*, even though SQLite itself
-- is lenient about it.
-- ============================================================

-- Drop tables first so this script is safe to re-run while you're
-- learning. Order matters here too: you must drop tables that
-- reference other tables (like city_features, which references
-- cities) before the tables they reference.
DROP TABLE IF EXISTS city_features;
DROP TABLE IF EXISTS routes;
DROP TABLE IF EXISTS airports;
DROP TABLE IF EXISTS weather;
DROP TABLE IF EXISTS tourism;
DROP TABLE IF EXISTS cities;
DROP TABLE IF EXISTS countries;

-- One row per country.
CREATE TABLE countries (
    country_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    iso2            TEXT UNIQUE NOT NULL,   -- e.g. 'FR'
    name            TEXT NOT NULL,
    region          TEXT,
    population      INTEGER,
    gdp_per_capita  REAL,                    -- used as a "cost" proxy
    latitude        REAL,
    longitude       REAL
);

-- One row per city. Every city belongs to one country.
CREATE TABLE cities (
    city_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    country_id      INTEGER REFERENCES countries(country_id),
    population      INTEGER,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    heritage_sites  INTEGER DEFAULT 0,        -- from data/culture.csv
    attractions     INTEGER DEFAULT 0,        -- from data/culture.csv
    CHECK (latitude BETWEEN -90 AND 90),
    CHECK (longitude BETWEEN -180 AND 180)
);

-- Twelve rows per city: one average per calendar month.
CREATE TABLE weather (
    weather_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id          INTEGER REFERENCES cities(city_id),
    month            INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    temperature_c    REAL,
    precipitation_mm REAL,
    UNIQUE (city_id, month)
);

-- One row per country per year (our sample data only has one year).
CREATE TABLE tourism (
    tourism_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id  INTEGER REFERENCES countries(country_id),
    year        INTEGER NOT NULL,
    arrivals    INTEGER
);

-- Real airports, from the OpenFlights dataset, matched to our cities.
CREATE TABLE airports (
    airport_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    iata_code   TEXT,
    name        TEXT,
    city_id     INTEGER REFERENCES cities(city_id),
    latitude    REAL,
    longitude   REAL
);

-- Real flight routes between two airports (also from OpenFlights).
CREATE TABLE routes (
    route_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    source_airport_id       INTEGER REFERENCES airports(airport_id),
    destination_airport_id  INTEGER REFERENCES airports(airport_id),
    airline                 TEXT
);

-- The "ready to use" table: one row per city with every calculated
-- feature and score. Everything in the app reads from here.
CREATE TABLE city_features (
    city_id              INTEGER PRIMARY KEY REFERENCES cities(city_id),

    -- raw numbers, calculated from the tables above
    avg_temperature_c    REAL,
    avg_precipitation_mm REAL,
    airport_count        INTEGER DEFAULT 0,
    route_count          INTEGER DEFAULT 0,
    connectivity         REAL DEFAULT 0,      -- from NetworkX, see build_features.py
    heritage_sites       INTEGER DEFAULT 0,
    attractions          INTEGER DEFAULT 0,
    gdp_per_capita        REAL,
    tourist_arrivals      INTEGER,

    -- every score below is rescaled to 0-100, higher = better
    weather_score        REAL,
    accessibility_score  REAL,
    culture_score        REAL,
    cost_score            REAL,   -- higher score = cheaper
    tourism_score         REAL,

    -- the plain weighted-average overall score (see build_features.py)
    overall_score          REAL,

    -- filled in later by cluster.py
    cluster                INTEGER
);
