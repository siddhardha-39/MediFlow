# soap_notes/models.py
"""
Pydantic schemas for SOAP note generation.

SOAP FORMAT:
    S - Subjective:   What the patient reports (symptoms, complaints, history)
    O - Objective:    What the clinician observes (vitals, exam findings, lab results)
    A - Assessment:   Diagnosis or clinical impression
    P - Plan:         Treatment plan, medications, follow-up

WHY SOAP:
    SOAP is the universal standard for clinical documentation.
    Every hospital, every EHR system, every medical school uses it.
    Structuring LLM output as SOAP makes it immediately usable.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from config import MEDIFLOW_LLM_MODEL


class SOAPNote(BaseModel):
    """
    Structured SOAP note generated from a doctor's transcript.

    All fields default to empty strings so the system never crashes
    on partial output. The validator (Module 2) checks for missing sections.
    """
    subjective:  str = Field(default="", description="Patient-reported symptoms, complaints, history")
    objective:   str = Field(default="", description="Clinical observations, vitals, exam findings")
    assessment:  str = Field(default="", description="Diagnosis or clinical impression")
    plan:        str = Field(default="", description="Treatment plan, prescriptions, follow-up")


class SOAPValidation(BaseModel):
    """
    Validation result for a SOAP note.
    Flags missing or weak sections so the doctor can review.
    """
    is_complete: bool = Field(description="True if all 4 SOAP sections have content")
    missing_sections: List[str] = Field(default_factory=list, description="Names of empty sections")
    warnings: List[str] = Field(default_factory=list, description="Quality warnings")


class SOAPResult(BaseModel):
    """
    Complete result from the SOAP note pipeline.
    Combines the note, validation, and medical entity extraction.
    """
    soap_note: SOAPNote
    validation: SOAPValidation
    patient_info: Optional[dict] = Field(default=None, description="Extracted medical entities (from Stage 2)")
    transcript_text: str = Field(description="Original transcript used for generation")
    created_at: datetime = Field(default_factory=datetime.now)
    model_used: str = Field(default=MEDIFLOW_LLM_MODEL)
