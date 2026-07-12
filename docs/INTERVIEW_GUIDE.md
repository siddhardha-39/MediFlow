# MediFlow Interview Guide

Technical answers to architectural questions for interviewers and recruiters.

---

### 1. Why LangGraph?
LangGraph provides a stateful, cyclical graph structure. Unlike chain-based agents (which execute linearly), clinical workflows require loopbacks (e.g., validation fail -> correction node -> re-validation). LangGraph tracks this state natively and supports interrupts (human-in-the-loop validation) before critical actions like saving EHR records.

### 2. Why is this a workflow rather than simply calling an LLM?
Clinical documentation requires strict compliance. Direct LLM prompts often omit sections, include wrong placeholders, or ignore spelling errors. A graph structure splits the task into dedicated steps: transcription cleanup, structured formatting, clinical completeness validation, grammar check, and doctor approval.

### 3. What makes the system agentic, if anything?
The system utilizes **routing agents** and **correction loops**. When the validator node detects missing clinical parameters, it routes the state back to the generator with feedback. It is agentic because it autonomously evaluates its own output against completeness criteria and decides whether to continue loops or prompt the user.

### 4. Why local LLMs?
Patient health data is highly sensitive. Transmitting PHI (Protected Health Information) to third-party APIs (like OpenAI) creates security risks. Running lightweight local models (e.g. `llama3.2:1b`) via Ollama preserves privacy by design and operates offline.

### 5. Why PostgreSQL with SQLite fallback?
* **PostgreSQL** is the standard for robust, relational enterprise storage.
* **SQLite fallback** guarantees zero-config developer onboarding. If no environment credentials exist, it falls back to SQLite so the project builds, runs, and passes tests instantly.

### 6. Why raw SQL instead of SQLAlchemy or an ORM?
Writing raw SQL allows precise query profiling and control over database-driver differences (e.g., SQLite's `lastrowid` vs Postgres' `RETURNING id`). In small service projects, this reduces framework overhead.

### 7. Why no Alembic?
Since the schema is small and initialized programmatically via `init_db()`, we rely on simple startup checks. A real deployment would integrate Alembic for migrations, which is listed as a project limitation.

### 8. How does RAG work?
We ingest patient PDFs, tag them with metadata domains (medications, allergies, conditions), and index them in a ChromaDB vector store. During searches, the query is matched against the index using cosine similarity, and top documents are formatted into the LLM context.

### 9. How are hallucination risks handled?
* **Metadata filters**: The RAG retriever restricts queries based on metadata tags.
* **Strict validator**: The validator node asserts completeness and compares generated entities with the source text.
* **Doctor in the loop**: The workflow pauses at the approval node, forcing the physician to review and edit the output.

### 10. What does LanguageTool validate?
LanguageTool performs grammar, style, and spelling checks on draft SOAP sections. It does **not** validate medical correctness, clinical accuracy, or treatment safety.

### 11. What happens when LanguageTool is unavailable?
The HTTP client catches timeouts/connection failures, updates `languagetool_status` to false, and lets the validation node complete successfully. The UI displays a non-blocking warning.

### 12. What happens when PostgreSQL is unavailable?
If Postgres variables are not configured, it selects SQLite. If they are configured but offline, connection fails, prompting the user.

### 13. How are tests isolated from external services?
We use pytest autouse fixtures to mock `check_text` and mock LLM calls. Tests do not require Ollama, PostgreSQL, or LanguageTool servers to be running.

### 14. Why Docker Compose?
It orchestrates all dependencies (Postgres, LanguageTool, backend, frontend) in a single command, ensuring identical environments in local dev, staging, and production.

### 15. What are the biggest limitations?
* No user authentication or HIPAA audit log.
* Simple raw SQL schema setups (no Alembic migrations).
* Local model quality is hardware-bound.

### 16. What would be required before real healthcare deployment?
* HIPAA-compliant cloud storage with full Audit Logging.
* User Authentication and Role-Based Access Control (RBAC).
* HL7 / FHIR integration to connect with existing hospital EHR systems.
* Database migrations framework (Alembic).

### 17. What would you improve with two additional weeks?
* Integrate FHIR endpoints to ingest real hospital patient records.
* Add Alembic migration layers.
* Integrate LangSmith tracing for LLM execution logs.
