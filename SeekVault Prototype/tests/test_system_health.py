"""
test_system_health.py — Tests for TASK-13 System Health, vector integrity diagnosis, and healing.
"""

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from seekvault.database.repository import Repository
from seekvault.ui.pages.system_health import check_vector_integrity, render_system_health_page
from seekvault.ui.pages.dashboard import render_dashboard


def test_system_health_callables():
    """Verify system health and dashboard entry points are callable."""
    assert callable(render_system_health_page)
    assert callable(render_dashboard)


def test_vector_integrity_detects_missing_vectors(tmp_path):
    """
    REQ-020 & TASK-13:
    When a file is recorded as INDEXED in SQLite but lacks an active vector in FAISS,
    check_vector_integrity must flag it as inconsistent.
    """
    db_file = tmp_path / "test_health.db"
    repo = Repository(db_path=db_file)
    folder = tmp_path / "research"
    folder.mkdir()
    fid = repo.add_authorized_folder(str(folder))

    f1 = folder / "paper.pdf"
    f1.write_text("Quantum entanglement research paper.", encoding="utf-8")
    rid = repo.upsert_file(
        folder_id=fid,
        file_path=str(f1),
        file_name="paper.pdf",
        file_extension=".pdf",
        file_size=f1.stat().st_size,
        file_hash="hash_001",
        file_type="DOCUMENT",
        modified_at="2026-01-01T00:00:00",
        privacy_tier="FULL",
        status="INDEXED"
    )

    # Mock SearchEngine whose FAISS index does NOT contain file 1
    mock_engine = MagicMock()
    mock_engine.text_index.has_file.return_value = False
    mock_engine.image_index.has_file.return_value = False
    mock_engine.text_index.index.ntotal = 0
    mock_engine.image_index.index.ntotal = 0

    diag = check_vector_integrity(repo, mock_engine)
    assert not diag["is_consistent"]
    assert diag["missing_vector_count"] == 1
    assert diag["missing_files"][0]["id"] == rid


def test_vector_integrity_ignores_metadata_only_files(tmp_path):
    """
    TASK-13 & TASK-07:
    Files classified as METADATA_ONLY legitimately have zero vectors in FAISS.
    They must NOT be flagged as missing vectors.
    """
    db_file = tmp_path / "test_health_meta.db"
    repo = Repository(db_path=db_file)
    folder = tmp_path / "credentials"
    folder.mkdir()
    fid = repo.add_authorized_folder(str(folder))

    f_vault = folder / "passwords.txt"
    f_vault.write_text("Master key list.", encoding="utf-8")
    repo.upsert_file(
        folder_id=fid,
        file_path=str(f_vault),
        file_name="passwords.txt",
        file_extension=".txt",
        file_size=f_vault.stat().st_size,
        file_hash="hash_vault",
        file_type="DOCUMENT",
        modified_at="2026-01-01T00:00:00",
        privacy_tier="METADATA_ONLY",
        status="INDEXED"
    )

    mock_engine = MagicMock()
    mock_engine.text_index.has_file.return_value = False
    mock_engine.image_index.has_file.return_value = False
    mock_engine.text_index.index.ntotal = 0
    mock_engine.image_index.index.ntotal = 0

    diag = check_vector_integrity(repo, mock_engine)
    # METADATA_ONLY file should NOT be flagged as missing vector
    assert diag["is_consistent"]
    assert diag["missing_vector_count"] == 0


def test_vector_integrity_consistent_when_all_vectors_present(tmp_path):
    """When all FULL/REDACTED files have vectors, report consistent."""
    db_file = tmp_path / "test_health_ok.db"
    repo = Repository(db_path=db_file)
    folder = tmp_path / "notes"
    folder.mkdir()
    fid = repo.add_authorized_folder(str(folder))

    f1 = folder / "note.txt"
    f1.write_text("General meeting notes.", encoding="utf-8")
    repo.upsert_file(
        folder_id=fid,
        file_path=str(f1),
        file_name="note.txt",
        file_extension=".txt",
        file_size=f1.stat().st_size,
        file_hash="hash_note",
        file_type="DOCUMENT",
        modified_at="2026-01-01T00:00:00",
        privacy_tier="FULL",
        status="INDEXED"
    )

    mock_engine = MagicMock()
    mock_engine.text_index.has_file.return_value = True
    mock_engine.image_index.has_file.return_value = True
    mock_engine.text_index.index.ntotal = 1
    mock_engine.image_index.index.ntotal = 0

    diag = check_vector_integrity(repo, mock_engine)
    assert diag["is_consistent"]
    assert diag["missing_vector_count"] == 0
    assert diag["indexed_count"] == 1


def test_human_error_description():
    """Verify friendly error descriptions for common file indexing failures."""
    from seekvault.ui.pages.system_health import _human_error_description

    assert "Access denied" in _human_error_description("PermissionError: [Errno 13] Permission denied")
    assert "password" in _human_error_description("PyPDF2.errors.FileNotDecryptedError: File is password encrypted")
    assert "empty" in _human_error_description("File is empty (0 bytes)")
    assert "moved, renamed, or deleted" in _human_error_description("FileNotFoundError: no such file or directory")


def test_indexing_status_page_alias():
    """Verify backwards compatibility alias is callable."""
    from seekvault.ui.pages.system_health import render_indexing_status_page
    assert callable(render_indexing_status_page)

