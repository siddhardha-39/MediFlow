from __future__ import annotations
import sys
from pathlib import Path

# Add project root to sys.path so we can import from document_loading and db
sys.path.append(str(Path(__file__).parent.parent))

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import StrOutputParser

from config import MEDIFLOW_LLM_MODEL
from rag.service import generate_grounded_patient_briefing

MEDICAL_SUMMARY_PROMPT = """You are a clinical assistant helping doctors prepare for patient consultations.

Given the relevant extracts from the patient's medical record below, generate a structured 1-page briefing that a doctor can read in under 30 seconds.

Format your response EXACTLY like this:

PATIENT BRIEFING
================
Name: [name]
Age: [age] | Blood Group: [blood group]

[CRITICAL ALERTS]
- [List allergies and anything life-threatening first]

[CHRONIC CONDITIONS]
- [List all chronic conditions with year diagnosed]

[CURRENT MEDICATIONS]
- [Drug name + dose + frequency]

[RECENT TESTS (KEY FINDINGS ONLY)]
- [Only flag abnormal or concerning results]

[RECENT VISITS SUMMARY]
- [Last 2-3 visits in one line each]

[DOCTOR'S FOCUS FOR TODAY]
- [2-3 bullet points on what needs attention based on the record]

---
RELEVANT PATIENT RECORD EXTRACTS:
{patient_record}
"""

def generate_patient_briefing(
    patient_record_context: str,
    *,
    model_name: str = MEDIFLOW_LLM_MODEL,
    temperature: float = 0.0,
) -> str:
    # LLM
    llm = ChatOllama(model=model_name, temperature=temperature)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a clinical assistant. Always follow the exact format given. Never add extra commentary."),
        ("human", MEDICAL_SUMMARY_PROMPT),
    ])
    
    # Doctor Summary Generation
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"patient_record": patient_record_context})

def summarize_patient(
    patient_id: str,
    *,
    model_name: str = MEDIFLOW_LLM_MODEL,
) -> str:
    """
    Generate a grounded doctor briefing from the upgraded RAG pipeline.

    The public return type remains a plain string so the existing FastAPI
    response shape stays unchanged.
    """
    return generate_grounded_patient_briefing(patient_id, model_name=model_name)

if __name__ == "__main__":
    # Test with the ID of our mock patient instead of the file path
    patient_id = "PT-2024-001-Rajesh-Kumar"
    briefing = summarize_patient(patient_id)
    print("\n" + "="*50)
    print(briefing)
