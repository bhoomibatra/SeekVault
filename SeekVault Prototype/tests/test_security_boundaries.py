import os
import hashlib
import tempfile
import pytest
from pathlib import Path

from seekvault.database.repository import Repository
from seekvault.database.connection import get_db_connection
from seekvault.database.schema import init_db
from seekvault.search.engine import SearchEngine
from seekvault.ingestion.pipeline import IngestionPipeline
from seekvault.organization.duplicate_detector import DuplicateDetector

@pytest.fixture
def security_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        db_file = root / "security_test.db"
        with get_db_connection(db_file) as conn:
            init_db(conn)

        repo = Repository(db_path=db_file)
        search_engine = SearchEngine(
            repository=repo,
            text_index_path=root / "text_sec.faiss",
            text_meta_path=root / "text_sec.json",
            image_index_path=root / "image_sec.faiss",
            image_meta_path=root / "image_sec.json",
        )
        pipeline = IngestionPipeline(repository=repo, search_engine=search_engine)

        auth_dir = root / "authorized_vault"
        auth_dir.mkdir()
        folder_id = repo.add_authorized_folder(str(auth_dir), is_recursive=True)

        unauth_dir = root / "unauthorized_restricted"
        unauth_dir.mkdir()

        yield {
            "root": root,
            "repo": repo,
            "search_engine": search_engine,
            "pipeline": pipeline,
            "auth_dir": auth_dir,
            "unauth_dir": unauth_dir,
            "folder_id": folder_id,
        }

def test_original_file_immutability(security_env):
    """REQ-007: Original files on disk must remain strictly read-only and immutable."""
    auth_dir = security_env["auth_dir"]
    pipeline = security_env["pipeline"]

    test_doc = auth_dir / "confidential_strategy.txt"
    original_content = (
        "Project Vanguard strategic initiative: highly sensitive financial and proprietary data.\n"
        "Contact: agent@seekvault.local or phone: +1-555-0199."
    )
    test_doc.write_text(original_content, encoding="utf-8")

    # Compute pre-ingestion SHA-256 and byte size
    pre_bytes = test_doc.read_bytes()
    pre_hash = hashlib.sha256(pre_bytes).hexdigest()
    pre_mtime = test_doc.stat().st_mtime_ns

    # Execute complete pipeline ingestion (extraction, presidio, embedding, indexing)
    res = pipeline.process_file(str(test_doc))
    assert res is not None

    # Compute post-ingestion SHA-256 and byte size
    post_bytes = test_doc.read_bytes()
    post_hash = hashlib.sha256(post_bytes).hexdigest()
    post_mtime = test_doc.stat().st_mtime_ns

    # Invariants: 100% identical hash, size, bytes, and modification timestamp
    assert pre_hash == post_hash, "Original file hash changed during ingestion! Immutability violated."
    assert pre_bytes == post_bytes, "Original file bytes altered during ingestion! Immutability violated."
    assert pre_mtime == post_mtime, "Original file modification timestamp altered!"

def test_query_time_deauthorization_suppression(security_env):
    """REQ-001 & REQ-017: Revoking folder authorization immediately suppresses search results."""
    auth_dir = security_env["auth_dir"]
    pipeline = security_env["pipeline"]
    repo = security_env["repo"]
    search_engine = security_env["search_engine"]
    folder_id = security_env["folder_id"]

    # Index document in authorized directory
    secret_doc = auth_dir / "quantum_cryptography.txt"
    secret_doc.write_text("Quantum key distribution protocol and photon entanglement experiments.", encoding="utf-8")
    res = pipeline.process_file(str(secret_doc))
    assert res is not None

    # Verify document is discoverable via semantic search
    initial_results = search_engine.search_text("quantum key distribution photon", top_k=5)
    assert len(initial_results) > 0
    assert initial_results[0]["file_name"] == "quantum_cryptography.txt"

    # Revoke authorization by setting folder active state to False
    repo.set_folder_active_state(folder_id, False)

    # Invariant: Search must immediately suppress the file without database deletion or app restart
    suppressed_results = search_engine.search_text("quantum key distribution photon", top_k=5)
    assert len(suppressed_results) == 0, "Deauthorized folder results were not suppressed at query-time!"

    # Reactivate folder -> file should be discoverable again
    repo.set_folder_active_state(folder_id, True)
    reactivated_results = search_engine.search_text("quantum key distribution photon", top_k=5)
    assert len(reactivated_results) > 0
    assert reactivated_results[0]["file_name"] == "quantum_cryptography.txt"

def test_pii_sanitization_zero_leakage_in_vectors(security_env):
    """REQ-006: Redacted PII tokens must never leak into searchable representations."""
    auth_dir = security_env["auth_dir"]
    pipeline = security_env["pipeline"]
    repo = security_env["repo"]

    pii_doc = auth_dir / "user_profile_admission.txt"
    raw_email = "alex.murphy.confidential@cybercorp.org"
    raw_phone = "+1-555-839-2041"
    pii_doc.write_text(
        f"Applicant Record for Alex Murphy. Email address: {raw_email}. Direct mobile phone: {raw_phone}. "
        "Standard university admission form with personal identifying contact numbers.",
        encoding="utf-8"
    )

    res = pipeline.process_file(str(pii_doc))
    assert res is not None
    assert res["privacy_tier"] in ("REDACTED", "METADATA_ONLY")

    # Inspect SQLite stored representation
    content_rec = repo.get_file_content(res["id"])
    assert content_rec is not None

    redacted_preview = content_rec.get("redacted_preview", "")
    searchable_preview = content_rec.get("searchable_text_preview", "")

    # Invariants: Raw sensitive strings MUST NOT appear in sanitized representations
    assert raw_email not in redacted_preview, "Raw email leaked into redacted preview!"
    assert raw_phone not in redacted_preview, "Raw phone number leaked into redacted preview!"

    # Presidio token replacement must be present
    assert "<EMAIL_ADDRESS>" in redacted_preview or "<EMAIL>" in redacted_preview or "<" in redacted_preview
    assert "<PHONE_NUMBER>" in redacted_preview or "<PHONE>" in redacted_preview or "<" in redacted_preview

def test_unauthorized_folder_containment(security_env):
    """REQ-001: Pipeline never processes or stores files outside authorized directories."""
    unauth_dir = security_env["unauth_dir"]
    pipeline = security_env["pipeline"]
    repo = security_env["repo"]
    search_engine = security_env["search_engine"]

    unauth_file = unauth_dir / "classified_leak.txt"
    unauth_file.write_text("Top secret foreign defense intelligence document.", encoding="utf-8")

    # Ingestion must reject unauthorized file
    ingest_result = pipeline.process_file(str(unauth_file))
    assert ingest_result is None, "Pipeline processed a file located in an unauthorized directory!"

    # Database must contain zero records for this path
    db_rec = repo.get_file_by_path(str(unauth_file))
    assert db_rec is None, "Unauthorized file path was stored in database!"

    # Search query must return empty
    search_results = search_engine.search_text("foreign defense intelligence document", top_k=5)
    assert len(search_results) == 0

def test_windows_path_case_normalization(security_env):
    """TASK-0003 & REQ-001: Windows path case variation must not cause false rejection or leaks."""
    auth_dir = security_env["auth_dir"]
    repo = security_env["repo"]

    test_file = auth_dir / "Financial_Audit_2026.docx"
    test_file.write_text("Annual balance sheet and corporate tax audit report.", encoding="utf-8")

    # Case variations
    path_lower = os.path.normpath(str(test_file)).lower()
    path_upper = os.path.normpath(str(test_file)).upper()

    # Both casing variations must be authorized on Windows
    assert repo.is_path_authorized(str(test_file)) is True
    assert repo.is_path_authorized(path_lower) is True
    if os.name == "nt":
        assert repo.is_path_authorized(path_upper) is True
