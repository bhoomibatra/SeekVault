import pytest
import tempfile
from pathlib import Path
from seekvault.database.repository import Repository
from seekvault.database.connection import get_db_connection
from seekvault.database.schema import init_db
from seekvault.organization.duplicate_detector import DuplicateDetector
from seekvault.organization.version_detector import VersionDetector

@pytest.fixture
def repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test.db"
        with get_db_connection(db_file) as conn:
            init_db(conn)
        yield Repository(db_path=db_file)

def test_duplicate_hashing_and_detection(repo):
    with tempfile.TemporaryDirectory() as tmpdir:
        dir_path = Path(tmpdir)
        file1 = dir_path / "original.pdf"
        file2 = dir_path / "copy_of_original.pdf"

        content = b"Exact identical binary content for testing hash duplicate detection"
        file1.write_bytes(content)
        file2.write_bytes(content)

        hash1 = DuplicateDetector.calculate_file_hash(file1)
        hash2 = DuplicateDetector.calculate_file_hash(file2)
        assert hash1 == hash2

        folder_id = repo.add_authorized_folder(str(dir_path))
        repo.upsert_file(folder_id, str(file1), "original.pdf", ".pdf", len(content), hash1, "DOCUMENT", "2026-09-28 10:00:00")
        repo.upsert_file(folder_id, str(file2), "copy_of_original.pdf", ".pdf", len(content), hash2, "DOCUMENT", "2026-09-28 10:05:00")

        duplicates = repo.get_duplicate_groups()
        assert len(duplicates) == 1
        assert duplicates[0]["file_count"] == 2
        assert duplicates[0]["file_hash"] == hash1

def test_version_stem_extraction():
    stem1 = VersionDetector.extract_base_stem("Project_Report_Draft_v1.docx")
    stem2 = VersionDetector.extract_base_stem("Project_Report_Draft_v2.docx")
    stem3 = VersionDetector.extract_base_stem("Project_Report_Final.docx")
    assert stem1 == "project_report"
    assert stem2 == "project_report"
    assert stem3 == "project_report"
