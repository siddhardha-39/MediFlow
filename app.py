# app.py
"""
FastAPI application entry point.

WHY THIS FILE EXISTS:
    This is the single entry point for the entire MediFlow API.
    As we add more modules (SOAP notes, database, memory), each
    module will have its own router.py, and we'll mount them all here.

    Current routers:
    - /api/transcribe  (Module 1 - transcription)

    Future routers (not built yet):
    - /api/soap        (Module 2 - SOAP notes)
    - /api/patients    (Module 5 - database)

HOW TO RUN:
    python app.py

    Then open http://localhost:8000/docs for the interactive API docs.
    FastAPI auto-generates Swagger UI from your endpoint definitions.
"""
import logging
from fastapi import FastAPI
from transcription.router import router as transcription_router

# ── Logging Setup ──────────────────────────────────────────────────────────────
# Configure logging ONCE at the app level.
# All modules use logging.getLogger(name) and inherit this config.
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s  %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MediFlow API",
    description="AI-powered clinical documentation system",
    version="0.3.0",  # Stage 3
)

# Mount the transcription router
# All transcription endpoints will be under /api/transcribe
app.include_router(transcription_router)


# ── Health Check ───────────────────────────────────────────────────────────────
@app.get("/health")
def health_check():
    """Simple health check endpoint to verify the server is running."""
    return {"status": "healthy", "version": "0.3.0"}


# ── Run Server ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    # host="0.0.0.0" makes it accessible from other machines on the network
    # reload=True auto-restarts on code changes (dev mode only)
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
