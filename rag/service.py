from __future__ import annotations

from pathlib import Path
from typing import Optional

from config import MEDIFLOW_LLM_MODEL
from .ingestor import RAGIngestor
from .query_engine import RAGQueryEngine
from .retriever import RAGRetriever
from .utils import (
    DEFAULT_GUIDELINE_DOCS_DIR,
    DEFAULT_PATIENT_DOCS_DIR,
    GUIDELINE_VECTOR_ROOT,
    PATIENT_VECTOR_ROOT,
    get_chroma_class,
    get_embedding_model,
    get_logger,
    safe_collection_name,
)

logger = get_logger("rag.service")


def ingest_patient_documents(
    patient_id: str,
    docs_dir: str | Path | None = None,
    force_rebuild: bool = False,
):
    """Ingest PDFs for one patient into an isolated patient vector store."""
    source_dir = Path(docs_dir or DEFAULT_PATIENT_DOCS_DIR)
    persist_dir = PATIENT_VECTOR_ROOT / patient_id
    patient_pdf = f"{patient_id}.pdf"
    include_files = [patient_pdf] if (source_dir / patient_pdf).exists() or docs_dir is None else None
    ingestor = RAGIngestor(
        docs_dir=source_dir,
        persist_dir=persist_dir,
        collection_name=f"patient_{patient_id}",
        document_type="patient_record",
        patient_id=patient_id,
        include_files=include_files,
    )
    return ingestor.run_ingestion(force_rebuild=force_rebuild)


def ingest_guideline_documents(
    docs_dir: str | Path | None = None,
    force_rebuild: bool = False,
):
    """Ingest medical guideline PDFs into the shared guideline vector store."""
    source_dir = Path(docs_dir or DEFAULT_GUIDELINE_DOCS_DIR)
    if not source_dir.exists() or not list(source_dir.glob("*.pdf")):
        logger.info("No guideline PDFs found at %s; guideline RAG will be skipped.", source_dir)
        return None

    ingestor = RAGIngestor(
        docs_dir=source_dir,
        persist_dir=GUIDELINE_VECTOR_ROOT,
        collection_name="clinical_guidelines",
        document_type="clinical_guideline",
    )
    return ingestor.run_ingestion(force_rebuild=force_rebuild)


def _load_patient_store(patient_id: str):
    persist_dir = PATIENT_VECTOR_ROOT / patient_id
    tracker_path = persist_dir / "ingested_files.json"
    if not persist_dir.exists() or not tracker_path.exists():
        return ingest_patient_documents(patient_id)

    Chroma = get_chroma_class()
    return Chroma(
        persist_directory=str(persist_dir),
        embedding_function=get_embedding_model(),
        collection_name=safe_collection_name(f"patient_{patient_id}"),
    )


def _load_guideline_store():
    tracker_path = GUIDELINE_VECTOR_ROOT / "ingested_files.json"
    if not GUIDELINE_VECTOR_ROOT.exists() or not tracker_path.exists():
        return ingest_guideline_documents()

    Chroma = get_chroma_class()
    return Chroma(
        persist_directory=str(GUIDELINE_VECTOR_ROOT),
        embedding_function=get_embedding_model(),
        collection_name="clinical_guidelines",
    )


def retrieve_patient_context(patient_id: str, query: str, k: int = 5) -> str:
    """Return formatted retrieved context for a patient."""
    vector_db = _load_patient_store(patient_id)
    retriever = RAGRetriever(vector_db)
    return retriever.format_context(retriever.retrieve(query, k=k))


def retrieve_guideline_context(query: str, k: int = 4) -> str:
    """Return formatted guideline context, or an empty string when no guidelines exist."""
    vector_db = _load_guideline_store()
    if vector_db is None:
        return ""

    retriever = RAGRetriever(vector_db)
    return retriever.format_context(retriever.retrieve(query, domain="clinical_guidelines", k=k))


def generate_grounded_patient_briefing(
    patient_id: str,
    *,
    model_name: str = MEDIFLOW_LLM_MODEL,
    patient_query: Optional[str] = None,
) -> str:
    """Generate a grounded doctor briefing using patient RAG plus optional guideline RAG."""
    query = patient_query or (
        "patient demographics, age, blood group, diagnosis history, allergies, medications, "
        "recent tests, recent visits, red flags, and care plan"
    )
    logger.info("Generating grounded patient briefing for %s", patient_id)
    patient_context = retrieve_patient_context(patient_id, query, k=6)
    guideline_context = retrieve_guideline_context(
        "clinical safety alerts allergies medications contraindications follow-up",
        k=3,
    )
    return RAGQueryEngine(model_name=model_name).generate_patient_briefing(
        patient_context=patient_context,
        guideline_context=guideline_context,
    )
