# wipe_db.py
import sqlite3
import os

db_path = "mediflow.db"
if os.path.exists(db_path):
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Delete child table first to prevent any foreign key constraint issues
    cursor.execute("DELETE FROM sessions;")
    cursor.execute("DELETE FROM patients;")
    conn.commit()
    print("Deleted all sessions and patients successfully!")
    conn.close()
else:
    print("SQLite database file mediflow.db not found.")
