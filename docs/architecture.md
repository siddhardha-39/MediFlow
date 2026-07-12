# MediFlow Application Architecture

This document describes the architectural layers and data flows of the MediFlow clinical intelligence system.

## System Topology

```mermaid
graph TD
    %% Frontend Layer
    Streamlit[Streamlit UI ui/app.py]
    
    %% API Layer
    FastAPI[FastAPI Server app.py]
    
    %% Workflow Layer
    subgraph LangGraph ["Stateful LangGraph Workflow (clinical_workflow/)"]
        Transcriber[Transcriber Node]
        Cleaner[Cleaner Node]
        Formatter[SOAP Formatter Node]
        Validator[Validator Node]
        Approval[Approval Pause Node]
        Corrector[Corrector Node]
        Saver[Saver Node]
    end
    
    %% AI & Language Services
    Ollama[Ollama Local LLM]
    Chroma[ChromaDB Vector Store]
    LT[LanguageTool Server]
    
    %% Persistence Layer
    DB[database/db.py Manager]
    Postgres[(PostgreSQL DB)]
    SQLite[(SQLite DB)]
    
    %% Connections
    Streamlit -- HTTP REST --> FastAPI
    FastAPI -- Invokes --> LangGraph
    
    %% Graph Node Flows
    Transcriber --> Cleaner --> Formatter --> Validator
    Validator -- "is_valid = True" --> Approval
    Validator -- "is_valid = False (Retry < 3)" --> Formatter
    Validator -- "is_valid = False (Retry >= 3)" --> Approval
    Approval -- "Approved" --> Saver
    Approval -- "Rejected / Corrections" --> Corrector --> Validator
    
    %% Node dependencies
    Formatter -- "RAG context" --> Chroma
    Formatter -- "Extract & Format" --> Ollama
    Validator -- "Spelling & Grammar" --> LT
    Saver -- "Persist Record" --> DB
    
    %% DB routing
    DB -- "Default / Complete Config" --> Postgres
    DB -- "Fallback / No Config" --> SQLite
```

## Architectural Decoupling

1. **Stateful Graph Pipeline**: The LangGraph engine isolates step-by-step documentation generation (transcription cleanup, clinical data extraction, formatting, completion validation, correction, and persistence) from route handlers and the presentation interface. State changes flow sequentially and support recursive loopbacks.
2. **Unified Database Manager**: [database/db.py](file:///d:/Projects/MediFlow/database/db.py) handles connection pools, parameter replacement (`?` -> `%s` for Postgres), and transaction controls. Other services query raw SQL or schema creations without knowing if the storage backend is SQLite or PostgreSQL.
3. **Language quality isolation**: LanguageTool performs spelling/grammar recommendations only. It does not validate medical accuracy, and its connection timeouts/failures degrade gracefully to prevent workflow blockages.
