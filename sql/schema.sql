-- Database schema

DROP TABLE IF EXISTS city_features;
DROP TABLE IF EXISTS routes;
DROP TABLE IF EXISTS airports;
DROP TABLE IF EXISTS weather;
DROP TABLE IF EXISTS tourism;
DROP TABLE IF EXISTS cities;
DROP TABLE IF EXISTS countries;

-- Country facts
CREATE TABLE countries (
    country_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    iso2                TEXT UNIQUE NOT NULL,
    name                TEXT NOT NULL,
    region               TEXT,
    population           INTEGER,
    gdp_per_capita        REAL,
    urban_population_pct   REAL,
    latitude                REAL,
    longitude                REAL
);

-- Candidate city list
CREATE TABLE cities (
    city_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    country_id      INTEGER REFERENCES countries(country_id),
    population      INTEGER,
    latitude        REAL NOT NULL,
    longitude       REAL NOT NULL,
    heritage_sites  INTEGER DEFAULT 0,
    attractions     INTEGER DEFAULT 0,
    attraction_1    TEXT,
    attraction_2    TEXT,
    attraction_3    TEXT,
    CHECK (latitude BETWEEN -90 AND 90),
    CHECK (longitude BETWEEN -180 AND 180)
);

-- Monthly climate per city
CREATE TABLE weather (
    weather_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id          INTEGER REFERENCES cities(city_id),
    month            INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    temperature_c    REAL,
    precipitation_mm REAL,
    UNIQUE (city_id, month)
);

-- Visitor numbers per country
CREATE TABLE tourism (
    tourism_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id         INTEGER REFERENCES countries(country_id),
    year                INTEGER NOT NULL,
    arrivals             INTEGER,
    tourism_growth_pct    REAL
);

-- Airports linked to cities
CREATE TABLE airports (
    airport_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    iata_code   TEXT,
    name        TEXT,
    city_id     INTEGER REFERENCES cities(city_id),
    latitude    REAL,
    longitude   REAL
);

-- Flight routes between airports
CREATE TABLE routes (
    route_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    source_airport_id       INTEGER REFERENCES airports(airport_id),
    destination_airport_id  INTEGER REFERENCES airports(airport_id),
    airline                 TEXT
);

-- Scores and facts per city
CREATE TABLE city_features (
    city_id               INTEGER PRIMARY KEY REFERENCES cities(city_id),

    avg_temperature_c     REAL,
    avg_precipitation_mm  REAL,
    airport_count         INTEGER DEFAULT 0,
    route_count           INTEGER DEFAULT 0,
    connectivity          REAL DEFAULT 0,
    heritage_sites        INTEGER DEFAULT 0,
    attractions            INTEGER DEFAULT 0,
    gdp_per_capita          REAL,
    urban_population_pct     REAL,
    tourist_arrivals           INTEGER,
    previous_arrivals            INTEGER,
    tourism_growth_pct             REAL,

    nearest_airport_name  TEXT,
    nearest_airport_km    REAL,

    weather_score        REAL,
    accessibility_score  REAL,
    culture_score        REAL,
    cost_score            REAL,
    tourism_score           REAL,

    overall_score            REAL,

    category                   TEXT,

    price_tier                    TEXT
);
