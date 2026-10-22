from dataclasses import dataclass
from typing import List, Dict, Any
from seekvault.privacy.detector import PrivacyDetector, DetectedEntity
from seekvault.privacy.redactor import PrivacyRedactor
from seekvault.core.logger import logger

# Entity Weights for Sensitivity Scoring
ENTITY_WEIGHTS = {
    "SECRET_KEY": 5.0,
    "FINANCIAL_INFO": 4.0,
    "CREDIT_CARD": 4.0,
    "ID_NUMBER": 4.0,
    "US_SSN": 4.0,
    "EMAIL_ADDRESS": 1.0,
    "PHONE_NUMBER": 1.0,
    "PERSON": 0.5,
    "LOCATION": 0.5
}

# Critical entity types that automatically force METADATA_ONLY tier
CRITICAL_ENTITIES = {"SECRET_KEY", "FINANCIAL_INFO", "CREDIT_CARD", "ID_NUMBER", "US_SSN"}

@dataclass
class PrivacyClassification:
    tier: str                           # "FULL", "REDACTED", "METADATA_ONLY"
    sensitivity_score: float            # Numeric sensitivity score
    detected_entities: List[DetectedEntity]
    redacted_text: str                  # Redacted text (empty if METADATA_ONLY)
    reason: str                         # Reason for tier decision

class PrivacyClassifier:
    """
    Evaluates extracted text, computes sensitivity score, assigns privacy classification tier
    (FULL, REDACTED, METADATA_ONLY), and applies in-memory redaction.
    """

    def __init__(self, metadata_score_threshold: float = 4.0):
        self.detector = PrivacyDetector()
        self.redactor = PrivacyRedactor()
        self.metadata_score_threshold = metadata_score_threshold

    def calculate_sensitivity_score(self, entities: List[DetectedEntity]) -> float:
        total_score = 0.0
        for ent in entities:
            weight = ENTITY_WEIGHTS.get(ent.entity_type, 1.0)
            total_score += weight * ent.score
        return round(total_score, 2)

    def classify(self, text: str) -> PrivacyClassification:
        if not text or not text.strip():
            return PrivacyClassification(
                tier="FULL",
                sensitivity_score=0.0,
                detected_entities=[],
                redacted_text="",
                reason="Text content is empty."
            )

        # 1. Detect entities
        entities = self.detector.detect(text)
        sensitivity_score = self.calculate_sensitivity_score(entities)

        if not entities or sensitivity_score == 0.0:
            return PrivacyClassification(
                tier="FULL",
                sensitivity_score=0.0,
                detected_entities=[],
                redacted_text=text,
                reason="No significant sensitive entities detected."
            )

        # 2. Check for Critical Entities (triggers METADATA_ONLY)
        detected_types = {e.entity_type for e in entities}
        critical_matches = detected_types.intersection(CRITICAL_ENTITIES)

        if critical_matches or sensitivity_score >= self.metadata_score_threshold:
            matched_list = ", ".join(critical_matches) if critical_matches else "High sensitivity score"
            return PrivacyClassification(
                tier="METADATA_ONLY",
                sensitivity_score=sensitivity_score,
                detected_entities=entities,
                redacted_text="",  # Content stripped from search index for safety
                reason=f"File contains highly sensitive critical entities ({matched_list}). Content excluded from vector index."
            )

        # 3. Otherwise, apply REDACTED tier (moderate sensitivity)
        redacted_text = self.redactor.redact(text, entities)
        entity_counts = ", ".join(f"{t}: {sum(1 for e in entities if e.entity_type == t)}" for t in detected_types)
        
        return PrivacyClassification(
            tier="REDACTED",
            sensitivity_score=sensitivity_score,
            detected_entities=entities,
            redacted_text=redacted_text,
            reason=f"Moderate sensitive entities detected ({entity_counts}). Anonymized tokens applied in-memory."
        )
