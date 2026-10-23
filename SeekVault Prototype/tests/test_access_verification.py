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


def test_sibling_prefix_path_rejection(repo):
    """TASK-05: Sibling folders that share a name prefix must NOT be authorized.
    For example, authorizing 'C:\\Vault' must NOT grant access to 'C:\\Vault_Secret'
    or 'C:\\VaultSibling'."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        auth_dir = base / "vault"
        auth_dir.mkdir()
        sibling_dir1 = base / "vault_secret"
        sibling_dir1.mkdir()
        sibling_dir2 = base / "vaultsibling"
        sibling_dir2.mkdir()

        secret_file1 = sibling_dir1 / "passwords.txt"
        secret_file1.write_text("top secret")
        secret_file2 = sibling_dir2 / "finances.xlsx"
        secret_file2.write_text("financial data")

        # Authorize only 'vault'
        repo.add_authorized_folder(str(auth_dir), is_recursive=True)

        assert not repo.is_path_authorized(str(secret_file1)), (
            f"Sibling folder '{sibling_dir1}' must NOT be authorized when only '{auth_dir}' is registered."
        )
        assert not repo.is_path_authorized(str(secret_file2)), (
            f"Sibling folder '{sibling_dir2}' must NOT be authorized when only '{auth_dir}' is registered."
        )
        assert repo.get_folder_for_path(str(secret_file1)) is None
        assert repo.get_folder_for_path(str(secret_file2)) is None


def test_nested_folders_most_specific_attribution(repo):
    """TASK-05: When both parent and child directories are authorized, files inside
    the child folder should resolve to the most specific (deepest) folder ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        parent_dir = base / "parent"
        parent_dir.mkdir()
        child_dir = parent_dir / "child"
        child_dir.mkdir()

        parent_file = parent_dir / "parent_doc.txt"
        parent_file.write_text("Parent doc")
        child_file = child_dir / "child_doc.txt"
        child_file.write_text("Child doc")

        parent_fid = repo.add_authorized_folder(str(parent_dir), is_recursive=True)
        child_fid = repo.add_authorized_folder(str(child_dir), is_recursive=True)

        assert repo.is_path_authorized(str(parent_file))
        assert repo.is_path_authorized(str(child_file))

        # Parent file belongs to parent_fid
        assert repo.get_folder_for_path(str(parent_file)) == parent_fid
        # Child file resolves to the more specific child_fid
        assert repo.get_folder_for_path(str(child_file)) == child_fid


def test_symlink_and_junction_escape_prevention(repo):
    """TASK-05: A symlink or junction inside an authorized folder that points
    outside to an unauthorized directory must be BLOCKED from indexing and query access."""
    import subprocess
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        auth_dir = base / "authorized"
        auth_dir.mkdir()
        secret_dir = base / "secret_unauthorized"
        secret_dir.mkdir()

        confidential = secret_dir / "confidential.txt"
        confidential.write_text("Confidential un-authorized data")

        repo.add_authorized_folder(str(auth_dir), is_recursive=True)

        # 1. Test directory junction escape (supported natively on Windows without admin)
        junc_path = auth_dir / "escape_junction"
        if os.name == "nt":
            res = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junc_path), str(secret_dir)],
                capture_output=True, text=True
            )
            if res.returncode == 0:
                junction_file = junc_path / "confidential.txt"
                assert junction_file.exists(), "Junction file must exist on disk"
                # Lexically it looks inside auth_dir, but physically resolves to secret_dir.
                # Must be BLOCKED.
                assert not repo.is_path_authorized(str(junction_file)), (
                    "Junction escape out of authorized root must be blocked by is_path_authorized"
                )

        # 2. Test file symlink escape (if privileges permit)
        symlink_file = auth_dir / "escape_symlink.txt"
        try:
            symlink_file.symlink_to(confidential)
            assert not repo.is_path_authorized(str(symlink_file)), (
                "Symlink pointing outside authorized root must be blocked"
            )
        except (OSError, NotImplementedError):
            # Normal on Windows if Developer Mode / SeCreateSymbolicLinkPrivilege is not held
            pass


def test_internal_junction_allowed(repo):
    """TASK-05: A junction that targets a subfolder within an authorized root is safe
    and must remain authorized."""
    import subprocess
    if os.name != "nt":
        pytest.skip("Directory junctions are Windows specific")

    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        auth_dir = base / "authorized"
        auth_dir.mkdir()
        sub_real = auth_dir / "real_sub"
        sub_real.mkdir()
        doc = sub_real / "notes.txt"
        doc.write_text("Internal valid notes")

        repo.add_authorized_folder(str(auth_dir), is_recursive=True)

        junc_path = auth_dir / "internal_link"
        res = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junc_path), str(sub_real)],
            capture_output=True, text=True
        )
        if res.returncode == 0:
            link_file = junc_path / "notes.txt"
            assert repo.is_path_authorized(str(link_file)), (
                "Internal junction pointing inside authorized root must be allowed"
            )


def test_folder_revocation_cascades_and_suppresses_results(repo):
    """TASK-05: Revoking an authorized folder:
    1. Removes the folder from authorized_folders.
    2. Deletes all associated indexed file records in SQLite via ON DELETE CASCADE.
    3. Suppresses any candidate results at query time via AccessVerifier."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        auth_dir = base / "to_revoke"
        auth_dir.mkdir()
        doc = auth_dir / "document.txt"
        doc.write_text("Temporary project proposal")

        fid = repo.add_authorized_folder(str(auth_dir), is_recursive=True)
        file_id = repo.upsert_file(
            folder_id=fid,
            file_path=str(doc),
            file_name="document.txt",
            file_extension=".txt",
            file_size=len("Temporary project proposal"),
            file_hash="hash_revocation_test",
            file_type="DOCUMENT",
            modified_at="2026-10-23 12:00:00",
            privacy_tier="FULL"
        )

        # Before revocation: file is accessible and returned
        candidates = [(file_id, 0.99)]
        results_before = AccessVerifier.filter_results(candidates, repo)
        assert len(results_before) == 1
        assert results_before[0][0]["id"] == file_id

        # Revoke folder authorization
        revoked = repo.remove_authorized_folder(fid)
        assert revoked is True

        # Folder list must not contain the revoked folder
        active_folders = repo.get_authorized_folders()
        assert not any(f["id"] == fid for f in active_folders)

        # File record in SQLite must be deleted via foreign key cascade
        file_rec = repo.get_file_by_id(file_id)
        assert file_rec is None, "File record should be deleted when authorized folder is removed (CASCADE)"

        # Query-time verifier must return 0 results
        results_after = AccessVerifier.filter_results(candidates, repo)
        assert len(results_after) == 0, "Revoked folder results must be suppressed"


def test_trailing_separators_and_parent_traversal_containment(repo):
    """Verify trailing separators and dot-dot parent traversals are handled securely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        vault_dir = base / "secure_vault"
        vault_dir.mkdir()
        outside_dir = base / "outside_dir"
        outside_dir.mkdir()

        # Add with trailing slash
        trailing_path = str(vault_dir) + os.sep
        repo.add_authorized_folder(trailing_path, is_recursive=True)

        valid_doc = vault_dir / "valid.txt"
        valid_doc.write_text("Valid content")

        # 1. Trailing separator on authorized folder still authorizes inner files
        assert repo.is_path_authorized(str(valid_doc)) is True

        # 2. File path with redundant slashes/dots still resolves correctly
        redundant_path = str(vault_dir) + os.sep + "." + os.sep + "valid.txt"
        assert repo.is_path_authorized(redundant_path) is True

        # 3. Path traversal attempting to escape vault must be blocked
        traversal_attack = str(vault_dir) + os.sep + ".." + os.sep + "outside_dir" + os.sep + "leak.txt"
        assert repo.is_path_authorized(traversal_attack) is False


def test_different_drive_letters_containment(repo):
    """Verify different drive letters on Windows or roots on POSIX are strictly rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        auth_dir = Path(tmpdir) / "vault"
        auth_dir.mkdir()
        repo.add_authorized_folder(str(auth_dir), is_recursive=True)

        # On Windows, try alternate drive letter X:
        if os.name == "nt":
            alt_drive_path = r"X:\fake_drive\secret.txt"
            assert repo.is_path_authorized(alt_drive_path) is False
        else:
            alt_root_path = "/var/secret/file.txt"
            assert repo.is_path_authorized(alt_root_path) is False


def test_search_engine_all_modes_query_time_suppression():
    """Verify SearchEngine filters revoked and deleted files across text, keyword, and hybrid paths."""
    from seekvault.search.engine import SearchEngine
    from seekvault.ingestion.pipeline import IngestionPipeline

    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        db_file = root / "multimode_sec.db"
        with get_db_connection(db_file) as conn:
            init_db(conn)

        repo = Repository(db_path=db_file)
        search_engine = SearchEngine(
            repository=repo,
            text_index_path=root / "t_sec.faiss",
            text_meta_path=root / "t_sec.json",
            image_index_path=root / "i_sec.faiss",
            image_meta_path=root / "i_sec.json",
        )
        pipeline = IngestionPipeline(repository=repo, search_engine=search_engine)

        auth_dir = root / "active_auth"
        auth_dir.mkdir()
        fid = repo.add_authorized_folder(str(auth_dir), is_recursive=True)

        doc = auth_dir / "Cyber_Defense_Strategy.txt"
        doc.write_text("Cyber defense protocol and automated firewall intrusion response.", encoding="utf-8")
        pipeline.process_file(str(doc))

        # 1. Discoverable in semantic, keyword, and hybrid modes
        res_sem = search_engine.search_text("firewall intrusion response", top_k=5)
        res_kw = search_engine.search_keyword("firewall intrusion", top_k=5)
        res_hyb = search_engine.search_hybrid("firewall intrusion response", top_k=5)

        assert any(r["file_name"] == "Cyber_Defense_Strategy.txt" for r in res_sem)
        assert any(r["file_name"] == "Cyber_Defense_Strategy.txt" for r in res_kw)
        assert any(r["file_name"] == "Cyber_Defense_Strategy.txt" for r in res_hyb)

        # 2. Deactivate folder: all modes must immediately suppress
        repo.set_folder_active_state(fid, False)
        assert len(search_engine.search_text("firewall intrusion response", top_k=5)) == 0
        assert len(search_engine.search_keyword("firewall intrusion", top_k=5)) == 0
        assert len(search_engine.search_hybrid("firewall intrusion response", top_k=5)) == 0

        # 3. Reactivate folder: discoverable again
        repo.set_folder_active_state(fid, True)
        assert len(search_engine.search_text("firewall intrusion response", top_k=5)) > 0
        assert len(search_engine.search_keyword("firewall intrusion", top_k=5)) > 0
        assert len(search_engine.search_hybrid("firewall intrusion response", top_k=5)) > 0

        # 4. Physical deletion: delete from disk, assert suppressed across all modes
        doc.unlink()
        assert len(search_engine.search_text("firewall intrusion response", top_k=5)) == 0
        assert len(search_engine.search_keyword("firewall intrusion", top_k=5)) == 0
        assert len(search_engine.search_hybrid("firewall intrusion response", top_k=5)) == 0

