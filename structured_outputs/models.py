# models.py
from pydantic import BaseModel, Field
from typing import List, Optional


class ScoredEntity(BaseModel):
    """A medical entity with an associated confidence score."""
    value: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class PatientInfo(BaseModel):
    """
    Core structured schema for extracted patient medical information.
    All fields are optional to gracefully handle sparse clinical notes.
    """
    conditions:  List[str] = Field(default_factory=list, description="Diagnosed medical conditions")
    allergies:   List[str] = Field(default_factory=list, description="Known allergies")
    medications: List[str] = Field(default_factory=list, description="Current medications")
    symptoms:    List[str] = Field(default_factory=list, description="Reported symptoms")


class ScoredPatientInfo(BaseModel):
    """
    PatientInfo with per-entity confidence scores.
    Produced by confidence.py after extraction and validation.
    """
    conditions:  List[ScoredEntity] = Field(default_factory=list)
    allergies:   List[ScoredEntity] = Field(default_factory=list)
    medications: List[ScoredEntity] = Field(default_factory=list)
    symptoms:    List[ScoredEntity] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction_notes: Optional[str] = None


class ExtractionResult(BaseModel):
    """
    Full result envelope returned by the pipeline.
    Carries the validated object, raw output, and pipeline metadata.
    """
    success: bool
    patient_info: Optional[PatientInfo] = None
    scored_info:  Optional[ScoredPatientInfo] = None
    raw_output:   Optional[str] = None
    error:        Optional[str] = None
    retries_used: int = 0