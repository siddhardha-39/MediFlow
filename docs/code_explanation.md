# MediFlow Complete Codebase Explanation

This document provides a comprehensive walkthrough and explanation of every folder, subfolder, and code file in the MediFlow project.

---

## Workspace Root Files

* **[app.py](../app.py)**  
  The main entry point for the FastAPI backend server. It initializes the SQLite database schema on startup, mounts all API routers (`transcription`, `soap_notes`, `agents`, `clinical_workflow`), and starts the Uvicorn ASGI server on port `8000`.
* **[config.py](../config.py)**  
  Loads variables from the local `.env` environment file and exposes key configuration settings (like `MEDIFLOW_LLM_MODEL`, `MEDIFLOW_EMBEDDING_MODEL`, `MEDIFLOW_API_URL`, and `RAG_EMBEDDING_PROVIDER`) with robust defaults.
* **[main.py](../main.py)**  
  A lightweight execution helper that can be run to start the FastAPI server programmatically.
* **[requirements.txt](../requirements.txt)**  
  Defines all external Python package dependencies required by the system, including `fastapi`, `streamlit`, `langchain-ollama`, `langgraph`, `faster-whisper`, and `pydub`.
* **[test_transcription.py](../test_transcription.py)**  
  A script designed to test the transcription pipeline end-to-end. It generates a synthetic 3-second sine wave audio file, uploads it to the FastAPI transcription endpoint, and verifies that the pipeline processes the file without crashing.
* **[RUN_LOCAL.md](../RUN_LOCAL.md)**  
  Deployment instructions tuned for running the MediFlow system locally on consumer hardware (such as an 8 GB RAM laptop) using Ollama.

---

## 1. `transcription/` (Module 1 - Whisper Audio Transcription)
This directory manages audio preprocessing and transcription using a local Whisper model.

* **[transcription/__init__.py](../transcription/__init__.py)**  
  Marks the directory as a Python package.
* **[transcription/models.py](../transcription/models.py)**  
  Declares the Pydantic schemas `TranscriptSegment` (representing a single spoken segment with timestamps) and `TranscriptionResult` (containing the full text, metadata, and segments list).
* **[transcription/preprocessor.py](../transcription/preprocessor.py)**  
  Uses the `pydub` library to convert incoming audio uploads (MP3, M4A, etc.) to a standardized 16kHz mono WAV format to ensure optimal Whisper transcription performance.
* **[transcription/transcriber.py](../transcription/transcriber.py)**  
  Wraps the `faster-whisper` library. It downloads the base Whisper model and executes inference locally using int8 quantization on CPU.
* **[transcription/service.py](../transcription/service.py)**  
  An orchestrator class that coordinates the preprocessing and transcription pipeline, saving transcription results to disk as JSON for auditing.
* **[transcription/router.py](../transcription/router.py)**  
  Exposes the FastAPI HTTP endpoint `POST /api/transcribe` for file uploads, validating file formats and file sizes.

---

## 2. `soap_notes/` (Module 2 - SOAP Notes Generator)
This directory generates clinical SOAP (Subjective, Objective, Assessment, Plan) summaries from consultation transcripts.

* **[soap_notes/__init__.py](../soap_notes/__init__.py)**  
  Marks the directory as a Python package.
* **[soap_notes/models.py](../soap_notes/models.py)**  
  Defines the schema for `SOAPNote` sections and validation checks.
* **[soap_notes/prompts.py](../soap_notes/prompts.py)**  
  Stores the default system prompts used to direct the LLM to structure consultation transcripts into SOAP formats.
* **[soap_notes/generator.py](../soap_notes/generator.py)**  
  Communicates with the ChatOllama interface (`llama3.2:1b`) to generate the draft SOAP note sections.
* **[soap_notes/validator.py](../soap_notes/validator.py)**  
  Checks if any essential clinical sections (e.g., plan, vitals, subjective reports) are empty or missing from the generated note.
* **[soap_notes/service.py](../soap_notes/service.py)**  
  Orchestrates note generation, validation checking, and fallback flows.
* **[soap_notes/router.py](../soap_notes/router.py)**  
  FastAPI endpoint handlers (`POST /api/soap`) for note drafting.

---

## 3. `structured_outputs/` (Stage 2 - Medical Entity Extraction)
A pipeline designed to extract structured list entities (allergies, medications, conditions) from unstructured clinical text.

* **[structured_outputs/__init__.py](../structured_outputs/__init__.py)**  
  Marks the directory as a Python package.
* **[structured_outputs/models.py](../structured_outputs/models.py)**  
  Defines Pydantic models for structured clinical output data structures (`PatientInfo`, `ScoredEntity`, `ScoredPatientInfo`, `ExtractionResult`).
* **[structured_outputs/prompts.py](../structured_outputs/prompts.py)**  
  System prompts that instruct the LLM to return JSON-formatted lists and correct invalid JSON formats.
* **[structured_outputs/extractor.py](../structured_outputs/extractor.py)**  
  Interfaces with local models at `temperature=0` to extract raw entities.
* **[structured_outputs/parser.py](../structured_outputs/parser.py)**  
  A custom brace-depth parser that finds and extracts the first valid `{...}` JSON substring from LLM text responses, stripping markdown fences.
* **[structured_outputs/validator.py](../structured_outputs/validator.py)**  
  Validates parsed JSON against the Pydantic schema and coerces incorrect data types.
* **[structured_outputs/retry_handler.py](../structured_outputs/retry_handler.py)**  
  A loop runner that re-prompts the model up to 3 times with validation errors to fix malformed outputs.
* **[structured_outputs/confidence.py](../structured_outputs/confidence.py)**  
  A heuristic scoring engine calculating confidence metrics based on abbreviation risks, entity lengths, and field coverage.
* **[structured_outputs/utils.py](../structured_outputs/utils.py)**  
  Utility scripts and test wrappers for verifying extraction and parsing logic.

---

## 4. `clinical_workflow/` (Stage 4 - Interactive LangGraph Workflow)
This module orchestrates the state machine guiding transcripts through cleaning, formatting, validation, interactive physician reviews, and database persistence.

* **[clinical_workflow/__init__.py](../clinical_workflow/__init__.py)**  
  Marks the directory as a Python package.
* **[clinical_workflow/state.py](../clinical_workflow/state.py)**  
  Defines the TypedDict `ClinicalWorkflowState` containing state variables (e.g., transcripts, SOAP notes, entities, retries, approval flags).
* **[clinical_workflow/utils.py](../clinical_workflow/utils.py)**  
  Configures workflow-specific loggers.
* **[clinical_workflow/graph.py](../clinical_workflow/graph.py)**  
  Assembles and compiles the StateGraph, defining node connections and conditional routing.
* **[clinical_workflow/runner.py](../clinical_workflow/runner.py)**  
  A convenience file to execute the graph pipeline directly from Python.
* **[clinical_workflow/router.py](../clinical_workflow/router.py)**  
  FastAPI endpoint handlers (`/api/workflow/start`, `/api/workflow/review`) that track session histories using an in-memory checkpointer.
* **`nodes/`**  
  Each step in the LangGraph clinical graph is isolated as a node function:
  * **[clinical_workflow/nodes/transcriber.py](../clinical_workflow/nodes/transcriber.py)**: Processes audio inputs.
  * **[clinical_workflow/nodes/cleaner.py](../clinical_workflow/nodes/cleaner.py)**: Removes spoken filler words ("um", "uh", "you know") using regex filters.
  * **[clinical_workflow/nodes/soap_formatter.py](../clinical_workflow/nodes/soap_formatter.py)**: Generates draft SOAP notes and extracts entities.
  * **[clinical_workflow/nodes/validator.py](../clinical_workflow/nodes/validator.py)**: Assesses SOAP completeness and runs LanguageTool checks.
  * **[clinical_workflow/nodes/approval.py](../clinical_workflow/nodes/approval.py)**: Pauses execution to wait for physician review.
  * **[clinical_workflow/nodes/corrector.py](../clinical_workflow/nodes/corrector.py)**: Adjusts draft text using physician correction notes.
  * **[clinical_workflow/nodes/saver.py](../clinical_workflow/nodes/saver.py)**: Persists approved SOAP notes and entities.

---

## 5. `rag/` (Stage 4 RAG - Grounded Document Briefings)
Handles RAG indexing and document retrieval to provide grounded patient summaries.

* **[rag/__init__.py](../rag/__init__.py)**  
  Marks the directory as a Python package.
* **[rag/utils.py](../rag/utils.py)**  
  Exposes helper functions to load embedding models (`nomic-embed-text` via Ollama) and select vector database classes.
* **[rag/metadata.py](../rag/metadata.py)**  
  A keyword-based metadata tagger classifying clinical chunks into distinct domains (medications, allergies, clinical guidelines) for ChromaDB storage.
* **[rag/ingestor.py](../rag/ingestor.py)**  
  Loads patient PDF documents, performs chunking, calculates vector embeddings, and writes database vectors to disk.
* **[rag/retriever.py](../rag/retriever.py)**  
  Executes vector searches using Chroma, deduplicating results and formatting context strings.
* **[rag/query_engine.py](../rag/query_engine.py)**  
  Instructs local LLMs to compile structured doctor briefings using patient and guideline context.
* **[rag/service.py](../rag/service.py)**  
  The public entry point orchestrating ingestion and retrieval for both patients and guidelines.

---

## 6. `database/` (Module 5 - SQLite & PostgreSQL Persistence)
Manages the structured database used to store patient metadata and session logs.

* **[database/__init__.py](../database/__init__.py)**  
  Marks the directory as a Python package.
* **[database/models.py](../database/models.py)**  
  Pydantic model definitions mapping to patient and session record schema structures.
* **[database/db.py](../database/db.py)**  
  Initializes connections, creates schemas, and handles relational persistence for PostgreSQL (with SQLite fallback).

---

## 7. `db/` (Chroma Vector Store Compatibility Wrapper)
A compatibility layer mapping older Stage 3 ingestion components to the Stage 4 RAG engine.

* **[db/chroma_store.py](../db/chroma_store.py)**  
  Wraps vector store initialization and retrieval logic.
* **[db/ingest_patients.py](../db/ingest_patients.py)**  
  A CLI tool that scans for patient PDF files in the project folder and ingests them into Chroma database folders.

---

## 8. `agents/` (Patient History Summarizer)
Exposes the RAG assistant that creates briefings.

* **[agents/__init__.py](../agents/__init__.py)**  
  Marks the directory as a Python package.
* **[agents/Patient_history_summeriser.py](../agents/Patient_history_summeriser.py)**  
  Compiles patient summaries using vector database retrieval.
* **[agents/router.py](../agents/router.py)**  
  FastAPI endpoint handlers to retrieve briefings (`GET /api/patients/{id}/briefing`) and query hospital database statistics.

---

## 9. `ui/` (Streamlit Dashboard & Doctor Portal)
Houses the user-facing web dashboard.

* **[ui/app.py](../ui/app.py)**  
  A single-page Streamlit application connecting to the FastAPI backend. It features a premium, responsive **Glassmorphic dark interface** with frosted panels, visit history lists, and interactive dictation reviews.

---

## 10. `tests/` (Automated Test Suite)
Contains unit and integration tests.

* **[tests/test_stage4.py](../tests/test_stage4.py)**  
  Validates individual clinical graph nodes (cleaner, validator, SOAP generator) and graph compilation.
* **[tests/test_api_stage4.py](../tests/test_api_stage4.py)**  
  Runs integration tests on FastAPI server endpoints (briefings, workflow start, review iterations).
* **[tests/test_rag_upgrade.py](../tests/test_rag_upgrade.py)**  
  Tests keyword tagging, vector store ingestion, changes tracking, and RAG retrieval.
* **[tests/test_local_demo_config.py](../tests/test_local_demo_config.py)**  
  Verifies default server configuration settings and fallback logic when LLM services are offline.
