import re
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from seekvault.core.logger import logger

@dataclass
class DetectedEntity:
    entity_type: str        # EMAIL_ADDRESS, PHONE_NUMBER, PERSON, ID_NUMBER, FINANCIAL_INFO, SECRET_KEY
    start: int
    end: int
    score: float
    text_span: str

# Custom Regex Patterns for local-first, zero-download entity detection
CUSTOM_REGEX_PATTERNS = {
    "FINANCIAL_INFO": [
        # Credit Card Numbers (Visa, Mastercard, Amex, Discover, Diners, JCB, UnionPay)
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12})\b",
        # CVV / Card Security Code
        r"(?i)\b(?:cvv|cvc|cvv2|security code)[\s:]*([0-9]{3,4})\b",
        # IBAN / Bank Account Number
        r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"
    ],
    "ID_NUMBER": [
        # US SSN (Social Security Number)
        r"\b\d{3}-\d{2}-\d{4}\b",
        # Indian Aadhaar Number
        r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        # Indian PAN Card Number
        r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",
        # Passport Number
        r"\b[A-PR-WYa-pr-wy][0-9]{7}\b"
    ],
    "SECRET_KEY": [
        # API Keys, Private Keys, Password Strings
        r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|bearer[_-]?token|password)[\s:=]+['\"]?([a-zA-Z0-9_\-]{16,64})['\"]?\b",
        # RSA / SSH Private Key Header
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ],
    "EMAIL_ADDRESS": [
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    ],
    "PHONE_NUMBER": [
        r"(?:\+\d{1,3}[-.\s]?)?\b\d{3}[-.\s]?\d{3,4}[-.\s]?\d{4}\b",
        r"(?:\+\d{1,3}[-.\s]?)?\b\d{3,4}[-.\s]?\d{3,4}\b",
        r"\b\d{10,11}\b"
    ],
    "PERSON": [
        r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b"
    ]
}

# Try initializing Presidio PatternRecognizer without spaCy download dependency
HAS_PRESIDIO_PATTERN = False
try:
    from presidio_analyzer import PatternRecognizer, Pattern
    HAS_PRESIDIO_PATTERN = True
except ImportError:
    HAS_PRESIDIO_PATTERN = False

class PrivacyDetector:
    """
    Local-First Privacy Detector combining Presidio Pattern Recognizers and Regex.
    Executes 100% offline with zero external network downloads.
    """

    def __init__(self):
        self.presidio_recognizers = []
        if HAS_PRESIDIO_PATTERN:
            for entity_type, patterns in CUSTOM_REGEX_PATTERNS.items():
                presidio_patterns = [
                    Pattern(name=f"{entity_type}_pat_{i}", regex=p, score=0.9)
                    for i, p in enumerate(patterns)
                ]
                rec = PatternRecognizer(
                    supported_entity=entity_type,
                    patterns=presidio_patterns
                )
                self.presidio_recognizers.append(rec)

    def detect(self, text: str) -> List[DetectedEntity]:
        if not text or not text.strip():
            return []

        detected_entities: List[DetectedEntity] = []
        seen_spans = set()

        # 1. Run Presidio Pattern Recognizers locally
        if self.presidio_recognizers:
            for rec in self.presidio_recognizers:
                try:
                    results = rec.analyze(text, entities=[rec.supported_entities[0]])
                    for res in results:
                        span_key = (res.start, res.end)
                        if span_key not in seen_spans:
                            seen_spans.add(span_key)
                            detected_entities.append(
                                DetectedEntity(
                                    entity_type=res.entity_type,
                                    start=res.start,
                                    end=res.end,
                                    score=round(float(res.score), 2),
                                    text_span=text[res.start:res.end]
                                )
                            )
                except Exception as e:
                    logger.debug(f"Presidio pattern scan note: {e}")

        # 2. Pure Regex scanner fallback / booster
        for entity_type, patterns in CUSTOM_REGEX_PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    start, end = match.span()
                    span_key = (start, end)
                    if span_key not in seen_spans:
                        seen_spans.add(span_key)
                        detected_entities.append(
                            DetectedEntity(
                                entity_type=entity_type,
                                start=start,
                                end=end,
                                score=0.95,
                                text_span=text[start:end]
                            )
                        )

        # Sort entities by character position
        detected_entities.sort(key=lambda x: x.start)
        return detected_entities
