"""
test_settings.py — Tests for TASK-14 Settings, index reset state synchronization, and backup/restore.
"""

from pathlib import Path
import zipfile
import pytest

from seekvault.database.repository import Repository
from seekvault.database.backup import create_backup, restore_backup
from seekvault.ui.pages.settings import render_settings_page


def test_settings_callable():
    """Verify settings render function is callable."""
    assert callable(render_settings_page)


def test_reset_all_search_indices_syncs_sqlite_to_pending(tmp_path):
    """
    F-3 & R-28 & TASK-14:
    Resetting search indices must purge vector_mappings AND synchronize
    file statuses in SQLite to 'PENDING', preventing database/index drift.
    """
    db_file = tmp_path / "test_reset.db"
    repo = Repository(db_path=db_file)
    folder = tmp_path / "work"
    folder.mkdir()
    fid = repo.add_authorized_folder(str(folder))

    f1 = folder / "doc.txt"
    f1.write_text("Work report contents.", encoding="utf-8")
    rid = repo.upsert_file(
        folder_id=fid,
        file_path=str(f1),
        file_name="doc.txt",
        file_extension=".txt",
        file_size=f1.stat().st_size,
        file_hash="hash_001",
        file_type="DOCUMENT",
        modified_at="2026-01-01T00:00:00",
        status="INDEXED"
    )

    repo.save_vector_mapping(rid, modality="TEXT", faiss_vector_id=0, vector_dim=384)
    assert len(repo.get_vectors_for_file(rid)) == 1
    assert repo.get_file_by_id(rid)["status"] == "INDEXED"

    # Execute synchronized reset
    affected = repo.reset_all_search_indices()
    assert affected > 0

    # 1. Vector mappings must be completely empty
    assert len(repo.get_vectors_for_file(rid)) == 0

    # 2. File record status must be synchronized to 'PENDING'
    updated = repo.get_file_by_id(rid)
    assert updated["status"] == "PENDING"

    # 3. Source file on disk remains completely intact
    assert f1.exists()


def test_backup_and_restore_cycle(tmp_path, monkeypatch):
    """
    R-27 & TASK-14:
    Test creating a backup archive and safely restoring it.
    """
    test_data_dir = tmp_path / "data_storage"
    test_data_dir.mkdir()
    db_file = test_data_dir / "seekvault.db"
    db_file.write_text("MOCK SQLITE DATABASE CONTENT", encoding="utf-8")

    indices_dir = test_data_dir / "indices"
    indices_dir.mkdir()
    (indices_dir / "text_index.faiss").write_bytes(b"FAISS_TEXT_BYTES")

    monkeypatch.setattr("seekvault.database.backup.DATA_DIR", test_data_dir)
    monkeypatch.setattr("seekvault.database.backup.DB_PATH", db_file)
    monkeypatch.setattr("seekvault.database.backup.INDEX_DIR", indices_dir)

    backup_dest = tmp_path / "backups"
    backup_zip = create_backup(destination_dir=backup_dest)

    assert backup_zip.exists()
    assert zipfile.is_zipfile(backup_zip)

    # Wipe mock data
    db_file.unlink()
    assert not db_file.exists()

    # Restore backup
    ok, msg = restore_backup(backup_zip)
    assert ok
    assert "successfully restored" in msg.lower()
    assert db_file.exists()
    assert db_file.read_text(encoding="utf-8") == "MOCK SQLITE DATABASE CONTENT"


def test_restore_invalid_archive(tmp_path):
    """Verify restore fails safely when given invalid or corrupt files."""
    fake_zip = tmp_path / "corrupt.zip"
    fake_zip.write_text("NOT A ZIP FILE")

    ok, msg = restore_backup(fake_zip)
    assert not ok
    assert "not a valid zip" in msg.lower()

    ok, msg = restore_backup(tmp_path / "nonexistent.zip")
    assert not ok
    assert "does not exist" in msg.lower()
