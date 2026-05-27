from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .metadata import ClinicalMetadataTagger
from .utils import get_chroma_class, get_embedding_model, get_logger, safe_collection_name

logger = get_logger("rag.ingestor")


class RAGIngestor:
    """Load PDFs, chunk them, attach clinical metadata, and persist to Chroma."""

    def __init__(
        self,
        docs_dir: str | Path,
        persist_dir: str | Path,
        *,
        collection_name: str,
        document_type: str = "patient_record",
        patient_id: Optional[str] = None,
        embedding_provider: Optional[str] = None,
        embedding_model_name: Optional[str] = None,
        include_files: Optional[List[str]] = None,
        chunk_size: int = 1200,
        chunk_overlap: int = 150,
    ):
        self.docs_dir = Path(docs_dir).resolve()
        self.persist_dir = Path(persist_dir).resolve()
        self.collection_name = safe_collection_name(collection_name)
        self.document_type = document_type
        self.patient_id = patient_id
        self.embedding_provider = embedding_provider
        self.embedding_model_name = embedding_model_name
        self.include_files = set(include_files or [])
        self.tracker_path = self.persist_dir / "ingested_files.json"
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""],
        )

    @staticmethod
    def get_file_md5(path: str | Path, chunk_size: int = 1024 * 1024) -> str:
        """Return a stable MD5 hash without reading large files all at once."""
        digest = hashlib.md5()
        with Path(path).open("rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(chunk_size), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def get_document_fingerprints(self) -> Dict[str, str]:
        """Fingerprint all PDFs in the configured document directory."""
        if not self.docs_dir.exists():
            return {}

        fingerprints = {}
        for path in sorted(self.docs_dir.glob("*.pdf")):
            if self.include_files and path.name not in self.include_files:
                continue
            fingerprints[path.name] = self.get_file_md5(path)
        return fingerprints

    def load_and_chunk_pdf(self, filename: str) -> List[Document]:
        """Load one PDF and split it into clinically tagged chunks."""
        pdf_path = self.docs_dir / filename
        logger.info("Loading PDF for RAG ingestion: %s", pdf_path)
        try:
            documents = PyPDFLoader(str(pdf_path)).load()
        except Exception as exc:
            logger.error("Failed to load PDF %s: %s", filename, exc)
            return []

        raw_chunks = self.text_splitter.split_documents(documents)
        tagged_chunks = []
        for chunk in raw_chunks:
            page_number = int(chunk.metadata.get("page", 0)) + 1
            metadata = ClinicalMetadataTagger.generate_metadata(
                filename,
                page_number,
                chunk.page_content,
                document_type=self.document_type,
                patient_id=self.patient_id,
            )
            chunk.metadata.update(metadata)
            tagged_chunks.append(chunk)

        return tagged_chunks

    def load_existing(self):
        """Load an existing Chroma store from disk."""
        Chroma = get_chroma_class()
        return Chroma(
            persist_directory=str(self.persist_dir),
            embedding_function=get_embedding_model(self.embedding_provider, self.embedding_model_name),
            collection_name=self.collection_name,
        )

    def run_ingestion(self, force_rebuild: bool = False):
        """Build or load a Chroma store, rebuilding only when PDFs changed."""
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        current_fingerprints = self.get_document_fingerprints()

        if not current_fingerprints:
            raise ValueError(f"No PDFs found in {self.docs_dir}")

        if self.tracker_path.exists() and not force_rebuild:
            try:
                saved_fingerprints = json.loads(self.tracker_path.read_text(encoding="utf-8"))
                if saved_fingerprints == current_fingerprints:
                    logger.info("RAG index is up to date: %s", self.persist_dir)
                    return self.load_existing()
            except Exception:
                logger.info("Could not read ingestion tracker; rebuilding index.")

        if self.persist_dir.exists():
            shutil.rmtree(self.persist_dir, ignore_errors=True)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        all_chunks: List[Document] = []
        for filename in current_fingerprints:
            all_chunks.extend(self.load_and_chunk_pdf(filename))

        if not all_chunks:
            raise ValueError(f"No chunks could be loaded from {self.docs_dir}")

        logger.info("Writing %d chunks to Chroma collection %s", len(all_chunks), self.collection_name)
        Chroma = get_chroma_class()
        vector_db = Chroma.from_documents(
            documents=all_chunks,
            embedding=get_embedding_model(self.embedding_provider, self.embedding_model_name),
            persist_directory=str(self.persist_dir),
            collection_name=self.collection_name,
        )
        self.tracker_path.write_text(json.dumps(current_fingerprints, indent=2), encoding="utf-8")
        return vector_db
