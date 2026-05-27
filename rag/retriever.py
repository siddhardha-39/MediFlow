from __future__ import annotations

import re
from typing import List, Optional, Tuple

from langchain_core.documents import Document

from .metadata import ClinicalMetadataTagger
from .utils import get_logger

logger = get_logger("rag.retriever")


class RAGRetriever:
    """Domain-aware clinical retriever with deduplication and source formatting."""

    def __init__(self, vector_db):
        self.vector_db = vector_db

    def retrieve(self, query: str, domain: Optional[str] = None, k: int = 5) -> List[Tuple[Document, float]]:
        """Retrieve top chunks, optionally constrained to one metadata domain."""
        if domain:
            return self._similarity_search(query, k=k, filter_dict={"primary_domain": domain})

        query_meta = ClinicalMetadataTagger.classify_query_metadata(query)
        domains = [query_meta["primary_domain"]] + query_meta["secondary_domains"]
        tags = query_meta["secondary_tags"]
        return self.retrieve_with_metadata_filter(query, domains, tags, k=k)

    def retrieve_with_metadata_filter(
        self,
        query: str,
        domains: List[str],
        secondary_tags: List[str],
        *,
        k: int = 5,
    ) -> List[Tuple[Document, float]]:
        """Retrieve and lightly rerank by domain, secondary tags, and key query terms."""
        candidate_k = max(k * 3, 10)
        filter_dict = {"primary_domain": {"$in": domains}} if domains else None
        candidates = self._similarity_search(query, k=candidate_k, filter_dict=filter_dict)

        if not candidates and filter_dict:
            candidates = self._similarity_search(query, k=candidate_k, filter_dict=None)

        key_terms = {
            term.lower()
            for term in re.findall(r"\b[A-Za-z0-9&.\-]{3,}\b", query)
            if term.isupper() or any(ch.isdigit() for ch in term) or len(term) > 4
        }

        scored = []
        primary = domains[0] if domains else None
        for doc, distance in candidates:
            doc_domain = doc.metadata.get("primary_domain")
            doc_tags = {
                tag.strip().lower()
                for tag in str(doc.metadata.get("secondary_tags", "")).split(",")
                if tag.strip()
            }
            tag_matches = sum(1 for tag in secondary_tags if tag in doc_tags)
            term_matches = sum(1 for term in key_terms if term in doc.page_content.lower())
            domain_boost = 0.05 if doc_domain == primary else 0.02 if doc_domain in domains else 0.0
            boosted_distance = max(0.0, float(distance) - domain_boost - (0.04 * tag_matches) - (0.02 * term_matches))
            scored.append((doc, boosted_distance))

        return self._dedupe_and_sort(scored, max_total=k)

    def format_context(self, results: List[Tuple[Document, float]]) -> str:
        """Format retrieved documents with source/page references for grounded prompts."""
        if not results:
            return ""

        parts = []
        for index, (doc, distance) in enumerate(results, 1):
            meta = doc.metadata
            source = meta.get("source_file", "unknown")
            page = meta.get("page", "unknown")
            domain = meta.get("primary_domain", "unknown")
            parts.append(
                f"[Reference {index} | Source: {source} | Page: {page} | Domain: {domain} | Distance: {distance:.4f}]\n"
                f"{doc.page_content}"
            )
        return "\n\n---\n\n".join(parts)

    def _similarity_search(self, query: str, *, k: int, filter_dict: Optional[dict]):
        try:
            if filter_dict:
                return self.vector_db.similarity_search_with_score(query, k=k, filter=filter_dict)
            return self.vector_db.similarity_search_with_score(query, k=k)
        except Exception as exc:
            logger.warning("RAG retrieval failed: %s", exc)
            return []

    @staticmethod
    def _dedupe_and_sort(results: List[Tuple[Document, float]], max_total: int) -> List[Tuple[Document, float]]:
        unique = {}
        for doc, distance in results:
            key = (
                doc.metadata.get("source_file"),
                doc.metadata.get("page"),
                doc.page_content[:250],
            )
            if key not in unique or distance < unique[key][1]:
                unique[key] = (doc, distance)

        sorted_results = list(unique.values())
        sorted_results.sort(key=lambda item: item[1])
        return sorted_results[:max_total]
