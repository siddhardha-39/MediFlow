# database/db.py
"""
SQLite database layer.

Provides simple CRUD operations for patients and sessions.
Uses plain SQL for clarity and easy PostgreSQL migration later.

DATABASE FILE: mediflow.db (created automatically in MediFlow/ root)
"""
import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger("database.db")

# Database file location
DB_PATH = str(Path(__file__).parent.parent / "mediflow.db")


def _get_connection() -> sqlite3.Connection:
    """Get a database connection with row_factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Rows behave like dicts
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent read performance
    return conn


def init_db():
    """
    Create tables if they don't exist.
    Called once at app startup.
    Safe to call multiple times (IF NOT EXISTS).
    """
    conn = _get_connection()
    conn.executescript("""
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
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized: %s", DB_PATH)


# ── Patient CRUD ───────────────────────────────────────────────────────────────

def create_patient(name: str, age: int = None, gender: str = None,
                   mrn: str = None) -> int:
    """Create a patient and return their ID."""
    conn = _get_connection()
    cursor = conn.execute(
        "INSERT INTO patients (name, age, gender, medical_record_number) VALUES (?, ?, ?, ?)",
        (name, age, gender, mrn),
    )
    patient_id = cursor.lastrowid
    conn.commit()
    conn.close()
    logger.info("Created patient: id=%d name=%s", patient_id, name)
    return patient_id


def get_patient(patient_id: int) -> Optional[Dict[str, Any]]:
    """Get a patient by ID."""
    conn = _get_connection()
    row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_patient_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Find a patient by name (case-insensitive partial match)."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT * FROM patients WHERE LOWER(name) LIKE LOWER(?)",
        (f"%{name}%",),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_patients() -> List[Dict[str, Any]]:
    """List all patients."""
    conn = _get_connection()
    rows = conn.execute("SELECT * FROM patients ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Session CRUD ───────────────────────────────────────────────────────────────

def create_session(patient_id: int, audio_file: str = None,
                   transcript: str = None, soap_note: dict = None,
                   patient_info: dict = None) -> int:
    """
    Create a session record for a patient visit.

    Args:
        patient_id:  The patient's ID.
        audio_file:  Original audio filename.
        transcript:  Full transcript text.
        soap_note:   Dict with keys: subjective, objective, assessment, plan.
        patient_info: Dict with keys: conditions, medications, allergies, symptoms.
    """
    soap = soap_note or {}
    info = patient_info or {}

    conn = _get_connection()
    cursor = conn.execute(
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
    conn.commit()
    conn.close()
    logger.info("Created session: id=%d patient_id=%d", session_id, patient_id)
    return session_id


def get_patient_sessions(patient_id: int) -> List[Dict[str, Any]]:
    """Get all sessions for a patient, most recent first."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM sessions WHERE patient_id = ? ORDER BY created_at DESC",
        (patient_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_patient_history(patient_id: int) -> str:
    """
    Get a formatted text summary of a patient's history across all sessions.
    Used by the memory module and LangChain tools for context retrieval.
    """
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
        lines.append(f"--- Session {i} ({s['created_at']}) ---")
        if s.get("soap_subjective"):
            lines.append(f"  Subjective: {s['soap_subjective']}")
        if s.get("soap_objective"):
            lines.append(f"  Objective: {s['soap_objective']}")
        if s.get("soap_assessment"):
            lines.append(f"  Assessment: {s['soap_assessment']}")
        if s.get("soap_plan"):
            lines.append(f"  Plan: {s['soap_plan']}")

        # Parse JSON fields
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
