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

# ── PostgreSQL Configuration ──────────────────────────────────────────────────
MEDIFLOW_POSTGRES_HOST = get_setting("MEDIFLOW_POSTGRES_HOST", "")
MEDIFLOW_POSTGRES_DB = get_setting("MEDIFLOW_POSTGRES_DB", "")
MEDIFLOW_POSTGRES_USER = get_setting("MEDIFLOW_POSTGRES_USER", "")
MEDIFLOW_POSTGRES_PASSWORD = os.getenv("MEDIFLOW_POSTGRES_PASSWORD", "").strip()
MEDIFLOW_POSTGRES_PORT = get_setting("MEDIFLOW_POSTGRES_PORT", "5432")

# Validate configuration presence to handle complete, partial, and no config states
required_pg = {
    "MEDIFLOW_POSTGRES_HOST": MEDIFLOW_POSTGRES_HOST.strip(),
    "MEDIFLOW_POSTGRES_DB": MEDIFLOW_POSTGRES_DB.strip(),
    "MEDIFLOW_POSTGRES_USER": MEDIFLOW_POSTGRES_USER.strip(),
    "MEDIFLOW_POSTGRES_PASSWORD": MEDIFLOW_POSTGRES_PASSWORD.strip(),
}

all_pg_set = all(bool(val) for val in required_pg.values())
any_pg_set = any(bool(val) for val in required_pg.values())

if any_pg_set and not all_pg_set:
    missing = [key for key, val in required_pg.items() if not val]
    raise ValueError(
        f"Incomplete PostgreSQL configuration. Missing required variables: {', '.join(missing)}"
    )

IS_POSTGRES = all_pg_set



