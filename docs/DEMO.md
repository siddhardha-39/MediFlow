# MediFlow E2E Demo Walkthrough Script

This script provides a 3–5 minute deterministic walk-through to demo MediFlow to recruiters or technical interviewers.

---

## 1. Project Introduction (60 Seconds)
* **Goal**: "MediFlow is a local-first clinical documentation and hospital intelligence platform. It reduces doctor burnout by automating patient record briefings and SOAP documentation generation using LangGraph stateful workflows, local LLMs, RAG, and LanguageTool."
* **Core Highlight**: "The architecture runs completely locally to minimize unnecessary external data transmission in this educational project. It features a robust PostgreSQL storage module with SQLite fallback and isolates external grammar service checks to degrade gracefully if they are offline."

---

## 2. Step-by-Step Walkthrough (2 Minutes)

### Step 1: Patient History Briefing
1. **Action**: Open the UI at `http://localhost:8501`, and click the **Patient History** tab.
2. **Context**: Select the mock patient `Rajesh Kumar`.
3. **Execution**: The system executes a RAG search in ChromaDB across his past medical PDFs (e.g. `PT-2024-001-Rajesh-Kumar.pdf`) to retrieve chronic conditions (diabetes), allergies (penicillin), and current medications (metformin).
4. **Outcome**: Displays a structured patient history card summarizing key context before the visit starts.

### Step 2: Dictation & Consultation Input
1. **Action**: Switch to the **Consultation & SOAP Generator** tab.
2. **Execution**: Enter a consultation transcript:
   > *"Good morning, Mr. Kumar. You have a fever for three days. Let's record vitals: blood pressure is 120/80, temperature is 101.5. I'll prescribe Tylenol 500mg and advise a chest X-ray. Follow up in 3 days."*
3. **Trigger**: Click **Generate SOAP Note**.

### Step 3: Stateful LangGraph Workflow Execution
1. **Transcription Cleanup**: Cleaner node filters out filler words ("um", "uh", "like") from the text.
2. **SOAP Note Formatting**: The LLM extracts symptoms, vitals, prescriptions, and formats them into four strict sections: *Subjective (S), Objective (O), Assessment (A), and Plan (P)*.
3. **Entity Extraction**: Medical entities (allergies, medications, chronic conditions) are extracted.
4. **Clinical Completeness Validation**: The Validator node asserts that all SOAP sections are filled.
5. **Language & Grammar Quality Check**: LanguageTool checks each section's text. It flags suggestions (e.g., recommends replacing *"an patient"* with *"a patient"*).
6. **Interrupt for Approval**: The workflow pauses, prompting the doctor to review the draft.

### Step 4: Doctor Review, Correction Loop, & Persist
1. **Action**: The doctor modifies the generated text (e.g., adding a detail) and clicks **Approve and Save to EHR**.
2. **Execution**: The graph resumes, saves the records to PostgreSQL (or SQLite if PostgreSQL is offline), and displays the database session ID.

### Step 5: Operational Telemetry
1. **Action**: Open the **Hospital Intelligence Dashboard** tab.
2. **Outcome**: The total patient count, consultation metrics, and aggregate conditions immediately update to reflect the newly saved consultation.

---

## 3. Graceful Failure Demonstration (Offline Failovers)
1. **LanguageTool Offline**: Stop the LanguageTool service. Click regenerate. The UI displays: *"⚠️ LanguageTool service is offline (timeout). Grammar check skipped."* The workflow completes successfully without crashing.
2. **Ollama Offline**: If the local LLM is shut down, the UI falls back to deterministic mock values and alerts the user, ensuring the app remains navigable.
