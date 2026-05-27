from __future__ import annotations

import re
from typing import Any, Dict, List

from .utils import get_logger

logger = get_logger("rag.metadata")


class ClinicalMetadataTagger:
    """Keyword-first healthcare metadata tagging for RAG chunks and queries."""

    PRIMARY_DOMAINS = [
        "patient_demographics",
        "diagnosis_history",
        "medications",
        "allergies",
        "lab_results",
        "imaging",
        "procedures",
        "visit_notes",
        "care_plan",
        "clinical_guidelines",
    ]

    DOMAIN_KEYWORDS = {
        "patient_demographics": [
            "name", "age", "gender", "dob", "date of birth", "mrn", "blood group",
            "address", "patient id",
        ],
        "diagnosis_history": [
            "diagnosis", "diagnosed", "history", "chronic", "condition", "diabetes",
            "hypertension", "asthma", "copd", "pneumonia", "angina", "infection",
        ],
        "medications": [
            "medication", "medicine", "drug", "dose", "dosage", "tablet", "capsule",
            "mg", "ml", "amlodipine", "metformin", "aspirin", "tylenol", "insulin",
        ],
        "allergies": [
            "allergy", "allergic", "allergies", "anaphylaxis", "rash", "penicillin",
            "sulfa", "latex", "contrast",
        ],
        "lab_results": [
            "lab", "laboratory", "test", "result", "blood pressure", "bp", "glucose",
            "hba1c", "hemoglobin", "creatinine", "cholesterol", "abnormal",
        ],
        "imaging": [
            "x-ray", "xray", "ct", "mri", "ultrasound", "scan", "ecg", "ekg",
            "radiology", "imaging",
        ],
        "procedures": [
            "procedure", "surgery", "operation", "biopsy", "catheter", "stent",
            "injection", "vaccination",
        ],
        "visit_notes": [
            "visit", "consultation", "follow up", "follow-up", "chief complaint",
            "symptom", "subjective", "objective", "assessment", "plan",
        ],
        "care_plan": [
            "plan", "advice", "follow", "refer", "referral", "monitor", "prescribe",
            "start", "continue", "stop", "review",
        ],
        "clinical_guidelines": [
            "guideline", "protocol", "recommendation", "contraindication", "indication",
            "screening", "criteria", "standard of care", "clinical practice",
        ],
    }

    SECONDARY_TAG_KEYWORDS = {
        "condition": ["diagnosis", "condition", "disease", "diabetes", "hypertension", "asthma", "pneumonia"],
        "drug": ["medication", "drug", "tablet", "metformin", "amlodipine", "aspirin", "tylenol"],
        "allergy-marker": ["allergy", "allergic", "anaphylaxis", "penicillin", "latex"],
        "abnormal-result": ["abnormal", "elevated", "low", "high", "positive", "critical"],
        "follow-up": ["follow up", "follow-up", "review", "return", "recheck"],
        "red-flag": ["chest pain", "shortness of breath", "syncope", "severe", "emergency"],
        "contraindication": ["contraindication", "avoid", "do not use", "not recommended"],
        "dosage": ["mg", "ml", "dose", "dosage", "daily", "bid", "tid", "frequency"],
        "test-result": ["test", "result", "lab", "x-ray", "ecg", "blood pressure", "hba1c"],
        "guideline-source": ["guideline", "protocol", "recommendation", "standard of care"],
    }

    @classmethod
    def determine_domain_keyword_fallback(
        cls,
        filename: str,
        text: str,
        *,
        document_type: str = "patient_record",
    ) -> str:
        """Classify text into one primary healthcare domain using keyword scoring."""
        if document_type == "clinical_guideline":
            return "clinical_guidelines"

        haystack = f"{filename}\n{text}".lower()
        scores = {}
        for domain, keywords in cls.DOMAIN_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                score += len(re.findall(r"\b" + re.escape(keyword.lower()) + r"\b", haystack))
            if score:
                scores[domain] = score

        if not scores:
            return "visit_notes"

        return max(scores.items(), key=lambda item: item[1])[0]

    @classmethod
    def determine_query_domains(cls, query: str, max_domains: int = 3) -> List[str]:
        """Classify a query into one or more likely retrieval domains."""
        text = query.lower()
        scores = {}
        for domain, keywords in cls.DOMAIN_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                score += len(re.findall(r"\b" + re.escape(keyword.lower()) + r"\b", text))
            if score:
                scores[domain] = score

        if not scores:
            return ["visit_notes"]

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return [domain for domain, _ in ranked[:max_domains]]

    @classmethod
    def extract_secondary_tags_keyword_fallback(cls, text: str) -> List[str]:
        """Extract broad healthcare secondary tags with deterministic keyword rules."""
        lower = text.lower()
        tags = []
        for tag, keywords in cls.SECONDARY_TAG_KEYWORDS.items():
            if any(re.search(r"\b" + re.escape(keyword.lower()) + r"\b", lower) for keyword in keywords):
                tags.append(tag)
        return tags

    @classmethod
    def classify_query_metadata(cls, query: str) -> Dict[str, Any]:
        """Return query metadata used by the retriever."""
        domains = cls.determine_query_domains(query, max_domains=3)
        return {
            "primary_domain": domains[0],
            "secondary_domains": domains[1:],
            "secondary_tags": cls.extract_secondary_tags_keyword_fallback(query),
            "confidence_score": 1.0 if domains != ["visit_notes"] else 0.6,
        }

    @classmethod
    def generate_metadata(
        cls,
        filename: str,
        page_number: int,
        chunk_text: str,
        *,
        document_type: str = "patient_record",
        patient_id: str | None = None,
        use_llm: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate Chroma-compatible metadata.

        `use_llm` is accepted for future expansion; ingestion stays keyword-first.
        """
        if use_llm:
            logger.info("LLM metadata tagging is not enabled yet; using keyword fallback.")

        primary_domain = cls.determine_domain_keyword_fallback(
            filename,
            chunk_text,
            document_type=document_type,
        )
        secondary_tags = cls.extract_secondary_tags_keyword_fallback(chunk_text)

        metadata = {
            "primary_domain": primary_domain,
            "secondary_tags": ",".join(secondary_tags),
            "source_file": filename,
            "page": int(page_number),
            "document_type": document_type,
        }
        if patient_id:
            metadata["patient_id"] = patient_id
        return metadata
