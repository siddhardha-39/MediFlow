# scripts/reset_demo_data.py
"""
Reset MediFlow demo data.

Clears all patients and sessions from the local SQLite database so you can
start a fresh demo without deleting the database file itself.

Usage:
    python scripts/reset_demo_data.py
"""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "mediflow.db"

if DB_PATH.exists():
    print(f"Connecting to {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Delete child table first to respect foreign key constraints
    cursor.execute("DELETE FROM sessions;")
    cursor.execute("DELETE FROM patients;")
    conn.commit()
    conn.close()

    print("✓ All sessions and patients deleted. Database is ready for a fresh demo.")
else:
    print(f"Database file not found: {DB_PATH}")
    print("Run the application first to create the database.")
