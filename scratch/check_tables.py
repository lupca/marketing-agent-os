# scratch/check_tables.py
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sqlalchemy import text
from db.connection import engine

def main():
    print("Checking tables in PostgreSQL...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
            tables = [row[0] for row in result.fetchall()]
            print(f"Total tables: {len(tables)}")
            print("Tables:")
            for t in sorted(tables):
                print(f" - {t}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
