import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.database import engine, init_db
from sqlalchemy import text


def setup():
    print("🚀 Initializing Local PostgreSQL for Nexus AI...")
    try:
        # Create tables
        init_db()
        print("✅ Tables created successfully.")
        
        # Verify connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database();"))
            db_name = result.fetchone()[0]
            print(f"✅ Connected to database: {db_name}")
            
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        raise SystemExit(1) from e

if __name__ == "__main__":
    setup()
