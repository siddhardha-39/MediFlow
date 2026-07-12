# agents/router.py
"""
FastAPI router for the Patient History Summarizer Agent and Hospital Dashboard.

Exposes endpoints to list patients, get patient history, and query hospital stats.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from llm_factory import get_chat_llm
from langchain_core.messages import HumanMessage

from agents.Patient_history_summeriser import summarize_patient
from database.db import (
    list_patients,
    get_patient,
    get_patient_by_name,
    get_patient_sessions,
    get_patient_history,
    get_db_stats
)

logger = logging.getLogger("agents.router")

# Patient router
router = APIRouter(prefix="/api/patients", tags=["patient-summarizer"])

# Dashboard router
dashboard_router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class BriefingResponse(BaseModel):
    """Response schema for patient history briefing."""
    patient_id: str
    briefing: str


class AskRequest(BaseModel):
    """Request body for dashboard Q&A."""
    query: str


# ── Patient Router Endpoints ──────────────────────────────────────────────────

@router.get("", response_model=List[dict])
async def get_all_patients():
    """List all patients in the database."""
    try:
        return list_patients()
    except Exception as e:
        logger.error("Failed to list patients: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{patient_id}/briefing", response_model=BriefingResponse)
async def get_patient_briefing(
    patient_id: str,
    x_gemini_api_key: Optional[str] = Header(None),
):
    """
    Generate a structured 1-page clinical briefing of a patient's medical history.

    Queries ChromaDB vector store for the patient's records and uses the
    Gemini LLM to compile the briefing. Pass the Gemini API key via the
    X-Gemini-API-Key header.
    """
    if not patient_id.strip():
        raise HTTPException(status_code=400, detail="patient_id cannot be empty")

    logger.info("Generating briefing for patient: %s", patient_id)
    try:
        briefing = summarize_patient(patient_id, api_key=x_gemini_api_key)
        return BriefingResponse(patient_id=patient_id, briefing=briefing)
    except Exception as e:
        logger.error("Failed to generate patient briefing for %s: %s", patient_id, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Patient briefing generation failed: {str(e)}"
        )


@router.get("/{patient_id}/sessions", response_model=List[dict])
async def get_sessions(patient_id: str):
    """List all sessions for a specific patient by ID, name, or MRN."""
    try:
        p = None
        if patient_id.isdigit():
            p = get_patient(int(patient_id))
        if not p:
            for pat in list_patients():
                if pat.get("medical_record_number") == patient_id or pat["name"].lower() == patient_id.lower():
                    p = pat
                    break
        if not p:
            p = get_patient_by_name(patient_id)
        
        if not p:
            raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")
        
        return get_patient_sessions(p["id"])
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch sessions: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{patient_id}/history")
async def get_history(patient_id: str):
    """Get the formatted patient history string."""
    try:
        p = None
        if patient_id.isdigit():
            p = get_patient(int(patient_id))
        if not p:
            for pat in list_patients():
                if pat.get("medical_record_number") == patient_id or pat["name"].lower() == patient_id.lower():
                    p = pat
                    break
        if not p:
            p = get_patient_by_name(patient_id)
            
        if not p:
            raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")
            
        history = get_patient_history(p["id"])
        return {"patient_id": patient_id, "history": history}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch patient history: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ── Dashboard Helper & Endpoints ──────────────────────────────────────────────


@dashboard_router.get("/stats")
async def get_dashboard_stats():
    """Retrieve aggregated operational hospital stats."""
    try:
        return get_db_stats()
    except Exception as e:
        logger.error("Failed to compile dashboard stats: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


DASHBOARD_QA_PROMPT = """You are a clinical database analyst assistant for MediFlow Hospital Intelligence.

Here is the current aggregated operational statistics from the hospital database:
- Total Patients: {total_patients}
- Total Consultation Sessions: {total_sessions}
- Top Diagnosed Conditions: {top_conditions}
- Top Prescribed Medications: {top_medications}
- Known Allergies Summary: {allergies_summary}

Based on this database summary, answer the manager's query in clear, professional natural language. Keep the answer concise (under 2 sentences) and completely factual based on the stats provided. If the information to answer their query is not present in the stats, state that clearly.

Manager's Query: {query}
"""


@dashboard_router.post("/ask")
async def ask_dashboard(
    request: AskRequest,
    x_gemini_api_key: Optional[str] = Header(None),
):
    """Answer hospital management queries using Gemini and database statistics."""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    stats = get_db_stats()
    try:
        prompt = DASHBOARD_QA_PROMPT.format(
            total_patients=stats["total_patients"],
            total_sessions=stats["total_sessions"],
            top_conditions=stats["top_conditions"],
            top_medications=stats["top_medications"],
            allergies_summary=stats["allergies_summary"],
            query=request.query
        )
        llm = get_chat_llm(temperature=0.0, api_key=x_gemini_api_key)
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"query": request.query, "answer": response.content.strip()}
    except Exception as e:
        logger.error("Dashboard QA failed: %s", e)
        return {
            "query": request.query,
            "answer": f"Gemini service unavailable. Direct stats: {stats['total_patients']} patients, {stats['total_sessions']} sessions."
        }
