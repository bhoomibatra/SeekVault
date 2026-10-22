from typing import List, Dict
from seekvault.privacy.detector import DetectedEntity
from seekvault.core.logger import logger

try:
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import RecognizerResult, OperatorConfig
    HAS_PRESIDIO_ANONYMIZER = True
except ImportError:
    HAS_PRESIDIO_ANONYMIZER = False

# Standard Placeholder Tokens
TOKEN_MAP = {
    "EMAIL_ADDRESS": "<EMAIL>",
    "PHONE_NUMBER": "<PHONE_NUMBER>",
    "PERSON": "<PERSON>",
    "FINANCIAL_INFO": "<FINANCIAL_INFO>",
    "CREDIT_CARD": "<FINANCIAL_INFO>",
    "ID_NUMBER": "<ID_NUMBER>",
    "US_SSN": "<ID_NUMBER>",
    "SECRET_KEY": "<SECRET_KEY>"
}

class PrivacyRedactor:
    """
    Performs in-memory anonymization by replacing detected sensitive entity spans with
    standardized token placeholders (<EMAIL>, <PHONE_NUMBER>, <PERSON>, etc.).
    Does NOT modify original user files on disk.
    """

    def __init__(self):
        self.anonymizer = AnonymizerEngine() if HAS_PRESIDIO_ANONYMIZER else None

    @staticmethod
    def get_token_for_entity(entity_type: str) -> str:
        return TOKEN_MAP.get(entity_type, f"<{entity_type}>")

    def redact(self, text: str, entities: List[DetectedEntity]) -> str:
        """
        Redacts sensitive spans in `text` in-memory.
        Replaces spans from right-to-left to maintain valid character offsets.
        """
        if not text or not entities:
            return text

        # Sort entities descending by start index to avoid offset shifting issues
        sorted_entities = sorted(entities, key=lambda e: e.start, reverse=True)
        
        redacted_text = text
        for ent in sorted_entities:
            placeholder = self.get_token_for_entity(ent.entity_type)
            start = ent.start
            end = ent.end
            
            # Bounds safety check
            if start >= 0 and end <= len(redacted_text) and start < end:
                redacted_text = redacted_text[:start] + placeholder + redacted_text[end:]
                
        return redacted_text
