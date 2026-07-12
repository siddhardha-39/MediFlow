# database/db.py
"""
Database layer — SQLite only.

Uses Python's built-in sqlite3 module; no external dependencies required.
"""
import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import MEDIFLOW_DB_PATH

logger = logging.getLogger("database.db")

# Database file location
DB_PATH = MEDIFLOW_DB_PATH

# ── SQL Schema ────────────────────────────────────────────────────────────────

SQL_INIT = """
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,
        medical_record_number TEXT UNIQUE,
        created_at TEXT DEFAULT (datetime('now', 'localtime'))
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        audio_file TEXT,
        transcript TEXT,
        soap_subjective TEXT,
        soap_objective TEXT,
        soap_assessment TEXT,
        soap_plan TEXT,
        conditions TEXT,
        medications TEXT,
        allergies TEXT,
        symptoms TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    );
"""

# ── Connection Management ─────────────────────────────────────────────────────

@contextmanager
def db_connection():
    """Context manager for SQLite connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error("Database error: %s", e)
        raise
    finally:
        conn.close()

# ── Database Initialization ───────────────────────────────────────────────────

def init_db():
    """Create tables if they don't exist."""
    with db_connection() as conn:
        conn.executescript(SQL_INIT)
    logger.info("SQLite database initialized: %s", DB_PATH)

# ── Patient CRUD ───────────────────────────────────────────────────────────────

def create_patient(name: str, age: int = None, gender: str = None,
                   mrn: str = None) -> int:
    """Create a patient and return their ID."""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO patients (name, age, gender, medical_record_number) VALUES (?, ?, ?, ?)",
            (name, age, gender, mrn),
        )
        patient_id = cursor.lastrowid
    logger.info("Created patient: id=%d name=%s", patient_id, name)
    return patient_id


def get_patient(patient_id: int) -> Optional[Dict[str, Any]]:
    """Get a patient by ID."""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        row = cursor.fetchone()
    return dict(row) if row else None


def get_patient_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Find a patient by name (case-insensitive partial match)."""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM patients WHERE LOWER(name) LIKE LOWER(?)",
            (f"%{name}%",),
        )
        row = cursor.fetchone()
    return dict(row) if row else None


def list_patients() -> List[Dict[str, Any]]:
    """List all patients."""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients ORDER BY created_at DESC")
        rows = cursor.fetchall()
    return [dict(r) for r in rows]

# ── Session CRUD ───────────────────────────────────────────────────────────────

def create_session(patient_id: int, audio_file: str = None,
                   transcript: str = None, soap_note: dict = None,
                   patient_info: dict = None) -> int:
    """Create a session record for a patient visit."""
    soap = soap_note or {}
    info = patient_info or {}

    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO sessions
               (patient_id, audio_file, transcript,
                soap_subjective, soap_objective, soap_assessment, soap_plan,
                conditions, medications, allergies, symptoms)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                patient_id, audio_file, transcript,
                soap.get("subjective", ""),
                soap.get("objective", ""),
                soap.get("assessment", ""),
                soap.get("plan", ""),
                json.dumps(info.get("conditions", [])),
                json.dumps(info.get("medications", [])),
                json.dumps(info.get("allergies", [])),
                json.dumps(info.get("symptoms", [])),
            ),
        )
        session_id = cursor.lastrowid
    logger.info("Created session: id=%d patient_id=%d", session_id, patient_id)
    return session_id


def get_patient_sessions(patient_id: int) -> List[Dict[str, Any]]:
    """Get all sessions for a patient, most recent first."""
    with db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM sessions WHERE patient_id = ? ORDER BY created_at DESC",
            (patient_id,),
        )
        rows = cursor.fetchall()
    return [dict(r) for r in rows]


def get_patient_history(patient_id: int) -> str:
    """Get a formatted text summary of a patient's history across all sessions."""
    patient = get_patient(patient_id)
    if not patient:
        return "Patient not found."

    sessions = get_patient_sessions(patient_id)
    if not sessions:
        return f"Patient {patient['name']} has no recorded sessions."

    lines = [f"Patient: {patient['name']} (Age: {patient.get('age', 'N/A')}, Gender: {patient.get('gender', 'N/A')})"]
    lines.append(f"Total sessions: {len(sessions)}")
    lines.append("")

    for i, s in enumerate(sessions, 1):
        created_at = s.get("created_at") or "N/A"
        lines.append(f"--- Session {i} ({created_at}) ---")
        if s.get("soap_subjective"):
            lines.append(f"  Subjective: {s['soap_subjective']}")
        if s.get("soap_objective"):
            lines.append(f"  Objective: {s['soap_objective']}")
        if s.get("soap_assessment"):
            lines.append(f"  Assessment: {s['soap_assessment']}")
        if s.get("soap_plan"):
            lines.append(f"  Plan: {s['soap_plan']}")

        for field in ["conditions", "medications", "allergies", "symptoms"]:
            val = s.get(field)
            if val:
                try:
                    items = json.loads(val)
                    if items:
                        lines.append(f"  {field.title()}: {', '.join(items)}")
                except json.JSONDecodeError:
                    pass
        lines.append("")

    return "\n".join(lines)

# ── Dashboard Statistics ──────────────────────────────────────────────────────

def get_db_stats() -> dict:
    """Aggregate operational metrics from the database."""
    with db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM patients")
        total_patients = int(cursor.fetchone()[0] or 0)

        cursor.execute("SELECT COUNT(*) FROM sessions")
        total_sessions = int(cursor.fetchone()[0] or 0)

        cursor.execute("SELECT conditions, medications, allergies FROM sessions")
        rows = cursor.fetchall()

    conditions_count: Dict[str, int] = {}
    medications_count: Dict[str, int] = {}
    allergies_count: Dict[str, int] = {}

    for row in rows:
        for raw, counter in [
            (row["conditions"], conditions_count),
            (row["medications"], medications_count),
            (row["allergies"], allergies_count),
        ]:
            if raw:
                try:
                    for item in json.loads(raw):
                        counter[item] = counter.get(item, 0) + 1
                except (json.JSONDecodeError, Exception):
                    pass

    top_conditions = sorted(conditions_count.items(), key=lambda x: x[1], reverse=True)[:5]
    top_medications = sorted(medications_count.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_patients": total_patients,
        "total_sessions": total_sessions,
        "top_conditions": [{"name": k, "count": v} for k, v in top_conditions],
        "top_medications": [{"name": k, "count": v} for k, v in top_medications],
        "allergies_summary": [{"name": k, "count": v} for k, v in allergies_count.items()],
    }
