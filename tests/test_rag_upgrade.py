import os
import sys
import tempfile
import unittest
import pytest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.documents import Document

from rag.ingestor import RAGIngestor
from rag.metadata import ClinicalMetadataTagger
from rag.retriever import RAGRetriever


class FakeVectorDB:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def similarity_search_with_score(self, query, k=4, filter=None):
        self.calls.append({"query": query, "k": k, "filter": filter})
        return self.results[:k]


@pytest.mark.unit
class TestRAGUpgrade(unittest.TestCase):
    def test_clinical_metadata_classification(self):
        medication = ClinicalMetadataTagger.generate_metadata(
            "patient.pdf",
            1,
            "Patient takes metformin 500mg twice daily and aspirin 75mg.",
        )
        self.assertEqual(medication["primary_domain"], "medications")
        self.assertIn("drug", medication["secondary_tags"])
        self.assertIn("dosage", medication["secondary_tags"])

        allergy = ClinicalMetadataTagger.generate_metadata(
            "patient.pdf",
            2,
            "Known allergy to penicillin with rash.",
        )
        self.assertEqual(allergy["primary_domain"], "allergies")
        self.assertIn("allergy-marker", allergy["secondary_tags"])

        guideline = ClinicalMetadataTagger.generate_metadata(
            "guideline.pdf",
            1,
            "Clinical practice guideline recommendation for follow-up.",
            document_type="clinical_guideline",
        )
        self.assertEqual(guideline["primary_domain"], "clinical_guidelines")

    def test_file_fingerprints_track_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs_dir = Path(tmp) / "docs"
            persist_dir = Path(tmp) / "chroma"
            docs_dir.mkdir()
            pdf_path = docs_dir / "PT-1.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 initial")

            ingestor = RAGIngestor(
                docs_dir=docs_dir,
                persist_dir=persist_dir,
                collection_name="patient_PT_1",
                patient_id="PT-1",
            )
            first = ingestor.get_document_fingerprints()
            pdf_path.write_bytes(b"%PDF-1.4 changed")
            second = ingestor.get_document_fingerprints()

            self.assertIn("PT-1.pdf", first)
            self.assertIn("PT-1.pdf", second)
            self.assertNotEqual(first["PT-1.pdf"], second["PT-1.pdf"])

    def test_retriever_deduplicates_and_preserves_source_metadata(self):
        doc_a = Document(
            page_content="Penicillin allergy and chest pain noted.",
            metadata={"source_file": "patient.pdf", "page": 1, "primary_domain": "allergies", "secondary_tags": "allergy-marker,red-flag"},
        )
        doc_b = Document(
            page_content="Penicillin allergy and chest pain noted.",
            metadata={"source_file": "patient.pdf", "page": 1, "primary_domain": "allergies", "secondary_tags": "allergy-marker,red-flag"},
        )
        doc_c = Document(
            page_content="Metformin 500mg twice daily.",
            metadata={"source_file": "patient.pdf", "page": 2, "primary_domain": "medications", "secondary_tags": "drug,dosage"},
        )
        retriever = RAGRetriever(FakeVectorDB([(doc_a, 0.4), (doc_b, 0.2), (doc_c, 0.3)]))

        results = retriever.retrieve("patient allergy and medications", k=3)
        context = retriever.format_context(results)

        self.assertEqual(len(results), 2)
        self.assertIn("Source: patient.pdf", context)
        self.assertIn("Page: 1", context)
        self.assertIn("Page: 2", context)


if __name__ == "__main__":
    unittest.main()
