import os
import sys
import shutil
from pathlib import Path

# Set up clean temporary data directory
test_data_dir = Path(__file__).resolve().parent / "scratch_clean_test_data"
if test_data_dir.exists():
    shutil.rmtree(test_data_dir, ignore_errors=True)
test_data_dir.mkdir(parents=True, exist_ok=True)

os.environ["SEEKVAULT_DATA_DIR"] = str(test_data_dir)

# Ensure SeekVault package is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import and initialize
from seekvault import config
print(f"[1/4] Config DATA_DIR: {config.DATA_DIR}")
assert config.DATA_DIR == test_data_dir, "Custom DATA_DIR not respected!"

from seekvault.database.repository import Repository
repo = Repository(db_path=config.DB_PATH)
print(f"[2/4] Database initialized cleanly at: {config.DB_PATH}")

# Verify SQLite tables exist
with repo._get_conn() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = [row[0] for row in cursor.fetchall()]

print(f"[3/4] Created tables ({len(table_names)}): {table_names}")
assert "authorized_folders" in table_names, "Missing authorized_folders table"
assert "files" in table_names, "Missing files table"
assert "file_content" in table_names, "Missing file_content table"
assert "detected_entities" in table_names, "Missing detected_entities table"
assert "vector_mappings" in table_names, "Missing vector_mappings table"

from seekvault.search.engine import SearchEngine
engine = SearchEngine(repository=repo)
print("[4/4] SearchEngine and FAISS index initialized cleanly.")

# Cleanup test directory safely
shutil.rmtree(test_data_dir, ignore_errors=True)
print("SUCCESS: Clean launch verified without a pre-seeded database!")
