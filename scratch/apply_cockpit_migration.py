# scratch/apply_cockpit_migration.py
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sqlalchemy import text
from db.connection import engine

SQL_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "db", "migrations", "cockpit_tables.sql"))

def run_migration():
    print(f"Reading SQL migration file from: {SQL_FILE}")
    if not os.path.exists(SQL_FILE):
        print("Error: SQL file does not exist!")
        return
        
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()
        
    print("Executing Cockpit Tables migration script on PostgreSQL database...")
    try:
        with engine.connect() as conn:
            # We can execute the entire script as a single batch
            conn.execute(text(sql_content))
            conn.commit()
        print("Migration executed successfully! Autopilot Cockpit tables initialized.")
    except Exception as e:
        print(f"Failed to execute migration script: {e}")

if __name__ == "__main__":
    run_migration()
