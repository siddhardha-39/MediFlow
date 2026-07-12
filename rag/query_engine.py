from __future__ import annotations

from config import MEDIFLOW_LLM_MODEL
from llm_factory import get_chat_llm
from .utils import get_logger

logger = get_logger("rag.query_engine")


class RAGQueryEngine:
    """Strict grounded answer generation over retrieved clinical context."""

    def __init__(self, model_name: str = MEDIFLOW_LLM_MODEL, temperature: float = 0.0):
        self.llm = get_chat_llm(model_name=model_name, temperature=temperature)

    def _invoke_or_default(self, prompt: str, default: str) -> str:
        try:
            from langchain_core.messages import HumanMessage
            response = self.llm.invoke([HumanMessage(content=prompt)])
            text = (response.content if hasattr(response, "content") else str(response)).strip()
            return text or default
        except Exception as exc:
            logger.error("RAG generation failed: %s", exc)
            return default

    def generate_answer(self, query: str, context: str) -> str:
        """Answer from retrieved context only."""
        if not context.strip():
            return "I don't know based on the provided clinical documents."

        prompt = f"""
You are a strict clinical document assistant.

Rules:
1. Answer only from the provided context.
2. If the answer is missing, say: "I don't know based on the provided clinical documents."
3. Include source/page references when the context provides them.
4. Do not invent diagnoses, medications, allergies, tests, or recommendations.

Context:
{context}

Question: {query}

Answer:
"""
        return self._invoke_or_default(
            prompt,
            "I don't know based on the provided clinical documents.",
        )

    def generate_patient_briefing(self, patient_context: str, guideline_context: str = "") -> str:
        """Generate the doctor-facing patient briefing with optional guideline grounding."""
        if not patient_context.strip():
            return (
                "PATIENT BRIEFING\n"
                "================\n"
                "Name: Unknown\n"
                "Age: Unknown | Blood Group: Unknown\n\n"
                "[CRITICAL ALERTS]\n"
                "- No patient record context was found.\n\n"
                "[CHRONIC CONDITIONS]\n"
                "- Unknown\n\n"
                "[CURRENT MEDICATIONS]\n"
                "- Unknown\n\n"
                "[RECENT TESTS (KEY FINDINGS ONLY)]\n"
                "- Unknown\n\n"
                "[RECENT VISITS SUMMARY]\n"
                "- Unknown\n\n"
                "[DOCTOR'S FOCUS FOR TODAY]\n"
                "- Review source records before clinical decision-making."
            )

        prompt = f"""
You are a clinical assistant helping a doctor prepare for a consultation.

Use ONLY the patient record context below. Use guideline context only for general safety framing if it is provided.
Do not invent patient facts. If a field is not found, write "Unknown".
Include compact source references in brackets when important facts come from referenced chunks.

Format the response EXACTLY like this:

PATIENT BRIEFING
================
Name: [name]
Age: [age] | Blood Group: [blood group]

[CRITICAL ALERTS]
- [Allergies, red flags, contraindications, or "None found"]

[CHRONIC CONDITIONS]
- [condition + source reference, or "Unknown"]

[CURRENT MEDICATIONS]
- [drug + dose + frequency + source reference, or "Unknown"]

[RECENT TESTS (KEY FINDINGS ONLY)]
- [abnormal or clinically important result + source reference, or "Unknown"]

[RECENT VISITS SUMMARY]
- [last 2-3 visits in one line each, or "Unknown"]

[DOCTOR'S FOCUS FOR TODAY]
- [2-3 concrete focus points grounded in the record]

PATIENT RECORD CONTEXT:
{patient_context}

GUIDELINE CONTEXT:
{guideline_context or "No guideline context retrieved."}
"""
        return self._invoke_or_default(
            prompt,
            "PATIENT BRIEFING\n================\nName: Unknown\nAge: Unknown | Blood Group: Unknown\n\n[CRITICAL ALERTS]\n- Unable to generate briefing because the local LLM was unavailable.",
        )
