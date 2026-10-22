import os
import tempfile
import pytest

from seekvault.core.database import init_db, get_indexed_files, get_db_connection
from seekvault.monitoring.folder_guard import FolderGuard
from seekvault.ingestion.scanner import FolderScanner
from seekvault.search.retriever import SemanticSearchEngine
from seekvault.embeddings.faiss_manager import FAISSManager
from seekvault.ingestion.hasher import compute_sha256

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def search_engine():
    return SemanticSearchEngine()

def test_vector_indexing_and_querying(temp_db, search_engine):
    """
    Test indexing a document, vector generation, FAISS store sync, and natural language search.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = os.path.join(tmpdir, "machine_learning.txt")
        content = "Candidate Elimination Algorithm is a supervised learning concept in Artificial Intelligence."
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(content)

        FolderGuard.authorize_folder(tmpdir, db_path=temp_db)
        summary = FolderScanner.scan_all_authorized_folders(custom_db_path=temp_db)
        assert summary["successful"] == 1

        # Perform natural language semantic query
        results = search_engine.search("Candidate Elimination Artificial Intelligence", top_k=5, custom_db_path=temp_db)
        assert len(results) > 0
        top_res = results[0]
        assert top_res["file_name"] == "machine_learning.txt"
        assert top_res["similarity_score"] > 50.0  # High similarity score
        assert "Candidate Elimination" in top_res["matched_text"]

def test_incremental_unchanged_files_skipping(temp_db):
    """
    Test that scanning an unchanged file skips re-embedding (SHA-256 match).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = os.path.join(tmpdir, "notes.txt")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write("Deep learning convolutional neural networks for computer vision.")

        FolderGuard.authorize_folder(tmpdir, db_path=temp_db)
        s1 = FolderScanner.scan_all_authorized_folders(custom_db_path=temp_db)
        assert s1["successful"] == 1
        assert s1["skipped"] == 0

        # Rescan without modifying file
        s2 = FolderScanner.scan_all_authorized_folders(custom_db_path=temp_db)
        assert s2["skipped"] == 1
        assert s2["successful"] == 0

def test_changed_files_reindexing(temp_db, search_engine):
    """
    Test that modifying a file updates its SHA-256 hash, purges old FAISS vectors,
    and embeds the new content.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = os.path.join(tmpdir, "report.txt")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write("Version 1: Quantum computing hardware and qubits.")

        FolderGuard.authorize_folder(tmpdir, db_path=temp_db)
        FolderScanner.scan_all_authorized_folders(custom_db_path=temp_db)

        # Query version 1 content
        r1 = search_engine.search("quantum qubits", top_k=5, custom_db_path=temp_db)
        assert len(r1) > 0

        # Modify file content on disk
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write("Version 2: Astrophysics and black hole thermodynamics physics.")

        # Rescan modified file
        FolderScanner.scan_all_authorized_folders(custom_db_path=temp_db)

        # Query version 2 content
        r2 = search_engine.search("astrophysics black hole", top_k=5, custom_db_path=temp_db)
        assert len(r2) > 0
        assert "Astrophysics" in r2[0]["matched_text"]

def test_deleted_files_purging(temp_db, search_engine):
    """
    Test that deleting a file from disk removes its vectors and excludes it from search.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = os.path.join(tmpdir, "temp_doc.txt")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write("Temporary file content regarding robotics and autonomous drones.")

        FolderGuard.authorize_folder(tmpdir, db_path=temp_db)
        FolderScanner.scan_all_authorized_folders(custom_db_path=temp_db)

        r_before = search_engine.search("autonomous drones robotics", top_k=5, custom_db_path=temp_db)
        assert len(r_before) == 1

        # Delete file from disk
        os.remove(doc_path)

        # Run scan & purge
        FolderScanner.scan_all_authorized_folders(custom_db_path=temp_db)

        # Query after deletion
        r_after = search_engine.search("autonomous drones robotics", top_k=5, custom_db_path=temp_db)
        assert len(r_after) == 0

def test_unauthorized_files_access_verification(temp_db, search_engine):
    """
    Test that revoking folder authorization filters out files at query-time.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = os.path.join(tmpdir, "private_notes.txt")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write("Confidential business strategies and financial projections.")

        # Authorize and scan
        auth_path = FolderGuard.authorize_folder(tmpdir, db_path=temp_db)
        FolderScanner.scan_all_authorized_folders(custom_db_path=temp_db)

        r_authorized = search_engine.search("business strategies financial", top_k=5, custom_db_path=temp_db)
        assert len(r_authorized) == 1

        # Revoke folder authorization
        folders = FolderGuard.get_authorized_paths(db_path=temp_db)
        conn = get_db_connection(temp_db)
        conn.execute("UPDATE authorized_folders SET is_active = 0")
        conn.commit()
        conn.close()

        # Query after revocation -> AccessVerifier blocks unauthorized result
        r_revoked = search_engine.search("business strategies financial", top_k=5, custom_db_path=temp_db)
        assert len(r_revoked) == 0
