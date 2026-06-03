# scratch/run_seeding.py
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sqlalchemy import text
from db.connection import engine

SQL_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs", "agentic ai", "brand", "seed_topvnsports.sql"))

def run_seeding():
    print(f"Reading SQL seed file from: {SQL_FILE}")
    if not os.path.exists(SQL_FILE):
        print("Error: SQL file does not exist!")
        return
        
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()
        
    print("Executing SQL seeding script on PostgreSQL database...")
    try:
        # Split DDL statement to execute cleanly if needed, or run as a single DO block
        with engine.connect() as conn:
            conn.execute(text(sql_content))
            conn.commit()
        print("Seeding script executed successfully! Database populated with TOPVNSPORT data.")
    except Exception as e:
        print(f"Failed to execute seeding script: {e}")

if __name__ == "__main__":
    run_seeding()
