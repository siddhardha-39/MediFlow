# MediFlow Demo Script

This is a practical 3 to 5 minute walkthrough for the current v1 branch.

## 1. Start the app

1. Start the FastAPI backend.
2. Start the Streamlit frontend.
3. Enter your Gemini API key in the UI runtime key field.

## 2. Patient History Briefing

1. Open the Patient History tab.
2. Select the synthetic patient `Rajesh Kumar`.
3. Click Generate Briefing.
4. Point out that the briefing is grounded in the synthetic PDF record and ChromaDB retrieval.

## 3. Clinical Documentation Workflow

1. Open the Clinical Documentation tab.
2. Paste a short consultation transcript.
3. Generate the SOAP draft.
4. Show the validator output and explain that the workflow only proceeds when the note is complete enough.
5. Reject the first draft with feedback such as "Assessment should mention chest pain follow-up."
6. Show the correction loop and the updated SOAP note.
7. Approve the final note.
8. Show the saved session and note that it was persisted to SQLite.

## 4. Hospital Intelligence Dashboard

1. Open the Hospital Intelligence Dashboard tab.
2. Show the consultation count and patient totals.
3. Ask a simple dashboard question if desired.

## 5. Closing Line

MediFlow demonstrates how LangGraph state, RAG, human review, and a small API/UI stack can be combined into a clean educational agentic workflow.
