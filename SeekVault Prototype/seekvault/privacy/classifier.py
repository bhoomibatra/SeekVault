from typing import List, Dict, Any
from seekvault.config import TIER_FULL, TIER_REDACTED, TIER_METADATA_ONLY, METADATA_ONLY_KEYWORDS

class PrivacyClassifier:
    @staticmethod
    def classify(
        file_name: str,
        text_content: str,
        detected_entities: List[Dict[str, Any]]
    ) -> str:
        """
        Classifies the file into FULL, REDACTED, or METADATA_ONLY.
        
        Rules:
        - METADATA_ONLY:
            If filename or content indicates high-risk confidential keys,
            passwords, or explicit credential dumps.
        - REDACTED:
            If any personal entities (Email, Phone, Aadhaar, PAN, Person, Credit Card) are detected.
        - FULL:
            If clean with no sensitive entities detected.
        """
        lower_name = file_name.lower()
        lower_text = text_content.lower()

        # Check for extreme confidential keywords
        for kw in METADATA_ONLY_KEYWORDS:
            if kw in lower_name:
                return TIER_METADATA_ONLY

        # Check if CONFIDENTIAL_KEY entity detected
        for ent in detected_entities:
            if ent.get("entity_type") in {"CONFIDENTIAL_KEY", "CRYPTO"}:
                return TIER_METADATA_ONLY

        # If entities detected, file must be REDACTED
        if detected_entities:
            return TIER_REDACTED

        return TIER_FULL
