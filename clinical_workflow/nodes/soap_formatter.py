# clinical_workflow/nodes/soap_formatter.py
"""
Node: Generate a SOAP note from the cleaned transcript.

LANGGRAPH CONCEPT — RETRIES VIA GRAPH EDGES:
    In plain Python, you'd write a for-loop for retries.
    In LangGraph, retries happen through the GRAPH STRUCTURE:
    - soap_formatter generates a note
    - validator checks it
    - if invalid, the conditional edge routes BACK to soap_formatter
    - the state carries retry_count so we know when to give up

    This is more powerful than a for-loop because:
    - Each retry is logged as a separate graph step
    - You can inspect what happened at each attempt
    - The graph can be visualized showing the retry path
"""
import logging
import re
from typing import Optional
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from llm_factory import get_chat_llm
from clinical_workflow.state import ClinicalWorkflowState
from clinical_workflow.utils import parse_llm_json
from clinical_workflow.prompts import SOAP_GENERATION_PROMPT

logger = logging.getLogger("workflow.node.soap_formatter")

_ENTITY_PATTERNS = {
    "conditions": [
        r"\bhypertension\b",
        r"\bhigh blood pressure\b",
        r"\bdiabetes\b",
        r"\btype 2 diabetes\b",
        r"\basthma\b",
        r"\bcopd\b",
        r"\bpneumonia\b",
        r"\bchronic kidney disease\b",
    ],
    "allergies": [
        r"\bpenicillin\b",
        r"\baspirin\b",
        r"\bsulfa\b",
        r"\blatex\b",
        r"\bnkda\b",
        r"\ballergic to ([^.\n;,]+)",
    ],
    "medications": [
        r"\bmetformin\b",
        r"\bamlodipine\b",
        r"\baspirin\b",
        r"\binsulin\b",
        r"\btylenol\b",
        r"\blisinopril\b",
        r"\batorvastatin\b",
        r"\bibuprofen\b",
        r"\btakes? ([^.\n;,]+)",
        r"\bcurrently taking ([^.\n;,]+)",
        r"\bon ([^.\n;,]+)\b",
    ],
    "symptoms": [
        r"\bchest pain\b",
        r"\bshortness of breath\b",
        r"\bfever\b",
        r"\bcough\b",
        r"\bheadache\b",
        r"\bnausea\b",
        r"\bvomiting\b",
        r"\bdizziness\b",
        r"\bfatigue\b",
    ],
}


def soap_formatter_node(state: ClinicalWorkflowState, config: RunnableConfig = None) -> dict:
    """
    Generate SOAP note from cleaned transcript using LLM.

    Reads:  state["clean_transcript"], state["retry_count"]
    Writes: state["soap_*"] fields, increments retry_count
    """
    api_key: Optional[str] = (config or {}).get("configurable", {}).get("api_key")
    llm = get_chat_llm(temperature=0.0, api_key=api_key)

    transcript = state.get("clean_transcript", "") or state.get("raw_transcript", "")
    retry_count = state.get("retry_count", 0)

    logger.info("SOAP_FORMATTER: Attempt %d, transcript = %d chars", retry_count + 1, len(transcript))

    if not transcript.strip():
        logger.warning("SOAP_FORMATTER: Empty transcript")
        return {
            "soap_subjective": "No transcript available",
            "soap_objective": "No transcript available",
            "soap_assessment": "No transcript available",
            "soap_plan": "No transcript available",
            "retry_count": retry_count + 1,
        }

    # Build prompt — on retries, add emphasis on completing ALL sections
    prompt_text = SOAP_GENERATION_PROMPT.format(transcript_text=transcript)
    if retry_count > 0:
        prompt_text += (
            "\n\nIMPORTANT: Your previous attempt was missing sections. "
            "You MUST fill ALL four sections: subjective, objective, assessment, plan. "
            "If information is not available, write 'Not documented in this visit'."
        )

    try:
        response = llm.invoke([HumanMessage(content=prompt_text)])
        raw = response.content.strip()

        # Parse JSON from response
        soap = parse_llm_json(raw)

        logger.info(
            "SOAP_FORMATTER: S=%d O=%d A=%d P=%d chars",
            len(soap.get("subjective", "")),
            len(soap.get("objective", "")),
            len(soap.get("assessment", "")),
            len(soap.get("plan", "")),
        )

        result = {
            "soap_subjective": soap.get("subjective", ""),
            "soap_objective": soap.get("objective", ""),
            "soap_assessment": soap.get("assessment", ""),
            "soap_plan": soap.get("plan", ""),
            "retry_count": retry_count + 1,
        }

        # Extract entities only on first attempt — transcript doesn't change
        # on retries, so re-extracting wastes ~8s on an extra LLM call
        if retry_count == 0:
            result.update(_extract_entities(transcript, api_key=api_key))

        return result

    except Exception as e:
        logger.error("SOAP_FORMATTER: LLM failed - %s", e)
        return {
            "soap_subjective": "",
            "soap_objective": "",
            "soap_assessment": "",
            "soap_plan": "",
            "retry_count": retry_count + 1,
        }




def _extract_entities(transcript: str, api_key: Optional[str] = None) -> dict:
    """Extract medical entities using Stage 2 pipeline."""
    local_entities = _extract_entities_local(transcript)
    if not api_key:
        return local_entities

    try:
        from structured_outputs.retry_handler import run_with_retry
        result = run_with_retry(transcript)
        if result.success and result.patient_info:
            merged = {
                "conditions": result.patient_info.conditions,
                "medications": result.patient_info.medications,
                "allergies": result.patient_info.allergies,
                "symptoms": result.patient_info.symptoms,
            }
            return _merge_entities(local_entities, merged)
    except Exception as e:
        logger.warning("Entity extraction failed: %s", e)

    return local_entities


def _extract_entities_local(transcript: str) -> dict:
    """Extract a small set of common entities directly from the transcript."""
    lower = transcript.lower()
    entities = {
        "conditions": [],
        "medications": [],
        "allergies": [],
        "symptoms": [],
    }

    for field, patterns in _ENTITY_PATTERNS.items():
        values = []
        for pattern in patterns:
            for match in re.finditer(pattern, lower, flags=re.IGNORECASE):
                value = match.group(1) if match.lastindex else match.group(0)
                cleaned = _clean_entity_candidate(value)
                if cleaned and cleaned not in values:
                    values.append(cleaned)
        entities[field] = values

    return entities


def _clean_entity_candidate(value: str) -> str:
    """Trim filler phrases, dose text, and trailing conjunctions from a candidate."""
    cleaned = value.strip().lower()
    cleaned = re.split(r"\b(?:and|but|with|for)\b", cleaned, maxsplit=1)[0]
    cleaned = re.split(r"[\.,;:\n\t]", cleaned, maxsplit=1)[0]
    cleaned = re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|units?|tablet(?:s)?|capsule(?:s)?|puff(?:s)?|times?|daily|bid|tid|qhs|q\d+h)\b.*$",
        "",
        cleaned,
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -_")
    return cleaned


def _merge_entities(primary: dict, fallback: dict) -> dict:
    """Merge entity lists while preserving order and removing duplicates."""
    merged = {}
    for field in ["conditions", "medications", "allergies", "symptoms"]:
        seen = set()
        combined = []
        for source in (primary.get(field, []), fallback.get(field, [])):
            for item in source:
                normalized = item.strip()
                if normalized and normalized.lower() not in seen:
                    seen.add(normalized.lower())
                    combined.append(normalized)
        merged[field] = combined
    return merged
