"""
db.py — everything to do with connecting to the database.

We use SQLite instead of a "real" database server like PostgreSQL or
MySQL. SQLite stores the entire database as a single file on disk —
there's no separate server to install, start, or configure, and no
username/password to set up. That makes it a good fit for a project
like this one: perfect for learning, for a single-user app, or for
a small deployment. (A busy, multi-user production app would
eventually outgrow it and want a real database server — but you won't
hit that limit here.)

Run this file directly to (re)create the database tables:
    python src/db.py
"""
import os

from sqlalchemy import create_engine, event, text

# The database is one file, stored at data/city_breaks.db. We build
# this path from this file's own location (not the current working
# directory), so it works the same whether you run
# `python src/db.py` from the project root or from inside src/.
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(PROJECT_ROOT, "data", "city_breaks.db")


def get_engine():
    """Build a SQLAlchemy engine pointing at data/city_breaks.db.
    Every other script in this project calls this function instead of
    opening the file directly, so the database location only lives in
    one place.
    """
    engine = create_engine(f"sqlite:///{DB_PATH}")

    # SQLite doesn't enforce foreign keys unless you ask it to, on
    # every single connection. This turns that on, so e.g. inserting
    # an airport for a city that doesn't exist will correctly fail.
    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys = ON")

    return engine


def init_db():
    """Run sql/schema.sql against the database. This drops and
    recreates every table, so it's safe to run again and again while
    you're learning — but it does erase existing data."""
    schema_path = os.path.join(PROJECT_ROOT, "sql", "schema.sql")
    with open(schema_path) as f:
        schema_sql = f.read()

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    engine = get_engine()
    # schema.sql has many statements in one file. SQLite's own
    # `executescript` runs a whole script like this in one go — the
    # usual SQLAlchemy `conn.execute(text(...))` only runs one
    # statement at a time, so we drop down to the raw connection here.
    raw_connection = engine.raw_connection()
    try:
        raw_connection.executescript(schema_sql)
        raw_connection.commit()
    finally:
        raw_connection.close()

    print(f"Database tables created at {DB_PATH}")


if __name__ == "__main__":
    init_db()

