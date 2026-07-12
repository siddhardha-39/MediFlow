from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional until dependencies are installed
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parent

if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env")


def get_setting(name: str, default: str) -> str:
    """Read a string setting from environment with a stable local default."""
    value = os.getenv(name, default)
    return value.strip() or default


# ── LLM Configuration ─────────────────────────────────────────────────────────
# MediFlow v1 uses Google Gemini exclusively.
# The Gemini API key is provided at runtime via the Streamlit UI (not stored here).
MEDIFLOW_LLM_MODEL = get_setting("MEDIFLOW_LLM_MODEL", "gemma-4-31b-it")

# ── API Configuration ─────────────────────────────────────────────────────────
MEDIFLOW_API_URL = get_setting("MEDIFLOW_API_URL", "http://localhost:8000")

# ── RAG / Embedding Configuration ────────────────────────────────────────────
# MediFlow v1 uses local HuggingFace embeddings (no Ollama server required).
RAG_EMBEDDING_PROVIDER = get_setting("RAG_EMBEDDING_PROVIDER", "huggingface").lower()
MEDIFLOW_EMBEDDING_MODEL = get_setting("MEDIFLOW_EMBEDDING_MODEL", "BAAI/bge-small-en")

# ── Database Configuration ────────────────────────────────────────────────────
# MediFlow v1 uses SQLite only. No PostgreSQL configuration needed.
MEDIFLOW_DB_PATH = get_setting("MEDIFLOW_DB_PATH", str(PROJECT_ROOT / "mediflow.db"))

# ── ChromaDB Configuration ────────────────────────────────────────────────────
MEDIFLOW_CHROMA_PATH = get_setting("MEDIFLOW_CHROMA_PATH", str(PROJECT_ROOT / "db" / "chroma_data"))
