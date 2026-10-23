"""
verify_e2e.py — SeekVault End-to-End Operational Verification Script

This script validates all 8 core product behaviours of SeekVault:
  1. Text semantic search returns relevant documents.
  2. Text semantic search (database normalization query).
  3. Cross-modal image search (red car near a building).
  4. Cross-modal image search (Java error screenshot).
  5. Privacy tier verification (REDACTED + METADATA_ONLY).
  6. Exact duplicate detection via SHA-256 clustering.
  7. Document version history detection.
  8. Query-time access enforcement for revoked folders, deleted files, and unauthorized paths across all search modes.

Data Isolation (TASK FIX):
  Runs against a temporary SEEKVAULT_DATA_DIR to guarantee that the user's real
  data_storage/ index is never wiped or corrupted.
"""

import sys
import os
import shutil
import tempfile
from pathlib import Path

# Ensure package root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ---------------------------------------------------------------------------
# Isolate to clean temporary data directory BEFORE importing seekvault.config
# ---------------------------------------------------------------------------
E2E_DATA_DIR = BASE_DIR / "scratch_e2e_test_data"
if E2E_DATA_DIR.exists():
    shutil.rmtree(E2E_DATA_DIR, ignore_errors=True)
E2E_DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ["SEEKVAULT_DATA_DIR"] = str(E2E_DATA_DIR)

from seekvault.config import TEXT_INDEX_PATH, IMAGE_INDEX_PATH
from seekvault.database.repository import Repository
from seekvault.search.engine import SearchEngine
from seekvault.ingestion.pipeline import IngestionPipeline

# ---------------------------------------------------------------------------
# Canonical sample-folder paths
# ---------------------------------------------------------------------------
SAMPLE_DIRS = [
    BASE_DIR / "sample_data" / "authorized_academic",
    BASE_DIR / "sample_data" / "authorized_personal",
    BASE_DIR / "sample_data" / "authorized_images",
    BASE_DIR / "sample_data" / "authorized_versions",
]

UNAUTHORIZED_FILE = BASE_DIR / "sample_data" / "unauthorized_folder" / "Secret_Research.pdf"


def _need_resync(repo: Repository, search_engine: SearchEngine) -> bool:
    """Return True when the workspace needs reindexing."""
    if search_engine.text_index.index.ntotal == 0 or not TEXT_INDEX_PATH.exists() or TEXT_INDEX_PATH.stat().st_size < 100:
        print("[HEAL] FAISS text index is empty or missing -- indexing required.")
        return True

    if search_engine.image_index.index.ntotal == 0 or not IMAGE_INDEX_PATH.exists() or IMAGE_INDEX_PATH.stat().st_size < 100:
        print("[HEAL] FAISS image index is empty or missing -- indexing required.")
        return True

    folders = repo.get_authorized_folders(active_only=True)
    stored_paths = {os.path.normcase(os.path.abspath(f["folder_path"])) for f in folders}
    for d in SAMPLE_DIRS:
        norm_d = os.path.normcase(os.path.abspath(str(d)))
        if norm_d not in stored_paths or not d.exists():
            print(f"[HEAL] Authorized folder missing from DB or disk: {d.name} -- indexing required.")
            return True

    with repo._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_name FROM files")
        indexed_names = {row["file_name"] for row in cursor.fetchall()}

    required_files = {
        "ML_Unit3_Notes.pdf",
        "DBMS_Lecture_4.docx",
        "car_parked.jpg",
        "java_error_screenshot.png",
        "Student_Admission_Form.pdf",
        "Master_Password_Vault.txt"
    }
    missing = required_files - indexed_names
    if missing:
        print(f"[HEAL] Key files missing from database ({missing}) -- indexing required.")
        return True

    return False


def _resync(repo: Repository, search_engine: SearchEngine, pipeline: IngestionPipeline):
    """Index all sample fixtures into the isolated temporary database."""
    print("\n[HEAL] Verifying sample data fixtures...")
    create_script = BASE_DIR / "sample_data" / "create_samples.py"
    import subprocess
    result = subprocess.run([sys.executable, str(create_script)], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WARN] Sample creation had warnings: {result.stderr[:200]}")

    print("[HEAL] Indexing sample folders into isolated test database...")
    total = 0
    for folder in SAMPLE_DIRS:
        if folder.exists():
            repo.add_authorized_folder(str(folder), is_recursive=True)
            count = pipeline.scan_folder(str(folder), is_recursive=True)
            print(f"       OK {folder.name}: {count} files indexed")
            total += count
        else:
            print(f"       WARN: Folder not found: {folder}")

    print(f"[HEAL] Isolated index complete -- {total} files indexed.\n")


def run_e2e_verification():
    repo = Repository()
    search_engine = SearchEngine(repository=repo)
    pipeline = IngestionPipeline(repository=repo, search_engine=search_engine)

    # Populate isolated temporary test environment
    if _need_resync(repo, search_engine):
        _resync(repo, search_engine, pipeline)

    print("=" * 54)
    print("SeekVault -- End-to-End Operational Verification")
    print(f"Isolated Data Dir: {E2E_DATA_DIR}")
    print("=" * 54)

    # ------------------------------------------------------------------
    # TEST 1 -- Text semantic search: candidate elimination
    # ------------------------------------------------------------------
    print("\nTEST 1: Text Search -- 'notes about candidate elimination'")
    res1 = search_engine.search_text("notes about candidate elimination", top_k=3)
    for r in res1:
        print(f"  -> File: {r['file_name']:<30}  Score: {r['similarity_score']:.4f}  Tier: {r['privacy_tier']}")
    assert len(res1) > 0, "TEXT SEARCH returned 0 results (FAISS index empty?)"
    assert "ML_Unit3_Notes.pdf" in [r["file_name"] for r in res1], \
        f"Expected ML_Unit3_Notes.pdf in results, got: {[r['file_name'] for r in res1]}"

    # ------------------------------------------------------------------
    # TEST 2 -- Text semantic search: database normalization
    # ------------------------------------------------------------------
    print("\nTEST 2: Text Search -- 'database normalization'")
    res2 = search_engine.search_text("database normalization", top_k=3)
    for r in res2:
        print(f"  -> File: {r['file_name']:<30}  Score: {r['similarity_score']:.4f}  Tier: {r['privacy_tier']}")
    assert len(res2) > 0, "TEXT SEARCH returned 0 results"
    assert "DBMS_Lecture_4.docx" in [r["file_name"] for r in res2], \
        f"Expected DBMS_Lecture_4.docx in results, got: {[r['file_name'] for r in res2]}"

    # ------------------------------------------------------------------
    # TEST 3 -- Cross-modal image search: red car parked
    # ------------------------------------------------------------------
    print("\nTEST 3: Cross-Modal Image Search -- 'red car parked near a building'")
    res3 = search_engine.search_images("red car parked near a building", top_k=3)
    for r in res3:
        print(f"  -> File: {r['file_name']:<30}  Score: {r['similarity_score']:.4f}")
    assert len(res3) > 0, "IMAGE SEARCH returned 0 results (FAISS index empty?)"
    assert "car_parked.jpg" in [r["file_name"] for r in res3], \
        f"Expected car_parked.jpg in results, got: {[r['file_name'] for r in res3]}"

    # ------------------------------------------------------------------
    # TEST 4 -- Cross-modal image search: Java error screenshot
    # ------------------------------------------------------------------
    print("\nTEST 4: Cross-Modal Image Search -- 'screenshot of java code error'")
    res4 = search_engine.search_images("screenshot of java code error", top_k=3)
    for r in res4:
        print(f"  -> File: {r['file_name']:<30}  Score: {r['similarity_score']:.4f}")
    assert len(res4) > 0, "IMAGE SEARCH returned 0 results"
    assert "java_error_screenshot.png" in [r["file_name"] for r in res4], \
        f"Expected java_error_screenshot.png in results, got: {[r['file_name'] for r in res4]}"

    # ------------------------------------------------------------------
    # TEST 5 -- Privacy tier verification
    # ------------------------------------------------------------------
    print("\nTEST 5: Privacy Tier Verification (REDACTED & METADATA_ONLY)")
    student_path = str(BASE_DIR / "sample_data" / "authorized_personal" / "Student_Admission_Form.pdf")
    student_file = repo.get_file_by_path(student_path)
    assert student_file is not None, f"Student_Admission_Form.pdf not found in DB at {student_path}"
    assert student_file["privacy_tier"] == "REDACTED", \
        f"Expected REDACTED, got: {student_file['privacy_tier']}"
    print(f"  -> Student_Admission_Form.pdf  tier: {student_file['privacy_tier']} [PASS] (REDACTED verified)")

    pass_path = str(BASE_DIR / "sample_data" / "authorized_personal" / "Master_Password_Vault.txt")
    pass_file = repo.get_file_by_path(pass_path)
    assert pass_file is not None, f"Master_Password_Vault.txt not found in DB at {pass_path}"
    assert pass_file["privacy_tier"] == "METADATA_ONLY", \
        f"Expected METADATA_ONLY, got: {pass_file['privacy_tier']}"
    print(f"  -> Master_Password_Vault.txt   tier: {pass_file['privacy_tier']} [PASS] (METADATA_ONLY verified)")

    # ------------------------------------------------------------------
    # TEST 6 -- Exact duplicate detection (SHA-256 hash clustering)
    # ------------------------------------------------------------------
    print("\nTEST 6: Exact Duplicate Detection")
    duplicates = repo.get_duplicate_groups()
    print(f"  -> Found {len(duplicates)} duplicate cluster(s):")
    for d in duplicates:
        print(f"     Hash {d['file_hash'][:14]}...  files: {d['file_names']}")
    assert len(duplicates) >= 1, \
        "Expected at least 1 duplicate cluster (ML_Unit3_Notes_Copy.pdf)"

    # ------------------------------------------------------------------
    # TEST 7 -- Document version history detection
    # ------------------------------------------------------------------
    print("\nTEST 7: Document Version History Detection")
    version_groups = repo.get_all_version_groups()
    print(f"  -> Found {len(version_groups)} version chain(s):")
    for vg in version_groups:
        print(f"     {vg['group_name']}: {[m['file_name'] for m in vg['members']]}")
    assert len(version_groups) >= 1, \
        "Expected at least 1 version chain (Project_Report_Draft_v1/v2)"

    # ------------------------------------------------------------------
    # TEST 8 -- Comprehensive query-time authorization enforcement
    # ------------------------------------------------------------------
    print("\nTEST 8: Query-Time Authorization & Access Verification Enforcement")

    # 8a: Static path authorization check
    is_authorized = repo.is_path_authorized(str(UNAUTHORIZED_FILE))
    assert is_authorized is False, "Unauthorized file path MUST NOT be authorized!"
    print(f"  -> Unauthorized file check: authorized={is_authorized} [PASS]")

    # 8b: Dynamic query-time enforcement on indexed files across all search modes
    with tempfile.TemporaryDirectory() as temp_vault_dir:
        vault_path = Path(temp_vault_dir)
        folder_id = repo.add_authorized_folder(str(vault_path), is_recursive=True)

        doc_file = vault_path / "Controlled_Access_Protocol.txt"
        doc_file.write_text("Controlled access protocol and zero-trust verification document.", encoding="utf-8")
        pipeline.process_file(str(doc_file))

        # Confirm initial discovery across semantic, keyword, and hybrid modes
        res_sem = search_engine.search_text("zero-trust verification document", top_k=5)
        res_kw = search_engine.search_keyword("Controlled access", top_k=5)
        res_hyb = search_engine.search_hybrid("zero-trust verification document", top_k=5)

        assert any(r["file_name"] == "Controlled_Access_Protocol.txt" for r in res_sem), "File not found in semantic search!"
        assert any(r["file_name"] == "Controlled_Access_Protocol.txt" for r in res_kw), "File not found in keyword search!"
        assert any(r["file_name"] == "Controlled_Access_Protocol.txt" for r in res_hyb), "File not found in hybrid search!"
        print("  -> Initial discovery across Semantic, Keyword, and Hybrid search: [PASS]")

        # Deactivate folder: all search modes MUST immediately suppress results
        repo.set_folder_active_state(folder_id, False)

        sup_sem = search_engine.search_text("zero-trust verification document", top_k=5)
        sup_kw = search_engine.search_keyword("Controlled access", top_k=5)
        sup_hyb = search_engine.search_hybrid("zero-trust verification document", top_k=5)

        assert not any(r["file_name"] == "Controlled_Access_Protocol.txt" for r in sup_sem), "Revoked folder leaked in semantic search!"
        assert not any(r["file_name"] == "Controlled_Access_Protocol.txt" for r in sup_kw), "Revoked folder leaked in keyword search!"
        assert not any(r["file_name"] == "Controlled_Access_Protocol.txt" for r in sup_hyb), "Revoked folder leaked in hybrid search!"
        print("  -> Query-time deauthorization suppression across all search modes: [PASS]")

        # Reactivate folder: search must return it again
        repo.set_folder_active_state(folder_id, True)
        reac_sem = search_engine.search_text("zero-trust verification document", top_k=5)
        assert any(r["file_name"] == "Controlled_Access_Protocol.txt" for r in reac_sem), "Reactivated folder not returned!"
        print("  -> Folder reactivation restoration: [PASS]")

        # Physical deletion: delete file from disk without removing DB entry
        doc_file.unlink()
        del_sem = search_engine.search_text("zero-trust verification document", top_k=5)
        del_kw = search_engine.search_keyword("Controlled access", top_k=5)
        del_hyb = search_engine.search_hybrid("zero-trust verification document", top_k=5)

        assert not any(r["file_name"] == "Controlled_Access_Protocol.txt" for r in del_sem), "Deleted file returned in semantic search!"
        assert not any(r["file_name"] == "Controlled_Access_Protocol.txt" for r in del_kw), "Deleted file returned in keyword search!"
        assert not any(r["file_name"] == "Controlled_Access_Protocol.txt" for r in del_hyb), "Deleted file returned in hybrid search!"
        print("  -> Physical disk deletion zero-trust suppression: [PASS]")

    # ------------------------------------------------------------------
    # All checks complete
    # ------------------------------------------------------------------
    print("\n" + "=" * 54)
    print("ALL 8 END-TO-END VERIFICATION CHECKS PASSED PERFECTLY!")
    print("=" * 54)


def main():
    try:
        run_e2e_verification()
    finally:
        # Clean up temporary test data directory
        if E2E_DATA_DIR.exists():
            shutil.rmtree(E2E_DATA_DIR, ignore_errors=True)
            print(f"[CLEANUP] Removed temporary verification data: {E2E_DATA_DIR}")


if __name__ == "__main__":
    main()
