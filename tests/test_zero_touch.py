import os
import tempfile
import pytest
from seekvault.core.database import init_db
from seekvault.monitoring.folder_guard import FolderGuard
from seekvault.ingestion.scanner import FolderScanner
from seekvault.ingestion.hasher import compute_sha256

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

def test_zero_touch_file_non_mutation(temp_db):
    """
    CRITICAL PRIVACY TEST: Verify that scanning and indexing files NEVER modifies
    file contents, modification timestamps, or binary hashes on disk.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "important_document.pdf")
        content = b"%PDF-1.4 Privacy Critical Document Content - Confidential"
        with open(test_file, "wb") as f:
            f.write(content)
            
        initial_hash = compute_sha256(test_file)
        initial_stat = os.stat(test_file)
        
        # Authorize and scan
        FolderGuard.authorize_folder(tmpdir, db_path=temp_db)
        FolderScanner.scan_all_authorized_folders(custom_db_path=temp_db)
        
        post_hash = compute_sha256(test_file)
        post_stat = os.stat(test_file)
        
        # Assert absolute non-mutation
        assert initial_hash == post_hash, "FILE MUTATION DETECTED! SHA-256 hash changed!"
        assert initial_stat.st_mtime == post_stat.st_mtime, "FILE TIMESTAMP MUTATION DETECTED!"
        assert initial_stat.st_size == post_stat.st_size, "FILE SIZE MUTATION DETECTED!"
