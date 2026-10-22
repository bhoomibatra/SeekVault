import os
import tempfile
import pytest
from seekvault.core.database import init_db, get_indexed_files
from seekvault.monitoring.folder_guard import FolderGuard
from seekvault.ingestion.scanner import FolderScanner

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def sample_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample files
        doc_pdf = os.path.join(tmpdir, "doc.pdf")
        doc_docx = os.path.join(tmpdir, "notes.docx")
        doc_txt = os.path.join(tmpdir, "readme.txt")
        img_png = os.path.join(tmpdir, "photo.png")
        img_jpg = os.path.join(tmpdir, "scan.jpg")
        unsupported = os.path.join(tmpdir, "binary.exe")
        
        for p in [doc_pdf, doc_docx, doc_txt, img_png, img_jpg, unsupported]:
            with open(p, "wb") as f:
                f.write(b"SeekVault Sample Test Content Data " * 10)
                
        yield tmpdir

def test_scanner_detection_and_metadata(temp_db, sample_files):
    FolderGuard.authorize_folder(sample_files, db_path=temp_db)
    
    summary = FolderScanner.scan_all_authorized_folders(custom_db_path=temp_db)
    assert summary["total_scanned"] == 5  # 5 supported files (.pdf, .docx, .txt, .png, .jpg)
    assert summary["successful"] == 5
    
    indexed = get_indexed_files(limit=100, custom_db_path=temp_db)
    assert len(indexed) == 5
    
    extensions = {f["file_extension"] for f in indexed}
    assert extensions == {".pdf", ".docx", ".txt", ".png", ".jpg"}
    
    for f in indexed:
        assert len(f["sha256_hash"]) == 64
        assert f["file_type"] in ["document", "image"]
