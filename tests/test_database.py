import os
import tempfile
import pytest
from seekvault.core.database import (
    init_db,
    add_authorized_folder,
    remove_authorized_folder,
    get_authorized_folders,
    upsert_file_metadata,
    get_indexed_files,
    get_dashboard_stats
)

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def temp_folder():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

def test_db_init(temp_db):
    assert os.path.exists(temp_db)
    stats = get_dashboard_stats(temp_db)
    assert stats["total_folders"] == 0
    assert stats["total_files"] == 0

def test_authorized_folder_crud(temp_db, temp_folder):
    result = add_authorized_folder(temp_folder, is_recursive=True, custom_db_path=temp_db)
    assert result["folder_path"] == os.path.abspath(os.path.realpath(temp_folder))
    
    folders = get_authorized_folders(active_only=True, custom_db_path=temp_db)
    assert len(folders) == 1
    assert folders[0]["folder_path"] == os.path.abspath(os.path.realpath(temp_folder))
    
    success = remove_authorized_folder(folders[0]["id"], custom_db_path=temp_db)
    assert success is True
    
    active_folders = get_authorized_folders(active_only=True, custom_db_path=temp_db)
    assert len(active_folders) == 0

def test_file_metadata_upsert(temp_db):
    dummy_path = os.path.abspath("C:/temp/test.pdf")
    file_record = {
        "file_path": dummy_path,
        "file_name": "test.pdf",
        "file_extension": ".pdf",
        "file_size": 2048,
        "mime_type": "application/pdf",
        "created_at": "2026-09-27T10:00:00",
        "modified_at": "2026-09-27T10:00:00",
        "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "file_type": "document",
        "privacy_tier": "FULL",
        "indexing_status": "INDEXED"
    }
    
    file_id = upsert_file_metadata(file_record, custom_db_path=temp_db)
    assert file_id > 0
    
    indexed = get_indexed_files(limit=10, custom_db_path=temp_db)
    assert len(indexed) == 1
    assert indexed[0]["file_name"] == "test.pdf"
    assert indexed[0]["sha256_hash"] == file_record["sha256_hash"]
