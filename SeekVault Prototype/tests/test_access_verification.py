import os
import pytest
import tempfile
from pathlib import Path
from seekvault.database.repository import Repository
from seekvault.database.connection import get_db_connection
from seekvault.database.schema import init_db
from seekvault.search.verifier import AccessVerifier

@pytest.fixture
def repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test.db"
        with get_db_connection(db_file) as conn:
            init_db(conn)
        yield Repository(db_path=db_file)

def test_query_time_access_verification(repo):
    with tempfile.TemporaryDirectory() as authorized_dir:
        auth_path = Path(authorized_dir)
        test_file = auth_path / "valid_document.txt"
        test_file.write_text("Some notes on machine learning")

        # 1. Authorize folder
        folder_id = repo.add_authorized_folder(str(auth_path), is_recursive=True)
        file_id = repo.upsert_file(
            folder_id=folder_id,
            file_path=str(test_file),
            file_name="valid_document.txt",
            file_extension=".txt",
            file_size=len("Some notes on machine learning"),
            file_hash="dummyhash123",
            file_type="DOCUMENT",
            modified_at="2026-09-28 10:00:00",
            privacy_tier="FULL"
        )

        candidate_results = [(file_id, 0.95)]

        # File is authorized and exists -> Verified
        filtered = AccessVerifier.filter_results(candidate_results, repo)
        assert len(filtered) == 1
        assert filtered[0][0]["id"] == file_id

        # 2. Deactivate folder authorization -> File must be SUPPRESSED at query time
        repo.set_folder_active_state(folder_id, False)
        filtered_suppressed = AccessVerifier.filter_results(candidate_results, repo)
        assert len(filtered_suppressed) == 0

        # 3. Reactivate folder, but delete file from disk -> File must be SUPPRESSED
        repo.set_folder_active_state(folder_id, True)
        test_file.unlink()
        filtered_deleted = AccessVerifier.filter_results(candidate_results, repo)
        assert len(filtered_deleted) == 0


def test_case_insensitive_path_authorization(repo):
    """TASK-0003 regression: drive-letter and directory casing must not affect
    authorization on Windows. os.path.normcase folds case before containment
    checks, so 'C:\\Docs\\Notes\\file.txt' is authorized when 'c:\\docs\\notes'
    is the registered folder, and vice versa."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        subdir = base / "SubDir"
        subdir.mkdir()
        test_file = subdir / "report.txt"
        test_file.write_text("Quarterly financial report")

        # Authorize using mixed-case path of the subdirectory
        folder_id = repo.add_authorized_folder(str(subdir), is_recursive=True)

        # Produce the same path but with opposite case via os.path.normcase
        # On Windows normcase lowercases; on Linux/Mac it is a no-op.
        # We build both variants and verify at least the normcase version
        # is authorised (the core fix).
        lowercased = os.path.normcase(str(test_file))
        uppercased = str(test_file).upper() if os.name == "nt" else str(test_file)

        # Normcase path must always be authorized
        assert repo.is_path_authorized(lowercased), (
            f"Normcase path '{lowercased}' should be authorized inside '{subdir}'"
        )

        # Original path must also be authorized
        assert repo.is_path_authorized(str(test_file)), (
            f"Original path '{test_file}' should be authorized"
        )

        # On Windows, uppercased path must also be authorized (the casing bug fix)
        if os.name == "nt":
            assert repo.is_path_authorized(uppercased), (
                f"Uppercase path '{uppercased}' should be authorized on Windows "
                f"after normcase fix (TASK-0003)"
            )

        # get_folder_for_path must return the correct folder ID as well
        resolved_folder_id = repo.get_folder_for_path(lowercased)
        assert resolved_folder_id == folder_id, (
            f"get_folder_for_path returned {resolved_folder_id}, expected {folder_id}"
        )

        # A file completely outside the authorized tree must NOT be authorized
        outside_file = base / "outside.txt"
        outside_file.write_text("Unauthorized content")
        assert not repo.is_path_authorized(str(outside_file)), (
            f"File outside authorized tree must never be authorized"
        )


def test_non_recursive_folder_boundary(repo):
    """Non-recursive folders must authorize only files directly inside them,
    not files inside subdirectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        nested = base / "nested"
        nested.mkdir()

        direct_file = base / "direct.txt"
        direct_file.write_text("Direct child")
        nested_file = nested / "deep.txt"
        nested_file.write_text("Nested child")

        # Authorize base non-recursively
        repo.add_authorized_folder(str(base), is_recursive=False)

        assert repo.is_path_authorized(str(direct_file)), \
            "Direct child must be authorized in non-recursive mode"
        assert not repo.is_path_authorized(str(nested_file)), \
            "Nested file must NOT be authorized in non-recursive mode"

