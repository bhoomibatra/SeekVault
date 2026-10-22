import pytest
from pathlib import Path
import tempfile
import os
from seekvault.database.repository import Repository
from seekvault.database.connection import get_db_connection
from seekvault.database.schema import init_db

@pytest.fixture
def repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test.db"
        with get_db_connection(db_file) as conn:
            init_db(conn)
        yield Repository(db_path=db_file)

def test_folder_authorization(repo):
    folder_a = r"C:\test\academic"
    folder_b = r"C:\test\personal"
    
    id_a = repo.add_authorized_folder(folder_a, is_recursive=True)
    assert id_a > 0
    id_b = repo.add_authorized_folder(folder_b, is_recursive=False)
    assert id_b > 0
    
    assert repo.is_path_authorized(r"C:\test\academic\notes.pdf") is True
    assert repo.is_path_authorized(r"C:\test\academic\deep\nested\notes.pdf") is True
    
    # Non-recursive folder
    assert repo.is_path_authorized(r"C:\test\personal\resume.docx") is True
    assert repo.is_path_authorized(r"C:\test\personal\sub\resume.docx") is False
    
    # Unauthorized path
    assert repo.is_path_authorized(r"C:\secret\file.txt") is False
    
    # Deactivate folder
    repo.set_folder_active_state(id_a, False)
    assert repo.is_path_authorized(r"C:\test\academic\notes.pdf") is False

def test_file_upsert_and_privacy(repo):
    folder_id = repo.add_authorized_folder(r"C:\docs")
    file_id = repo.upsert_file(
        folder_id=folder_id,
        file_path=r"C:\docs\report.pdf",
        file_name="report.pdf",
        file_extension=".pdf",
        file_size=1024,
        file_hash="hash123",
        file_type="DOCUMENT",
        modified_at="2026-09-28 10:00:00",
        privacy_tier="REDACTED",
        status="INDEXED"
    )
    assert file_id > 0
    
    file_rec = repo.get_file_by_id(file_id)
    assert file_rec is not None
    assert file_rec["privacy_tier"] == "REDACTED"
    assert file_rec["file_name"] == "report.pdf"


def test_prune_missing_files(repo):
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        folder_id = repo.add_authorized_folder(str(root))

        # Create two physical files
        f1 = root / "keep.txt"
        f1.write_text("keep this file")
        f2 = root / "delete_me.txt"
        f2.write_text("delete this file")

        id1 = repo.upsert_file(
            folder_id=folder_id,
            file_path=str(f1),
            file_name="keep.txt",
            file_extension=".txt",
            file_size=len("keep this file"),
            file_hash="hash_keep",
            file_type="DOCUMENT",
            modified_at="2026-10-22 10:00:00"
        )
        id2 = repo.upsert_file(
            folder_id=folder_id,
            file_path=str(f2),
            file_name="delete_me.txt",
            file_extension=".txt",
            file_size=len("delete this file"),
            file_hash="hash_del",
            file_type="DOCUMENT",
            modified_at="2026-10-22 10:00:00"
        )

        assert repo.get_file_by_id(id1) is not None
        assert repo.get_file_by_id(id2) is not None

        # Physically delete f2 on disk
        f2.unlink()
        assert not f2.exists()

        # Run prune_missing_files
        purged = repo.prune_missing_files()
        assert id2 in purged
        assert id1 not in purged

        # Verify f2 is gone from DB while f1 remains
        assert repo.get_file_by_id(id2) is None
        assert repo.get_file_by_id(id1) is not None

        # Now deactivate the folder
        repo.set_folder_active_state(folder_id, False)
        # f1 is now unauthorized, so next prune should remove f1
        purged_unauth = repo.prune_missing_files()
        assert id1 in purged_unauth
        assert repo.get_file_by_id(id1) is None

