"""
db.py — everything to do with connecting to PostgreSQL.

We use SQLAlchemy because pandas' `to_sql()` and `read_sql()` need it,
but we only ever use one function from it: `create_engine()`.

Run this file directly to (re)create the database tables:
    python src/db.py
"""
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()  # reads the .env file in the project root, if present


def get_engine():
    """Build a SQLAlchemy engine from the POSTGRES_* environment
    variables. Every other script in this project calls this function
    instead of connecting to Postgres directly, so the connection
    details only live in one place.
    """
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "city_breaks")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)


def init_db():
    """Run sql/schema.sql against the database. This drops and
    recreates every table, so it's safe to run again and again while
    you're learning — but it does erase existing data."""
    schema_path = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")
    with open(schema_path) as f:
        schema_sql = f.read()

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(schema_sql))
    print("Database tables created.")


if __name__ == "__main__":
    init_db()
