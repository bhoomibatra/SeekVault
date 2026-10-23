import re
from typing import List, Dict, Any
from seekvault.config import TIER_FULL, TIER_REDACTED, TIER_METADATA_ONLY, METADATA_ONLY_KEYWORDS

# Explicit credential and secret patterns in content that trigger METADATA_ONLY
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\b(?:seed[_\s-]?phrase|recovery[_\s-]?seed|master[_\s-]?key)\b\s*[:=]", re.IGNORECASE),
    re.compile(r"\b(?:api[_\s-]?secret|bearer[_\s-]?token|private[_\s-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9_\-\$\#\@]{8,}", re.IGNORECASE),
]

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
            If filename contains high-risk credential keywords (e.g. password_vault, secret_key),
            OR text contains private key headers / explicit credential dumps,
            OR CONFIDENTIAL_KEY / CRYPTO entity is detected.
        - REDACTED:
            If any personal identifying entities (Email, Phone, Aadhaar, PAN, Person, Credit Card) are detected.
        - FULL:
            If clean with no sensitive entities detected.
        """
        lower_name = file_name.lower()

        # 1. Check filename for high-risk confidential keywords
        for kw in METADATA_ONLY_KEYWORDS:
            if kw in lower_name:
                return TIER_METADATA_ONLY

        # 2. Check if CONFIDENTIAL_KEY or CRYPTO entity is detected
        for ent in detected_entities:
            if ent.get("entity_type") in {"CONFIDENTIAL_KEY", "CRYPTO"}:
                return TIER_METADATA_ONLY

        # 3. Check content for explicit private keys or master credentials
        if text_content:
            for pat in SECRET_PATTERNS:
                if pat.search(text_content):
                    return TIER_METADATA_ONLY

        # 4. If any sensitive entities detected, file must be REDACTED
        if detected_entities:
            return TIER_REDACTED

        return TIER_FULL
