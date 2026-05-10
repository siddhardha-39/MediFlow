# database/models.py
"""
SQLite database models using plain SQL (no ORM).

WHY PLAIN SQL INSTEAD OF SQLALCHEMY:
    - Simpler to understand for beginners
    - No extra dependency
    - Easy to migrate to PostgreSQL later (same SQL syntax)
    - SQLAlchemy is great but adds complexity we don't need yet

TABLES:
    patients        - basic patient info
    sessions        - each visit/recording session
    transcripts     - raw transcript from Whisper
    soap_notes      - generated SOAP documentation
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Patient(BaseModel):
    """A patient record."""
    id: Optional[int] = None
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    medical_record_number: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class Session(BaseModel):
    """A single visit/recording session for a patient."""
    id: Optional[int] = None
    patient_id: int
    audio_file: Optional[str] = None
    transcript: Optional[str] = None
    soap_subjective: Optional[str] = None
    soap_objective: Optional[str] = None
    soap_assessment: Optional[str] = None
    soap_plan: Optional[str] = None
    conditions: Optional[str] = None    # JSON string of extracted conditions
    medications: Optional[str] = None   # JSON string of extracted medications
    allergies: Optional[str] = None     # JSON string of extracted allergies
    symptoms: Optional[str] = None      # JSON string of extracted symptoms
    created_at: datetime = Field(default_factory=datetime.now)
