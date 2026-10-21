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
  8. Query-time access enforcement for unauthorized folders.

Self-healing behaviour (TASK-0004):
  - Detects stale folder paths in SQLite that no longer match the current workspace.
  - Detects an empty FAISS text index (no vectors persisted on disk).
  - Regenerates all sample fixtures and re-indexes them automatically before
    running assertions — no manual intervention required.
"""

import sys
import os
from pathlib import Path

# Ensure the package root is on sys.path regardless of working directory.
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from seekvault.config import TEXT_INDEX_PATH, IMAGE_INDEX_PATH
from seekvault.database.repository import Repository
from seekvault.search.engine import SearchEngine
from seekvault.ingestion.pipeline import IngestionPipeline

# ---------------------------------------------------------------------------
# Canonical sample-folder paths (always relative to this script's location).
# ---------------------------------------------------------------------------
SAMPLE_DIRS = [
    BASE_DIR / "sample_data" / "authorized_academic",
    BASE_DIR / "sample_data" / "authorized_personal",
    BASE_DIR / "sample_data" / "authorized_images",
    BASE_DIR / "sample_data" / "authorized_versions",
]

UNAUTHORIZED_FILE = BASE_DIR / "sample_data" / "unauthorized_folder" / "Secret_Research.pdf"


def _need_resync(repo: Repository, search_engine: SearchEngine) -> bool:
    """Return True when the workspace needs reindexing.

    Triggers:
    - FAISS text index is empty or missing.
    - FAISS image index is empty or missing.
    - Any of the canonical sample folders are not authorized in SQLite.
    - Key test files are not present in the files table.
    """
    # 1. Check FAISS text index
    if search_engine.text_index.index.ntotal == 0 or not TEXT_INDEX_PATH.exists() or TEXT_INDEX_PATH.stat().st_size < 100:
        print("[HEAL] FAISS text index is empty or missing -- reindexing required.")
        return True

    # 2. Check FAISS image index
    if search_engine.image_index.index.ntotal == 0 or not IMAGE_INDEX_PATH.exists() or IMAGE_INDEX_PATH.stat().st_size < 100:
        print("[HEAL] FAISS image index is empty or missing -- reindexing required.")
        return True

    # 3. Check SQLite authorized folder coverage
    folders = repo.get_authorized_folders(active_only=True)
    stored_paths = {os.path.normcase(os.path.abspath(f["folder_path"])) for f in folders}
    for d in SAMPLE_DIRS:
        norm_d = os.path.normcase(os.path.abspath(str(d)))
        if norm_d not in stored_paths or not d.exists():
            print(f"[HEAL] Authorized folder missing from DB or disk: {d.name} -- reindexing required.")
            return True

    # 4. Check essential test files in database
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
        print(f"[HEAL] Key files missing from database ({missing}) -- reindexing required.")
        return True

    return False


def _resync(repo: Repository, search_engine: SearchEngine, pipeline: IngestionPipeline):
    """Clear stale database records and re-index all sample fixtures."""
    print("\n[HEAL] Generating sample data fixtures...")
    create_script = BASE_DIR / "sample_data" / "create_samples.py"
    import subprocess
    result = subprocess.run([sys.executable, str(create_script)], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WARN] Sample creation had warnings: {result.stderr[:200]}")

    print("[HEAL] Clearing SQLite tables for clean reindex...")
    with repo._get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM version_members")
        cursor.execute("DELETE FROM version_groups")
        cursor.execute("DELETE FROM duplicate_groups")
        cursor.execute("DELETE FROM vector_mappings")
        cursor.execute("DELETE FROM detected_entities")
        cursor.execute("DELETE FROM file_content")
        cursor.execute("DELETE FROM files")
        cursor.execute("DELETE FROM authorized_folders")

    # Reset FAISS indexes
    search_engine.text_index.reset()
    search_engine.image_index.reset()

    print("[HEAL] Re-indexing sample folders...")
    total = 0
    for folder in SAMPLE_DIRS:
        if folder.exists():
            folder_id = repo.add_authorized_folder(str(folder), is_recursive=True)
            count = pipeline.scan_folder(str(folder), is_recursive=True)
            print(f"       OK {folder.name}: {count} files indexed")
            total += count
        else:
            print(f"       WARN: Folder not found: {folder}")

    print(f"[HEAL] Reindex complete -- {total} files indexed.\n")


def main():
    repo = Repository()
    search_engine = SearchEngine(repository=repo)
    pipeline = IngestionPipeline(repository=repo, search_engine=search_engine)

    # ------------------------------------------------------------------
    # Self-healing: resync if stale paths or missing vectors are detected.
    # ------------------------------------------------------------------
    if _need_resync(repo, search_engine):
        _resync(repo, search_engine, pipeline)

    print("=" * 54)
    print("SeekVault -- End-to-End Operational Verification")
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
    # TEST 3 -- Cross-modal image search: red car near a building
    # ------------------------------------------------------------------
    print("\nTEST 3: Image Search -- 'red car near a building'")
    res3 = search_engine.search_images("red car near a building", top_k=3)
    for r in res3:
        print(f"  -> Image: {r['file_name']:<30}  Score: {r['similarity_score']:.4f}")
    assert len(res3) > 0, "IMAGE SEARCH returned 0 results (image FAISS index empty?)"
    assert res3[0]["file_name"] == "car_parked.jpg", \
        f"Expected car_parked.jpg as top result, got: {res3[0]['file_name']}"

    # ------------------------------------------------------------------
    # TEST 4 -- Cross-modal image search: Java error screenshot
    # ------------------------------------------------------------------
    print("\nTEST 4: Image Search -- 'screenshot containing Java error'")
    res4 = search_engine.search_images("screenshot containing Java error", top_k=3)
    for r in res4:
        print(f"  -> Image: {r['file_name']:<30}  Score: {r['similarity_score']:.4f}")
    assert len(res4) > 0, "IMAGE SEARCH returned 0 results"
    assert res4[0]["file_name"] == "java_error_screenshot.png", \
        f"Expected java_error_screenshot.png as top result, got: {res4[0]['file_name']}"

    # ------------------------------------------------------------------
    # TEST 5 -- Privacy tier verification
    # ------------------------------------------------------------------
    print("\nTEST 5: Privacy Tier Verification")
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
    # TEST 8 -- Query-time folder authorization enforcement
    # ------------------------------------------------------------------
    print("\nTEST 8: Query-Time Folder Authorization Enforcement")
    is_authorized = repo.is_path_authorized(str(UNAUTHORIZED_FILE))
    assert is_authorized is False, \
        f"Unauthorized file MUST NOT be authorized, but is_path_authorized returned True"
    print(f"  -> Secret_Research.pdf  authorized: {is_authorized} [PASS] (access correctly REJECTED)")

    # ------------------------------------------------------------------
    # All checks complete
    # ------------------------------------------------------------------
    print("\n" + "=" * 54)
    print("ALL 8 END-TO-END VERIFICATION CHECKS PASSED PERFECTLY!")
    print("=" * 54)


if __name__ == "__main__":
    main()
