from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from config import RAG_EMBEDDING_PROVIDER

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - python-dotenv is optional at import time
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHROMA_ROOT = PROJECT_ROOT / "db" / "chroma_data"
PATIENT_VECTOR_ROOT = CHROMA_ROOT / "patients"
GUIDELINE_VECTOR_ROOT = CHROMA_ROOT / "guidelines"
DEFAULT_PATIENT_DOCS_DIR = PROJECT_ROOT / "data" / "sample_patients"
DEFAULT_GUIDELINE_DOCS_DIR = PROJECT_ROOT / "data" / "guidelines"


def setup_unicode() -> None:
    """Make Windows console logging less likely to choke on UTF-8 text."""
    for stream in (sys.stdout, sys.stderr):
        if getattr(stream, "encoding", None) != "utf-8":
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def get_logger(name: str) -> logging.Logger:
    """Create a consistent logger for RAG operations."""
    setup_unicode()
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def _load_env() -> None:
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env")


def get_embedding_model(provider: Optional[str] = None, model_name: Optional[str] = None):
    """
    Build a HuggingFace embedding model (runs in-process, no external server required).

    Default model: BAAI/bge-small-en
    Override via environment variable: RAG_HUGGINGFACE_EMBEDDING_MODEL
    """
    _load_env()
    selected = (provider or RAG_EMBEDDING_PROVIDER).strip().lower()

    if selected not in {"huggingface"}:
        raise ValueError(
            f"RAG_EMBEDDING_PROVIDER must be 'huggingface', got '{selected}'. "
            "Ollama embeddings have been removed in v1.0."
        )

    from langchain_huggingface import HuggingFaceEmbeddings

    model = model_name or os.getenv("RAG_HUGGINGFACE_EMBEDDING_MODEL", "BAAI/bge-small-en")
    return HuggingFaceEmbeddings(model_name=model)


def get_chroma_class():
    """Return the Chroma vector store class, preferring the dedicated package."""
    try:
        from langchain_chroma import Chroma
    except ImportError:
        from langchain_community.vectorstores import Chroma
    return Chroma


def safe_collection_name(name: str) -> str:
    """Normalize collection names for Chroma."""
    cleaned = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in name)
    cleaned = cleaned.strip("_-")
    return cleaned or "mediflow_collection"
