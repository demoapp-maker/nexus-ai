from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.database import DATABASE_URL, engine, init_db
from sqlalchemy import text


def setup() -> None:
    print("Initializing the Nexus AI database...")
    try:
        init_db()
        print("Tables created successfully.")

        with engine.connect() as connection:
            if engine.dialect.name == "sqlite":
                version = connection.execute(text("SELECT sqlite_version()"))
                print(f"Connected to SQLite {version.scalar_one()}.")
            else:
                name = connection.execute(text("SELECT current_database()"))
                print(f"Connected to database: {name.scalar_one()}.")
        print(f"Database URL configured: {DATABASE_URL.split('@')[-1]}")
    except Exception as exc:
        print(f"Database setup failed: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    setup()
