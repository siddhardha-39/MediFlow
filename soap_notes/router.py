# soap_notes/router.py
"""
FastAPI endpoint for SOAP note generation.

POST /api/soap  — accepts transcript text, returns structured SOAP note.
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from soap_notes.service import generate_soap_note
from soap_notes.models import SOAPResult

logger = logging.getLogger("soap_notes.router")

router = APIRouter(prefix="/api", tags=["soap-notes"])


class SOAPRequest(BaseModel):
    """Request body for SOAP note generation."""
    transcript_text: str


@router.post("/soap", response_model=SOAPResult)
async def create_soap_note(request: SOAPRequest):
    """
    Generate a structured SOAP note from transcript text.

    Usage:
        POST /api/soap
        {"transcript_text": "Patient reports chest pain..."}
    """
    if not request.transcript_text.strip():
        raise HTTPException(status_code=400, detail="transcript_text cannot be empty")

    try:
        result = generate_soap_note(request.transcript_text)
        return result
    except Exception as e:
        logger.error("SOAP generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"SOAP generation failed: {str(e)}")
