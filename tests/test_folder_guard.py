import os
import tempfile
import pytest
from seekvault.core.database import init_db
from seekvault.monitoring.folder_guard import FolderGuard

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

def test_authorize_and_revoke_folder(temp_db, temp_dir):
    auth_path = FolderGuard.authorize_folder(temp_dir, db_path=temp_db)
    assert os.path.isabs(auth_path)
    
    paths = FolderGuard.get_authorized_paths(db_path=temp_db)
    assert auth_path in paths
    
    dummy_file = os.path.join(temp_dir, "sub", "test.pdf")
    assert FolderGuard.is_path_authorized(dummy_file, db_path=temp_db) is True
    
    outside_file = "C:/Windows/System32/cmd.exe"
    assert FolderGuard.is_path_authorized(outside_file, db_path=temp_db) is False

def test_nonexistent_folder_error(temp_db):
    with pytest.raises(FileNotFoundError):
        FolderGuard.authorize_folder("C:/NonExistentPath_SeekVault_Test_12345", db_path=temp_db)
