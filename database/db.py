# database/db.py
"""
Database abstraction layer.

Supports SQLite (default) and PostgreSQL (if environment variables are provided).
"""
import sqlite3
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from config import (
    IS_POSTGRES,
    MEDIFLOW_POSTGRES_HOST,
    MEDIFLOW_POSTGRES_DB,
    MEDIFLOW_POSTGRES_USER,
    MEDIFLOW_POSTGRES_PASSWORD,
    MEDIFLOW_POSTGRES_PORT,
)

logger = logging.getLogger("database.db")

# Database file location for SQLite
DB_PATH = str(Path(__file__).parent.parent / "mediflow.db")

# ── SQL Schemas ───────────────────────────────────────────────────────────────

SQL_INIT_SQLITE = """
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

SQL_INIT_POSTGRES = """
    CREATE TABLE IF NOT EXISTS patients (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        age INTEGER,
        gender VARCHAR(50),
        medical_record_number VARCHAR(100) UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id SERIAL PRIMARY KEY,
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    );
"""

# ── Helpers for DB Row Handling ───────────────────────────────────────────────

def _get_first_val(row) -> Any:
    """Safely get the first value of a row, regardless of DB driver row format."""
    if row is None:
        return None
    if isinstance(row, dict):
        return list(row.values())[0]
    try:
        return row[0]
    except Exception:
        try:
            return list(row.values())[0]
        except Exception:
            return None

def _get_field(row, name: str, index: int) -> Any:
    """Safely get a field by name or index, regardless of DB driver row format."""
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(name)
    try:
        return row[name]
    except Exception:
        pass
    try:
        return row[index]
    except Exception:
        return None

# ── Connection Management ─────────────────────────────────────────────────────

def _get_connection():
    """Get a connection to either SQLite or PostgreSQL."""
    if IS_POSTGRES:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        conn = psycopg2.connect(
            host=MEDIFLOW_POSTGRES_HOST,
            database=MEDIFLOW_POSTGRES_DB,
            user=MEDIFLOW_POSTGRES_USER,
            password=MEDIFLOW_POSTGRES_PASSWORD,
            port=MEDIFLOW_POSTGRES_PORT,
            cursor_factory=RealDictCursor
        )
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

@contextmanager
def db_connection():
    """Context manager to ensure database connections are committed and closed."""
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.error("Database connection exception: %s", e)
        raise e
    finally:
        conn.close()

# ── Abstract SQL Execution ────────────────────────────────────────────────────

def _execute_query(cursor, query: str, params: tuple = ()):
    """Execute a query, converting placeholders if PostgreSQL is active."""
    if IS_POSTGRES:
        q = query.replace("?", "%s")
    else:
        q = query
    cursor.execute(q, params)
    return cursor

def _execute_insert(cursor, query: str, params: tuple) -> int:
    """Execute an insert query and return the generated auto-increment ID."""
    if IS_POSTGRES:
        pg_query = query.replace("?", "%s") + " RETURNING id"
        cursor.execute(pg_query, params)
        row = cursor.fetchone()
        val = _get_field(row, "id", 0)
        if val is None:
            raise ValueError("Failed to retrieve returning ID from PostgreSQL insert.")
        return int(val)
    else:
        cursor.execute(query, params)
        return cursor.lastrowid

# ── Database Initialization ───────────────────────────────────────────────────

def init_db():
    """Create tables if they don't exist."""
    with db_connection() as conn:
        cursor = conn.cursor()
        if IS_POSTGRES:
            cursor.execute(SQL_INIT_POSTGRES)
        else:
            conn.executescript(SQL_INIT_SQLITE)
    logger.info("Database initialized (PostgreSQL=%s): %s", IS_POSTGRES, DB_PATH if not IS_POSTGRES else MEDIFLOW_POSTGRES_DB)

# ── Patient CRUD ───────────────────────────────────────────────────────────────

def create_patient(name: str, age: int = None, gender: str = None,
                   mrn: str = None) -> int:
    """Create a patient and return their ID."""
    with db_connection() as conn:
        cursor = conn.cursor()
        patient_id = _execute_insert(
            cursor,
            "INSERT INTO patients (name, age, gender, medical_record_number) VALUES (?, ?, ?, ?)",
            (name, age, gender, mrn),
        )
    logger.info("Created patient: id=%d name=%s", patient_id, name)
    return patient_id

def get_patient(patient_id: int) -> Optional[Dict[str, Any]]:
    """Get a patient by ID."""
    with db_connection() as conn:
        cursor = conn.cursor()
        _execute_query(cursor, "SELECT * FROM patients WHERE id = ?", (patient_id,))
        row = cursor.fetchone()
    return dict(row) if row else None

def get_patient_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Find a patient by name (case-insensitive partial match)."""
    with db_connection() as conn:
        cursor = conn.cursor()
        _execute_query(
            cursor,
            "SELECT * FROM patients WHERE LOWER(name) LIKE LOWER(?)",
            (f"%{name}%",),
        )
        row = cursor.fetchone()
    return dict(row) if row else None

def list_patients() -> List[Dict[str, Any]]:
    """List all patients."""
    with db_connection() as conn:
        cursor = conn.cursor()
        _execute_query(cursor, "SELECT * FROM patients ORDER BY created_at DESC")
        rows = cursor.fetchall()
    return [dict(r) for r in rows]

# ── Session CRUD ───────────────────────────────────────────────────────────────

def create_session(patient_id: int, audio_file: str = None,
                   transcript: str = None, soap_note: dict = None,
                   patient_info: dict = None) -> int:
    """
    Create a session record for a patient visit.
    """
    soap = soap_note or {}
    info = patient_info or {}

    with db_connection() as conn:
        cursor = conn.cursor()
        session_id = _execute_insert(
            cursor,
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
    logger.info("Created session: id=%d patient_id=%d", session_id, patient_id)
    return session_id

def get_patient_sessions(patient_id: int) -> List[Dict[str, Any]]:
    """Get all sessions for a patient, most recent first."""
    with db_connection() as conn:
        cursor = conn.cursor()
        _execute_query(
            cursor,
            "SELECT * FROM sessions WHERE patient_id = ? ORDER BY created_at DESC",
            (patient_id,),
        )
        rows = cursor.fetchall()
    return [dict(r) for r in rows]

def get_patient_history(patient_id: int) -> str:
    """
    Get a formatted text summary of a patient's history across all sessions.
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
        # Handle created_at formatting safely
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

# ── Dashboard Statistics ──────────────────────────────────────────────────────

def get_db_stats() -> dict:
    """Helper to aggregate operational metrics from the database."""
    with db_connection() as conn:
        cursor = conn.cursor()
        
        _execute_query(cursor, "SELECT COUNT(*) FROM patients")
        total_patients_row = cursor.fetchone()
        total_patients = int(_get_first_val(total_patients_row) or 0)
        
        _execute_query(cursor, "SELECT COUNT(*) FROM sessions")
        total_sessions_row = cursor.fetchone()
        total_sessions = int(_get_first_val(total_sessions_row) or 0)
        
        _execute_query(cursor, "SELECT conditions, medications, allergies FROM sessions")
        rows = cursor.fetchall()
        
    conditions_count = {}
    medications_count = {}
    allergies_count = {}
    
    for row in rows:
        conds_raw = _get_field(row, "conditions", 0)
        meds_raw = _get_field(row, "medications", 1)
        algs_raw = _get_field(row, "allergies", 2)
        
        if conds_raw:
            try:
                for cond in json.loads(conds_raw):
                    conditions_count[cond] = conditions_count.get(cond, 0) + 1
            except:
                pass
        if meds_raw:
            try:
                for med in json.loads(meds_raw):
                    medications_count[med] = medications_count.get(med, 0) + 1
            except:
                pass
        if algs_raw:
            try:
                for alg in json.loads(algs_raw):
                    allergies_count[alg] = allergies_count.get(alg, 0) + 1
            except:
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
