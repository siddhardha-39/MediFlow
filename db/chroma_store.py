import os
from pathlib import Path
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

def get_chroma_store(patient_id: str) -> Chroma:
    """
    Initializes and returns the ChromaDB vector store for a specific patient.
    Embeddings for each file are stored SEPARATELY in their own folder.
    """
    # Create persistent directory inside db/chroma_data/{patient_id}
    db_dir = Path(__file__).parent / "chroma_data" / patient_id
    
    # Embeddings
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    
    # ChromaDB (per patient)
    vector_store = Chroma(
        collection_name=patient_id,
        embedding_function=embeddings,
        persist_directory=str(db_dir)
    )
    return vector_store

def add_documents_to_db(chunks: list[Document], patient_id: str) -> Chroma:
    """
    Adds document chunks to the specific patient's Chroma DB.
    """
    vector_store = get_chroma_store(patient_id)
    vector_store.add_documents(documents=chunks)
    return vector_store

def get_retriever(patient_id: str, k: int = 5):
    """
    Returns a retriever interface for the specific patient's vector store.
    """
    vector_store = get_chroma_store(patient_id)
    
    # Retriever
    return vector_store.as_retriever(search_kwargs={"k": k})
