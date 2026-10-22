import os
import tempfile
import pytest

from seekvault.privacy.detector import PrivacyDetector
from seekvault.privacy.redactor import PrivacyRedactor
from seekvault.privacy.classifier import PrivacyClassifier, PrivacyClassification
from seekvault.ingestion.hasher import compute_sha256
from seekvault.core.database import init_db, get_indexed_files
from seekvault.monitoring.folder_guard import FolderGuard
from seekvault.ingestion.scanner import FolderScanner

@pytest.fixture
def classifier():
    return PrivacyClassifier()

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

def test_classification_full_tier(classifier):
    clean_text = "The team meeting will review software engineering best practices and architectural design."
    result = classifier.classify(clean_text)
    
    assert isinstance(result, PrivacyClassification)
    assert result.tier == "FULL"
    assert result.sensitivity_score == 0.0
    assert len(result.detected_entities) == 0
    assert result.redacted_text == clean_text

def test_classification_redacted_tier(classifier):
    sensitive_text = "Contact Alice Smith at alice.smith@company.org or phone +1-555-0149 for support."
    result = classifier.classify(sensitive_text)
    
    assert isinstance(result, PrivacyClassification)
    assert result.tier == "REDACTED"
    assert result.sensitivity_score > 0.0
    assert len(result.detected_entities) > 0
    
    # Assert sensitive spans replaced with tokens in memory
    assert "<EMAIL>" in result.redacted_text or "<EMAIL_ADDRESS>" in result.redacted_text
    assert "<PHONE_NUMBER>" in result.redacted_text
    assert "alice.smith@company.org" not in result.redacted_text
    assert "+1-555-0149" not in result.redacted_text

def test_classification_metadata_only_tier(classifier):
    critical_text = "Confidential Card 4532111122223333 with CVV 888 and SSN 123-45-6789. secret_key=abcdef1234567890xyz."
    result = classifier.classify(critical_text)
    
    assert isinstance(result, PrivacyClassification)
    assert result.tier == "METADATA_ONLY"
    assert result.sensitivity_score >= 4.0
    assert len(result.detected_entities) > 0
    # Content stripped for safety
    assert result.redacted_text == ""

def test_zero_touch_and_db_logging(temp_db):
    """
    Verify that scanning a file containing sensitive PII applies privacy tier
    in SQLite while leaving the original file on disk 100% untouched.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        confidential_file = os.path.join(tmpdir, "confidential.txt")
        confidential_content = "Customer record: John Doe email john@domain.com card 4111222233334444"
        with open(confidential_file, "w", encoding="utf-8") as f:
            f.write(confidential_content)
            
        initial_hash = compute_sha256(confidential_file)
        
        FolderGuard.authorize_folder(tmpdir, db_path=temp_db)
        FolderScanner.scan_all_authorized_folders(custom_db_path=temp_db)
        
        # Verify original file untouched
        post_hash = compute_sha256(confidential_file)
        assert initial_hash == post_hash, "FILE MUTATED DURING PRIVACY SCAN!"
        
        # Verify DB metadata & classification
        indexed = get_indexed_files(custom_db_path=temp_db)
        assert len(indexed) == 1
        rec = indexed[0]
        assert rec["privacy_tier"] in ["REDACTED", "METADATA_ONLY"]
        assert "4111222233334444" not in (rec["extracted_text"] or "")
