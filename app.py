# app.py
"""
FastAPI application entry point.

Mounts all module routers and initializes the database.

HOW TO RUN:
    python app.py
    Then open http://localhost:8000/docs for interactive API docs.
"""
import logging
from fastapi import FastAPI
from database.db import init_db

# Import routers
from transcription.router import router as transcription_router
from soap_notes.router import router as soap_router

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)-8s  %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)

# ── FastAPI App ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MediFlow API",
    description="AI-powered clinical documentation system",
    version="0.3.0",
)

# Mount routers
app.include_router(transcription_router)
app.include_router(soap_router)

# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.3.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
