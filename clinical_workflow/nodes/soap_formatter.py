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
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from config import MEDIFLOW_LLM_MODEL
from clinical_workflow.state import ClinicalWorkflowState
from clinical_workflow.utils import parse_llm_json
from soap_notes.prompts import SOAP_GENERATION_PROMPT

logger = logging.getLogger("workflow.node.soap_formatter")

# Same model, deterministic
llm = ChatOllama(model=MEDIFLOW_LLM_MODEL, temperature=0.0)


def soap_formatter_node(state: ClinicalWorkflowState) -> dict:
    """
    Generate SOAP note from cleaned transcript using LLM.

    Reads:  state["clean_transcript"], state["retry_count"]
    Writes: state["soap_*"] fields, increments retry_count
    """
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
            result.update(_extract_entities(transcript))

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




def _extract_entities(transcript: str) -> dict:
    """Extract medical entities using Stage 2 pipeline."""
    try:
        from structured_outputs.retry_handler import run_with_retry
        result = run_with_retry(transcript)
        if result.success and result.patient_info:
            return {
                "conditions": result.patient_info.conditions,
                "medications": result.patient_info.medications,
                "allergies": result.patient_info.allergies,
                "symptoms": result.patient_info.symptoms,
            }
    except Exception as e:
        logger.warning("Entity extraction failed: %s", e)

    return {"conditions": [], "medications": [], "allergies": [], "symptoms": []}
