# soap_notes/generator.py
"""
SOAP note generator using Ollama LLM.

Takes transcript text -> sends to LLM with SOAP prompt -> returns raw output.
Parsing and validation are handled separately (same pattern as Stage 2).
"""
import json
import logging
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from config import MEDIFLOW_LLM_MODEL
from soap_notes.prompts import SOAP_GENERATION_PROMPT
from soap_notes.models import SOAPNote

logger = logging.getLogger("soap_notes.generator")

# Same model as Stage 2 — deterministic output
llm = ChatOllama(model=MEDIFLOW_LLM_MODEL, temperature=0.0)


def generate_soap_raw(transcript_text: str) -> str:
    """Send transcript to LLM and get raw SOAP note response."""
    prompt = SOAP_GENERATION_PROMPT.format(transcript_text=transcript_text)
    logger.info("Generating SOAP note from transcript (%d chars)", len(transcript_text))

    response = llm.invoke([HumanMessage(content=prompt)])
    raw = response.content.strip()
    logger.debug("Raw SOAP output: %s", raw[:200])
    return raw


def parse_soap(raw: str) -> SOAPNote:
    """
    Parse raw LLM output into a SOAPNote.
    Reuses the same JSON extraction logic from Stage 2.
    """
    # Strip markdown fences if present
    import re
    cleaned = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", raw).strip()

    # Find JSON object
    start = cleaned.find("{")
    if start == -1:
        logger.warning("No JSON found in output, returning empty SOAP note")
        return SOAPNote()

    depth = 0
    for i, ch in enumerate(cleaned[start:], start=start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        if depth == 0:
            json_str = cleaned[start:i+1]
            break
    else:
        logger.warning("Unclosed JSON, returning empty SOAP note")
        return SOAPNote()

    try:
        data = json.loads(json_str)
        return SOAPNote(**data)
    except (json.JSONDecodeError, Exception) as e:
        logger.error("Failed to parse SOAP JSON: %s", e)
        return SOAPNote()
