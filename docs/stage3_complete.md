# MediFlow Stage 3 - Complete Documentation

> **Stage:** 3 (Complete)  
> **Date:** May 2026  
> **Status:** All 7 modules built, tested, and operational

---

## Architecture Overview

```
Doctor Audio (.wav / .mp3)
    |
    v
[Module 1: Transcription]    transcription/
    |  Whisper (faster-whisper)
    v
Transcript Text
    |
    v
[Module 2: SOAP Notes]       soap_notes/
    |  LLM (llama3.2:1b)
    v
Structured SOAP Note  +  Medical Entities (Stage 2)
    |
    v
[Module 3: Tools]             tools/
    |  LangChain @tool wrappers
    v
[Module 4: Agent]             agent/
    |  ReAct agent loop
    v
[Module 5: Database]          database/
    |  SQLite (mediflow.db)
    v
[Module 6: Memory]            memory/
    |  Session + Patient context
    v
[Module 7: Workflow]          workflow/
    |  LangGraph pipeline
    v
Complete Clinical Record
```

---

## Project Structure

```
MediFlow/
|-- app.py                      # FastAPI entry point
|-- test_full_pipeline.py       # End-to-end test
|-- test_transcription.py       # Module 1 test
|-- mediflow.db                 # SQLite database (auto-created)
|
|-- transcription/              # Module 1 - Whisper transcription
|   |-- models.py               #   TranscriptSegment, TranscriptionResult
|   |-- preprocessor.py         #   Any audio -> 16kHz mono WAV
|   |-- transcriber.py          #   faster-whisper wrapper
|   |-- service.py              #   Pipeline orchestrator
|   |-- router.py               #   POST /api/transcribe
|
|-- soap_notes/                 # Module 2 - SOAP note generation
|   |-- models.py               #   SOAPNote, SOAPValidation, SOAPResult
|   |-- prompts.py              #   SOAP generation prompt
|   |-- generator.py            #   LLM SOAP generation + JSON parsing
|   |-- validator.py            #   Completeness validation
|   |-- service.py              #   Pipeline orchestrator
|   |-- router.py               #   POST /api/soap
|
|-- tools/                      # Module 3 - LangChain tools
|   |-- clinical_tools.py       #   5 tools: transcribe, soap, validate, save, history
|
|-- agent/                      # Module 4 - Documentation agent
|   |-- prompts.py              #   System prompt
|   |-- clinical_agent.py       #   ReAct agent with tool calling
|
|-- database/                   # Module 5 - SQLite integration
|   |-- models.py               #   Patient, Session Pydantic models
|   |-- db.py                   #   CRUD operations + patient history
|
|-- memory/                     # Module 6 - Session memory
|   |-- session_memory.py       #   ConversationMemory, PatientContext, SessionContext
|
|-- workflow/                   # Module 7 - LangGraph orchestration
|   |-- pipeline.py             #   StateGraph with conditional retry
|
|-- structured_outputs/         # Stage 2 - Medical entity extraction
|-- docs/                       # Documentation
```

---

## Module Details

### Module 1 - Transcription
- **Tech:** faster-whisper (base model, CPU, int8)
- **Input:** Audio file (WAV, MP3, M4A, etc.)
- **Output:** TranscriptionResult with timestamped segments
- **API:** POST /api/transcribe (file upload)

### Module 2 - SOAP Notes
- **Tech:** ChatOllama (llama3.2:1b, temperature=0)
- **Input:** Transcript text
- **Output:** SOAPResult (SOAP note + validation + medical entities)
- **API:** POST /api/soap (JSON body)
- **Integrates:** Stage 2 medical entity extraction

### Module 3 - LangChain Tools
5 tools available to the agent:
1. `transcribe_audio` - Convert audio to text
2. `generate_soap` - Create SOAP notes
3. `validate_note` - Check note completeness
4. `save_patient_record` - Save to database
5. `fetch_patient_history` - Retrieve past visits

### Module 4 - Clinical Agent
- **Pattern:** ReAct (Reasoning + Acting)
- **Flow:** Think -> Call Tool -> Observe -> Repeat -> Respond
- **Memory:** Maintains session context across interactions
- **Safety:** Max 10 iterations to prevent infinite loops

### Module 5 - Database
- **Tech:** SQLite (plain SQL, no ORM)
- **Tables:** patients, sessions
- **Features:** CRUD, patient search, history retrieval
- **Migration ready:** Same SQL syntax works with PostgreSQL

### Module 6 - Memory
Three layers:
1. **ConversationMemory** - Current session messages
2. **PatientContext** - Cached patient history from DB
3. **SessionContext** - Combines both for agent prompt

### Module 7 - LangGraph Workflow
- **Graph:** generate_soap -> validate -> (retry or proceed) -> extract -> save
- **Retry:** Up to 2 retries on SOAP validation failure
- **State:** TypedDict flowing through all nodes
- **Branching:** Conditional edges based on validation result

---

## Test Results

```
TEST 1: Database         [OK] - 2 patients created, CRUD working
TEST 2: SOAP Generation  [OK] - Both patients processed successfully
TEST 3: Database Save    [OK] - Sessions saved with SOAP notes + entities
TEST 4: History          [OK] - Full patient history retrieved
TEST 5: Memory           [OK] - Context combines history + transcript + conversation
TEST 6: LangGraph        [OK] - Pipeline ran with retry logic
                               (retry triggered due to model limitations, saved with warnings)
```

---

## Key Dependencies

| Package | Purpose |
|---|---|
| faster-whisper | Local Whisper transcription |
| fastapi + uvicorn | REST API |
| langchain-ollama | Ollama LLM interface |
| langchain-core | Tools, messages, prompts |
| langgraph | Workflow orchestration |
| pydantic | Schema validation |
| pydub + audioop-lts | Audio preprocessing |
| sqlite3 | Database (built-in) |

---

## How to Run

### Start the API
```bash
python app.py
# Server at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Run all tests
```bash
python test_full_pipeline.py    # Tests modules 2-7
python test_transcription.py    # Tests module 1 (needs server running)
```

### Run the LangGraph pipeline directly
```python
from workflow.pipeline import run_pipeline

result = run_pipeline(
    transcript="Patient reports chest pain...",
    patient_name="John Doe",
)
print(result)
```

---

## Known Limitations

| Issue | Cause | Solution |
|---|---|---|
| SOAP JSON sometimes unclosed | llama3.2:1b too small for complex JSON | Upgrade to larger model when RAM allows |
| Conditions field often empty | Model misses diagnosis entities | Larger model or pre-processing |
| LangGraph retry needed ~50% | Same model limitation | Expected with 1B model |
| Agent tool calling unreliable | Small models struggle with tool schemas | Works better with 3B+ models |
