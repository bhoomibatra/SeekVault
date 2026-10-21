from typing import List, Dict, Any

class PrivacySanitizer:
    @staticmethod
    def sanitize(text: str, detected_entities: List[Dict[str, Any]]) -> str:
        """
        Replace detected sensitive entities with placeholders in text.
        NOTE: Original user files are NEVER modified. This applies ONLY to
        the searchable representation and text embeddings.
        """
        if not text or not detected_entities:
            return text

        # Sort entities by start_char descending so string splicing does not shift indices
        sorted_entities = sorted(detected_entities, key=lambda x: x["start_char"], reverse=True)

        sanitized = text
        for ent in sorted_entities:
            start = ent["start_char"]
            end = ent["end_char"]
            ent_type = ent["entity_type"]
            placeholder = f"<{ent_type}>"
            sanitized = sanitized[:start] + placeholder + sanitized[end:]

        return sanitized
