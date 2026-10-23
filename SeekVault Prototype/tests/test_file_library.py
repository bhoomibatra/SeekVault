"""
test_file_library.py — Tests for TASK-11 File Library, safe revocation, and PII masking.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from seekvault.database.repository import Repository
from seekvault.ui.pages.file_library import render_file_library_page


def test_file_library_import():
    """Verify file_library module imports cleanly."""
    assert callable(render_file_library_page)


def test_safe_revocation_leaves_original_files_intact(tmp_path):
    """
    REQ-001 & TASK-11:
    Revoking an authorized folder removes it from SeekVault's records,
    but original physical files on disk MUST strictly remain intact.
    """
    db_file = tmp_path / "test_library.db"
    repo = Repository(db_path=db_file)

    auth_dir = tmp_path / "confidential_project"
    auth_dir.mkdir()
    sample_file = auth_dir / "whitepaper.txt"
    sample_content = "Confidential architectural whitepaper contents."
    sample_file.write_text(sample_content, encoding="utf-8")

    fid = repo.add_authorized_folder(str(auth_dir))
    rid = repo.upsert_file(
        folder_id=fid,
        file_path=str(sample_file),
        file_name="whitepaper.txt",
        file_extension=".txt",
        file_size=sample_file.stat().st_size,
        file_hash="sample_sha256_hash",
        file_type="DOCUMENT",
        modified_at="2026-01-01T00:00:00",
        status="INDEXED"
    )

    assert repo.is_path_authorized(str(sample_file))
    assert repo.get_file_by_id(rid) is not None

    # Simulate user confirming revocation
    revoked = repo.remove_authorized_folder(fid)
    assert revoked

    # 1. Path must no longer be authorized
    assert not repo.is_path_authorized(str(sample_file))

    # 2. File record in DB purged or suppressed
    assert repo.get_authorized_folders() == []

    # 3. PHYSICAL SOURCE FILE ON DISK MUST STILL EXIST AND BE BIT-FOR-BIT IDENTICAL
    assert sample_file.exists()
    assert sample_file.read_text(encoding="utf-8") == sample_content


def test_zero_raw_pii_in_detected_entities(tmp_path):
    """
    TASK-11 & TASK-07:
    Entity audit records must store and present masked tokens only,
    never unmasked raw PII text.
    """
    db_file = tmp_path / "test_pii_audit.db"
    repo = Repository(db_path=db_file)

    folder = tmp_path / "admissions"
    folder.mkdir()
    fid = repo.add_authorized_folder(str(folder))
    f = folder / "student.txt"
    f.write_text("Student record", encoding="utf-8")

    rid = repo.upsert_file(
        folder_id=fid,
        file_path=str(f),
        file_name="student.txt",
        file_extension=".txt",
        file_size=f.stat().st_size,
        file_hash="hash_123",
        file_type="DOCUMENT",
        modified_at="2026-01-01T00:00:00",
        status="INDEXED"
    )

    # Ingest entities with raw PII
    raw_email = "student.private@university.edu"
    raw_phone = "+91-9876543210"
    repo.save_detected_entities(rid, [
        {"entity_type": "EMAIL_ADDRESS", "entity_text": raw_email, "confidence": 0.95},
        {"entity_type": "PHONE_NUMBER", "entity_text": raw_phone, "confidence": 0.90},
    ])

    entities = repo.get_detected_entities_for_file(rid)
    assert len(entities) == 2

    for ent in entities:
        # Must not contain unmasked raw PII
        assert raw_email not in ent["entity_token"]
        assert raw_phone not in ent["entity_token"]
        # Must contain redacted token format
        assert "REDACTED" in ent["entity_token"] or ent["entity_token"].startswith("<")


def test_folder_file_counts_breakdown(tmp_path):
    """Verify get_folder_file_counts accurately tallies status categories."""
    db_file = tmp_path / "test_counts.db"
    repo = Repository(db_path=db_file)

    folder = tmp_path / "docs"
    folder.mkdir()
    fid = repo.add_authorized_folder(str(folder))

    # Add 2 INDEXED, 1 FAILED, 1 PENDING
    repo.upsert_file(folder_id=fid, file_path=str(folder / "f1.txt"), file_name="f1.txt", file_extension=".txt", file_size=10, file_hash="h1", file_type="DOCUMENT", modified_at="2026-01-01", status="INDEXED")
    repo.upsert_file(folder_id=fid, file_path=str(folder / "f2.txt"), file_name="f2.txt", file_extension=".txt", file_size=10, file_hash="h2", file_type="DOCUMENT", modified_at="2026-01-01", status="INDEXED")
    repo.upsert_file(folder_id=fid, file_path=str(folder / "f3.txt"), file_name="f3.txt", file_extension=".txt", file_size=10, file_hash="h3", file_type="DOCUMENT", modified_at="2026-01-01", status="FAILED")
    repo.upsert_file(folder_id=fid, file_path=str(folder / "f4.txt"), file_name="f4.txt", file_extension=".txt", file_size=10, file_hash="h4", file_type="DOCUMENT", modified_at="2026-01-01", status="PENDING")

    counts = repo.get_folder_file_counts()
    assert fid in counts
    assert counts[fid]["indexed"] == 2
    assert counts[fid]["failed"] == 1
    assert counts[fid]["pending"] == 1
