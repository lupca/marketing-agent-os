import sqlite3
import os

db_path = 'data/mock_database.db'
if not os.path.exists(db_path):
    print(f"File {db_path} not found.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", [t[0] for t in tables])
    
    for table_name in [t[0] for t in tables]:
        print(f"\n--- Data from table: {table_name} ---")
        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5;")
            rows = cursor.fetchall()
            # Get column names
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [c[1] for c in cursor.fetchall()]
            print(columns)
            for row in rows:
                print(row)
        except Exception as e:
            print(f"Error reading table {table_name}: {e}")
    
    conn.close()
