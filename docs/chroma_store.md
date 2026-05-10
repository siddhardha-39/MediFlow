# Documentation: `db/chroma_store.py`

## Purpose
This script manages the **Embeddings**, **ChromaDB**, and **Retriever** layers. It is responsible for converting text chunks into mathematical vectors (embeddings) and storing those vectors securely on the disk. It also provides the search interface for the LLM agent to find relevant text chunks.

## Code Explanation

```python
import os
from pathlib import Path
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document

def get_chroma_store(patient_id: str) -> Chroma:
    # 1. Isolate Database Storage Path
    db_dir = Path(__file__).parent / "chroma_data" / patient_id
    
    # 2. Embedding Model Selection
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    
    # 3. Chroma DB Instance Initialization
    vector_store = Chroma(
        collection_name=patient_id,
        embedding_function=embeddings,
        persist_directory=str(db_dir)
    )
    return vector_store

def add_documents_to_db(chunks: list[Document], patient_id: str) -> Chroma:
    vector_store = get_chroma_store(patient_id)
    vector_store.add_documents(documents=chunks)
    return vector_store

def get_retriever(patient_id: str, k: int = 5):
    vector_store = get_chroma_store(patient_id)
    # 4. Generate Retriever Interface
    return vector_store.as_retriever(search_kwargs={"k": k})
```

## How It Works
1. **Isolated Storage**: `get_chroma_store` dynamically generates a path like `db/chroma_data/PT-2024-001`. This strictly separates vector data, ensuring patient records are not mixed in the same database file.
2. **Nomic Embeddings**: We use `nomic-embed-text` via Ollama. It converts chunks of human text into multi-dimensional arrays (vectors) while utilizing minimal system RAM.
3. **Database Initialization**: The `Chroma` client points to our isolated path, utilizing the defined embeddings engine. When data is added, Chroma automatically converts the text via `nomic-embed-text` and saves it to SQLite/parquet files in that folder.
4. **Retriever Layer**: `get_retriever` wraps the database into a LangChain retrieval interface. `k=5` tells the retriever that whenever a question is asked, it should return the top 5 most mathematically relevant text chunks.
