import pytest
from seekvault.privacy.analyzer import PrivacyAnalyzer
from seekvault.privacy.sanitizer import PrivacySanitizer
from seekvault.privacy.classifier import PrivacyClassifier
from seekvault.config import TIER_FULL, TIER_REDACTED, TIER_METADATA_ONLY

def test_detect_email_and_phone():
    text = "Please reach out to harsh@example.com or call +91 9876543210 for details."
    entities = PrivacyAnalyzer.analyze(text)
    types = [e["entity_type"] for e in entities]
    assert "EMAIL_ADDRESS" in types
    assert "PHONE_NUMBER" in types

def test_detect_aadhaar_and_pan():
    text = "Student verification: Aadhaar 4521 8963 1254 and PAN ABCDE1234F."
    entities = PrivacyAnalyzer.analyze(text)
    types = [e["entity_type"] for e in entities]
    assert "AADHAAR_NUMBER" in types
    assert "PAN_NUMBER" in types

def test_sanitization_placeholders():
    text = "Contact me at alice@domain.com or 123-456-7890."
    entities = PrivacyAnalyzer.analyze(text)
    sanitized = PrivacySanitizer.sanitize(text, entities)
    assert "alice@domain.com" not in sanitized
    assert "123-456-7890" not in sanitized
    assert "<EMAIL_ADDRESS>" in sanitized
    assert "<PHONE_NUMBER>" in sanitized

def test_classification_tiers():
    # 1. Clean academic text -> FULL
    clean_text = "The Candidate Elimination Algorithm outputs a version space."
    clean_ents = PrivacyAnalyzer.analyze(clean_text)
    tier1 = PrivacyClassifier.classify("ml_notes.txt", clean_text, clean_ents)
    assert tier1 == TIER_FULL

    # 2. Text with PII -> REDACTED
    pii_text = "My phone is 9876543210."
    pii_ents = PrivacyAnalyzer.analyze(pii_text)
    tier2 = PrivacyClassifier.classify("contact.txt", pii_text, pii_ents)
    assert tier2 == TIER_REDACTED

    # 3. Confidential password file -> METADATA_ONLY
    pass_text = "Master recovery keys."
    pass_ents = []
    tier3 = PrivacyClassifier.classify("master_password_vault.txt", pass_text, pass_ents)
    assert tier3 == TIER_METADATA_ONLY
