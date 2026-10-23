import re
import hashlib
from typing import List, Dict, Any, Optional

# Custom regex definitions tailored for Indian & international context
PATTERNS = {
    "AADHAAR_NUMBER": re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"),
    "PAN_NUMBER": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b"),
    "PHONE_NUMBER": re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|\b(?:\+91[\-\s]?)?[6-9]\d{9}\b"),
    "EMAIL_ADDRESS": re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "CONFIDENTIAL_KEY": re.compile(r"(?:api[_-]?key|secret[_-]?key|password|passphrase|auth[_-]?token)\s*[:=]\s*['\"]?([A-Za-z0-9_\-\$\#\@]{6,})['\"]?", re.IGNORECASE)
}

RULE_CATEGORY_MAP = {
    "AADHAAR_NUMBER": "id",
    "PAN_NUMBER": "id",
    "PHONE_NUMBER": "phone",
    "EMAIL_ADDRESS": "email",
    "CREDIT_CARD": "financial",
    "CONFIDENTIAL_KEY": "creds",
}

def scan_custom_patterns(text: str, enabled_rules: Optional[Dict[str, bool]] = None) -> List[Dict[str, Any]]:
    """Scan text against custom regex patterns and return standardized entity matches with masked tokens."""
    entities = []
    for entity_type, pattern in PATTERNS.items():
        cat = RULE_CATEGORY_MAP.get(entity_type)
        if enabled_rules and cat and not enabled_rules.get(cat, True) and cat != "creds":
            continue
        for match in pattern.finditer(text):
            raw = match.group(0)
            h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:6]
            entities.append({
                "entity_type": entity_type,
                "entity_text": raw,
                "entity_token": f"<{entity_type}_REDACTED_{h}>",
                "start_char": match.start(),
                "end_char": match.end(),
                "confidence": 0.95
            })
    return entities
