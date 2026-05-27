from __future__ import annotations

from langchain_core.documents import Document

from rag.service import ingest_patient_documents
from rag.utils import PATIENT_VECTOR_ROOT, get_chroma_class, get_embedding_model, safe_collection_name


def get_chroma_store(patient_id: str):
    """
    Return the ChromaDB vector store for a specific patient.

    Compatibility wrapper around the upgraded RAG package. New patient indexes
    live in db/chroma_data/patients/{patient_id}.
    """
    db_dir = PATIENT_VECTOR_ROOT / patient_id
    if not db_dir.exists():
        return ingest_patient_documents(patient_id)

    Chroma = get_chroma_class()
    return Chroma(
        collection_name=safe_collection_name(f"patient_{patient_id}"),
        embedding_function=get_embedding_model(),
        persist_directory=str(db_dir),
    )


def add_documents_to_db(chunks: list[Document], patient_id: str):
    """
    Add already-created chunks to the specific patient's vector store.

    This preserves the old interface used by db/ingest_patients.py while
    storing data in the new patient-specific RAG path.
    """
    db_dir = PATIENT_VECTOR_ROOT / patient_id
    db_dir.mkdir(parents=True, exist_ok=True)
    Chroma = get_chroma_class()
    vector_store = Chroma(
        collection_name=safe_collection_name(f"patient_{patient_id}"),
        embedding_function=get_embedding_model(),
        persist_directory=str(db_dir),
    )
    for chunk in chunks:
        chunk.metadata.setdefault("patient_id", patient_id)
        chunk.metadata.setdefault("document_type", "patient_record")
    vector_store.add_documents(documents=chunks)
    return vector_store


def get_retriever(patient_id: str, k: int = 5):
    """
    Return a LangChain retriever interface for the specific patient's store.
    """
    vector_store = get_chroma_store(patient_id)
    return vector_store.as_retriever(search_kwargs={"k": k})
