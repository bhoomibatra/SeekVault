import os
import tempfile
import sqlite3
from pathlib import Path
import pytest
from unittest.mock import patch

from seekvault.database.repository import Repository
from seekvault.ingestion.pipeline import IngestionPipeline
from seekvault.search.engine import SearchEngine
from seekvault.privacy.classifier import PrivacyClassifier
from seekvault.privacy.analyzer import PrivacyAnalyzer
from seekvault.privacy.sanitizer import PrivacySanitizer
from seekvault import config


@pytest.fixture
def privacy_test_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        db_path = base_dir / "test_privacy.db"
        text_idx_path = base_dir / "text_index.faiss"
        text_meta_path = base_dir / "text_ids.json"
        img_idx_path = base_dir / "image_index.faiss"
        img_meta_path = base_dir / "image_ids.json"

        repo = Repository(db_path=db_path)
        search_engine = SearchEngine(
            repository=repo,
            text_index_path=text_idx_path,
            text_meta_path=text_meta_path,
            image_index_path=img_idx_path,
            image_meta_path=img_meta_path
        )
        pipeline = IngestionPipeline(repository=repo, search_engine=search_engine)

        auth_dir = base_dir / "authorized_docs"
        auth_dir.mkdir()
        repo.add_authorized_folder(str(auth_dir), is_recursive=True)

        yield {
            "pipeline": pipeline,
            "repo": repo,
            "engine": search_engine,
            "auth_dir": auth_dir,
            "db_path": db_path
        }


def test_stored_representation_zero_pii_leakage_in_sqlite(privacy_test_env):
    """TASK-07: Verify stored SQLite representations (file_content & detected_entities)
    contain ZERO raw PII strings (emails, phones, PAN, Aadhaar, credit cards)."""
    pipeline = privacy_test_env["pipeline"]
    repo = privacy_test_env["repo"]
    auth_dir = privacy_test_env["auth_dir"]
    db_path = privacy_test_env["db_path"]

    raw_email = "sensitive.executive@enterprise.org"
    raw_phone = "+91 9876543210"
    raw_pan = "ABCDE1234F"
    raw_aadhaar = "1234 5678 9012"
    raw_card = "4111 2222 3333 4444"

    doc = auth_dir / "confidential_employee_profile.txt"
    doc.write_text(
        f"Employee Personnel File.\n"
        f"Official Email: {raw_email}\n"
        f"Contact Number: {raw_phone}\n"
        f"Income Tax PAN: {raw_pan}\n"
        f"Identity Aadhaar: {raw_aadhaar}\n"
        f"Corporate Card: {raw_card}\n"
        f"General role: Departmental Operations Director.",
        encoding="utf-8"
    )

    res = pipeline.process_file(str(doc))
    assert res is not None
    assert res["privacy_tier"] == "REDACTED"
    file_id = res["id"]

    # 1. Query file_content directly from SQLite to inspect stored text representations
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM file_content WHERE file_id = ?", (file_id,)).fetchone()
    conn.close()

    assert row is not None
    searchable_preview = row["searchable_text_preview"]
    redacted_preview = row["redacted_preview"]

    pii_samples = [raw_email, raw_phone, raw_pan, raw_aadhaar, raw_card]
    for pii in pii_samples:
        assert pii not in searchable_preview, f"Raw PII '{pii}' leaked into searchable_text_preview!"
        assert pii not in redacted_preview, f"Raw PII '{pii}' leaked into redacted_preview!"

    # 2. Query detected_entities table: ensure entity_token contains masked tokens, never raw PII
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    entity_rows = conn.execute("SELECT * FROM detected_entities WHERE file_id = ?", (file_id,)).fetchall()
    conn.close()

    assert len(entity_rows) >= 3, f"Expected at least 3 detected entities, found {len(entity_rows)}"
    for r in entity_rows:
        token = r["entity_token"]
        for pii in pii_samples:
            assert pii not in token, f"Raw PII '{pii}' leaked into detected_entities.entity_token ({token})!"
        assert token.startswith("<") and token.endswith(">"), f"Token is not properly masked: {token}"


def test_metadata_only_zero_vector_and_zero_snippet_leakage(privacy_test_env):
    """TASK-07: Files classified as METADATA_ONLY must store exactly ZERO vectors in FAISS,
    must have content hidden in SQLite, and cannot be retrieved via body text queries."""
    pipeline = privacy_test_env["pipeline"]
    repo = privacy_test_env["repo"]
    engine = privacy_test_env["engine"]
    auth_dir = privacy_test_env["auth_dir"]
    db_path = privacy_test_env["db_path"]

    # Content with explicit private key header and master credentials
    secret_doc = auth_dir / "production_master_credentials.txt"
    secret_phrase = "super_classified_orbit_encryption_payload_987654"
    secret_doc.write_text(
        f"-----BEGIN RSA PRIVATE KEY-----\n"
        f"MIIEowIBAAKCAQEA0987654321xyz...\n"
        f"Payload: {secret_phrase}\n"
        f"-----END RSA PRIVATE KEY-----\n",
        encoding="utf-8"
    )

    res = pipeline.process_file(str(secret_doc))
    assert res is not None
    assert res["privacy_tier"] == "METADATA_ONLY"
    file_id = res["id"]

    # 1. Stored preview in SQLite must be hidden
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM file_content WHERE file_id = ?", (file_id,)).fetchone()
    conn.close()

    assert row is not None
    assert secret_phrase not in row["searchable_text_preview"]
    assert "CONTENT HIDDEN" in row["searchable_text_preview"]
    assert "CONTENT HIDDEN" in row["redacted_preview"]
    assert row["raw_char_count"] == 0

    # 2. Vector mappings in SQLite must be completely empty for this file
    mappings = repo.get_vectors_for_file(file_id)
    assert len(mappings) == 0, f"METADATA_ONLY file must have 0 vector mappings, got {len(mappings)}"

    # 3. FAISS index must NOT have this file
    assert not engine.text_index.has_file(file_id)

    # 4. Search query for body text must return 0 matches
    search_results = engine.search_text(secret_phrase, top_k=5)
    assert len(search_results) == 0, "METADATA_ONLY content should not be retrievable via text search"


def test_false_positives_clean_policy_and_protocol_discussions():
    """TASK-07: Academic or policy text discussing passwords or privacy without actual credentials
    must NOT falsely trigger METADATA_ONLY or REDACTED."""
    # 1. Clean academic text
    clean_academic = (
        "In computer science, a secure hashing function ensures data integrity. "
        "Algorithms such as SHA-256 and BLAKE2 produce fixed-size digests."
    )
    ents = PrivacyAnalyzer.analyze(clean_academic)
    assert len(ents) == 0
    tier = PrivacyClassifier.classify("hash_functions.txt", clean_academic, ents)
    assert tier == "FULL"

    # 2. Policy text mentioning password guidelines
    policy_text = (
        "Organizational Password Policy: All employees must construct passwords "
        "containing at least 14 characters. Passwords must not be reused."
    )
    ents_policy = PrivacyAnalyzer.analyze(policy_text)
    # Ensure policy guideline does not match actual credential syntax
    assert not any(e["entity_type"] == "CONFIDENTIAL_KEY" for e in ents_policy)
    tier_policy = PrivacyClassifier.classify("it_policy.docx", policy_text, ents_policy)
    assert tier_policy == "FULL"


def test_false_negatives_and_malformed_pii_recognition():
    """TASK-07: Recognizers must catch varied formats, edge cases, and international contacts."""
    # 1. International phone formats
    phones_text = "Call office at +1 (555) 234-5678 or mobile +91-9876543210 or 9876543210."
    phone_ents = PrivacyAnalyzer.analyze(phones_text)
    phone_types = [e["entity_type"] for e in phone_ents]
    assert "PHONE_NUMBER" in phone_types

    # 2. Complex emails with tags and subdomains
    email_text = "Reach engineering at dev-ops+infra_prod@sub.domain.corp.internal for deployment."
    email_ents = PrivacyAnalyzer.analyze(email_text)
    email_types = [e["entity_type"] for e in email_ents]
    assert "EMAIL_ADDRESS" in email_types

    # 3. PAN card case sensitivity / spacing
    pan_text = "Verification: PAN ABCDE1234F."
    pan_ents = PrivacyAnalyzer.analyze(pan_text)
    assert any(e["entity_type"] == "PAN_NUMBER" for e in pan_ents)


def test_image_ocr_privacy_classification(privacy_test_env):
    """TASK-07: Images containing sensitive text (via OCR) must inherit REDACTED or METADATA_ONLY
    and sanitize OCR previews accordingly."""
    pipeline = privacy_test_env["pipeline"]
    repo = privacy_test_env["repo"]
    auth_dir = privacy_test_env["auth_dir"]
    db_path = privacy_test_env["db_path"]

    img_file = auth_dir / "scanned_id_card.png"
    from PIL import Image
    img = Image.new("RGB", (100, 100), color="white")
    img.save(img_file)

    # Mock OCR output containing personal email and phone
    mock_ocr = {
        "success": True,
        "text": "Cardholder Name: Jane Doe\nEmail: jane.doe@idvault.org\nPhone: +1-555-432-1098",
        "available": True,
        "error": None
    }

    with patch("seekvault.extraction.ocr_extractor.OCRExtractor.extract_text", return_value=mock_ocr), \
         patch("seekvault.extraction.ocr_extractor.OCRExtractor.is_available", return_value=True), \
         patch("seekvault.config.ENABLE_OCR", True):
        res = pipeline.process_file(str(img_file))

    assert res is not None
    assert res["privacy_tier"] == "REDACTED"
    file_id = res["id"]

    # Verify SQLite file_content preview does not contain raw email/phone
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM file_content WHERE file_id = ?", (file_id,)).fetchone()
    conn.close()

    assert row is not None
    assert "jane.doe@idvault.org" not in row["searchable_text_preview"]
    assert "jane.doe@idvault.org" not in row["redacted_preview"]
    assert "<EMAIL_ADDRESS>" in row["redacted_preview"]
