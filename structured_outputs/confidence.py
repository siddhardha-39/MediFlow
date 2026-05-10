# confidence.py
"""
Confidence scoring layer.

Responsibilities:
- Estimate how confident we are in each extracted entity
- Produce a ScoredPatientInfo with per-entity scores and an overall score

Scoring heuristics (lightweight, no secondary model needed):
- Entity length:       very short strings (<3 chars) score lower
- Field coverage:      more populated fields → higher overall confidence
- Abbreviation risk:   if abbreviations were not expanded they score lower
- Empty field penalty: empty lists reduce overall confidence
"""
from typing import List

from structured_outputs.models import PatientInfo, ScoredEntity, ScoredPatientInfo
from structured_outputs.utils import get_logger

logger = get_logger("confidence")

# Abbreviations that indicate the LLM may not have normalised the text
_RAW_ABBREVIATIONS = {"dm", "hx", "rx", "nkda", "bp", "sob", "cp", "htn"}


# ── Scoring helpers ────────────────────────────────────────────────────────────

def _score_entity(value: str) -> float:
    """
    Score a single entity string.

    Rules:
    - Base score: 1.0
    - Very short (<= 2 chars):  -0.4  (likely garbage or unexpanded abbrev)
    - Known raw abbreviation:   -0.3
    - Medium short (3-5 chars): -0.1  (might be fine, slight doubt)
    """
    score = 1.0
    v = value.strip().lower()

    if len(v) <= 2:
        score -= 0.4
    elif v in _RAW_ABBREVIATIONS:
        score -= 0.3
    elif len(v) <= 5:
        score -= 0.1

    return round(max(0.0, min(1.0, score)), 3)


def _score_list(items: List[str]) -> List[ScoredEntity]:
    return [ScoredEntity(value=item, confidence=_score_entity(item)) for item in items]


def _overall_confidence(info: PatientInfo) -> float:
    """
    Compute overall confidence as a weighted average of:
    - Average entity score across all fields
    - Field coverage ratio (how many of the 4 fields are non-empty)
    """
    all_entities = (
        info.conditions + info.allergies + info.medications + info.symptoms
    )
    if not all_entities:
        return 0.0

    avg_entity_score = sum(_score_entity(e) for e in all_entities) / len(all_entities)

    non_empty_fields = sum([
        bool(info.conditions),
        bool(info.allergies),
        bool(info.medications),
        bool(info.symptoms),
    ])
    coverage_ratio = non_empty_fields / 4.0

    # Weighted blend: entity quality 70%, field coverage 30%
    overall = 0.7 * avg_entity_score + 0.3 * coverage_ratio
    return round(overall, 3)


# ── Public API ─────────────────────────────────────────────────────────────────

def score(info: PatientInfo, notes: str = "") -> ScoredPatientInfo:
    """
    Attach confidence scores to every extracted entity.

    Args:
        info:  A validated PatientInfo instance.
        notes: Optional string describing any pipeline anomalies.

    Returns:
        ScoredPatientInfo with per-entity and overall confidence scores.
    """
    overall = _overall_confidence(info)

    scored = ScoredPatientInfo(
        conditions=_score_list(info.conditions),
        allergies=_score_list(info.allergies),
        medications=_score_list(info.medications),
        symptoms=_score_list(info.symptoms),
        overall_confidence=overall,
        extraction_notes=notes or None,
    )

    logger.info(
        "Confidence scored — overall=%.3f  entities=%d",
        overall,
        sum(len(getattr(info, f)) for f in ["conditions", "allergies", "medications", "symptoms"]),
    )
    return scored
