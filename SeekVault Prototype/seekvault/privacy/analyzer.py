import hashlib
from typing import List, Dict, Any
import logging
from seekvault.privacy.recognizers import scan_custom_patterns

logger = logging.getLogger(__name__)

class PrivacyAnalyzer:
    _presidio_recognizers = None

    @classmethod
    def _get_presidio_recognizers(cls):
        if cls._presidio_recognizers is None:
            recognizers = []
            try:
                from presidio_analyzer.predefined_recognizers import (
                    EmailRecognizer,
                    PhoneRecognizer,
                    CreditCardRecognizer,
                    CryptoRecognizer,
                    IbanRecognizer
                )
                recognizers.extend([
                    EmailRecognizer(),
                    PhoneRecognizer(),
                    CreditCardRecognizer(),
                    CryptoRecognizer(),
                    IbanRecognizer()
                ])
                logger.info("Presidio predefined recognizers loaded.")
            except Exception as e:
                logger.warning(f"Could not load Presidio recognizers: {e}")
            cls._presidio_recognizers = recognizers
        return cls._presidio_recognizers

    @classmethod
    def analyze(cls, text: str, entities: List[str] = None) -> List[Dict[str, Any]]:
        """
        Analyze text using Presidio Recognizers supplemented with Custom Regex.
        Returns a list of standardized entity dictionaries:
        [{"entity_type": ..., "entity_text": ..., "start_char": ..., "end_char": ..., "confidence": ...}]
        """
        if not text or not text.strip():
            return []

        detected_entities: List[Dict[str, Any]] = []

        # 1. Custom Regex Recognizers (Aadhaar, PAN, custom phone/keys/emails)
        custom_matches = scan_custom_patterns(text)
        detected_entities.extend(custom_matches)

        # 2. Presidio Predefined Recognizers
        presidio_recs = cls._get_presidio_recognizers()
        for rec in presidio_recs:
            try:
                results = rec.analyze(text=text, entities=entities)
                if results:
                    for res in results:
                        entity_str = text[res.start:res.end]
                        h = hashlib.sha256(entity_str.encode("utf-8")).hexdigest()[:6]
                        detected_entities.append({
                            "entity_type": res.entity_type,
                            "entity_text": entity_str,
                            "entity_token": f"<{res.entity_type}_REDACTED_{h}>",
                            "start_char": res.start,
                            "end_char": res.end,
                            "confidence": round(res.score, 2)
                        })
            except Exception as e:
                logger.debug(f"Recognizer {rec.name} error: {e}")

        # Deduplicate and sort by start_char
        seen_spans = set()
        deduped = []
        for ent in sorted(detected_entities, key=lambda x: (x["start_char"], -x["end_char"])):
            span = (ent["start_char"], ent["end_char"])
            if span not in seen_spans:
                seen_spans.add(span)
                deduped.append(ent)

        return deduped
