# Patient History Summarizer

This helper module powers the patient briefing feature used by the Streamlit UI and FastAPI backend.

## What it does

- Retrieves patient-scoped context from the RAG service.
- Passes the context into Gemini through the shared chat factory.
- Returns a concise, doctor-facing briefing string.

## Current implementation

The active code path is `agents/Patient_history_summeriser.py`, which calls `rag.service.generate_grounded_patient_briefing(patient_id, api_key=...)`.

That path uses:

- synthetic patient PDFs
- HuggingFace embeddings
- ChromaDB persistence
- runtime Gemini API-key injection

## Why it still exists

It is a small, useful compatibility boundary between the briefing endpoint and the underlying RAG pipeline.
