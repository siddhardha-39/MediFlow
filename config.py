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


MEDIFLOW_LLM_MODEL = get_setting("MEDIFLOW_LLM_MODEL", "llama3.2:1b")
MEDIFLOW_EMBEDDING_MODEL = get_setting("MEDIFLOW_EMBEDDING_MODEL", "nomic-embed-text")
MEDIFLOW_API_URL = get_setting("MEDIFLOW_API_URL", "http://localhost:8000")
RAG_EMBEDDING_PROVIDER = get_setting("RAG_EMBEDDING_PROVIDER", "ollama").lower()
