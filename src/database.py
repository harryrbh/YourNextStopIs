"""Everything to do with connecting to the database."""
import os

from sqlalchemy import create_engine, event, text

# The database is one file, stored at data/cityBreaks.db
projectRoot = os.path.join(os.path.dirname(__file__), "..")
databasePath = os.path.join(projectRoot, "data", "cityBreaks.db")


def getEngine():
    """Build a SQLAlchemy engine pointing at data/cityBreaks.db."""
    engine = create_engine(f"sqlite:///{databasePath}")

    # SQLite doesn't enforce foreign keys unless you ask it to, on every single connection
    @event.listens_for(engine, "connect")
    def _enableForeignKeys(dbapiConnection, _):
        dbapiConnection.execute("PRAGMA foreign_keys = ON")

    return engine


def initDb():
    """Run sql/schema.sql against the database."""
    schemaPath = os.path.join(projectRoot, "sql", "schema.sql")
    with open(schemaPath) as schemaFile:
        schemaSql = schemaFile.read()

    os.makedirs(os.path.dirname(databasePath), exist_ok=True)

    engine = getEngine()
    # The schema file holds many statements
    rawConnection = engine.raw_connection()
    try:
        rawConnection.executescript(schemaSql)
        rawConnection.commit()
    finally:
        rawConnection.close()

    print(f"Database tables created at {databasePath}")


if __name__ == "__main__":
    initDb()

