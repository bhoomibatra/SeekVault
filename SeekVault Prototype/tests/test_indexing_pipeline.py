import os
import hashlib
import tempfile
from pathlib import Path
import pytest
from PIL import Image
import docx
import fitz  # PyMuPDF

from seekvault.database.repository import Repository
from seekvault.ingestion.pipeline import IngestionPipeline
from seekvault.search.engine import SearchEngine
from seekvault.search.faiss_index import FaissIndex
from seekvault import config


@pytest.fixture
def clean_pipeline():
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        db_path = base_dir / "test_seekvault.db"
        text_idx_path = base_dir / "text_index.faiss"
        text_meta_path = base_dir / "text_ids.json"
        img_idx_path = base_dir / "image_index.faiss"
        img_meta_path = base_dir / "image_ids.json"

        repo = Repository(db_path=db_path)

        search_engine = SearchEngine(
            repository=repo,
            text_index_path=text_idx_path,
            text_meta_path=text_meta_path,
            image_index_path=img_idx_path,
            image_meta_path=img_meta_path
        )

        pipeline = IngestionPipeline(repository=repo, search_engine=search_engine)
        yield {
            "pipeline": pipeline,
            "repo": repo,
            "engine": search_engine,
            "base_dir": base_dir
        }


def test_pipeline_unauthorized_folder_rejection(clean_pipeline):
    """TASK-06: Scanning or processing files in an unauthorized folder must be rejected."""
    pipeline = clean_pipeline["pipeline"]
    repo = clean_pipeline["repo"]
    base_dir = clean_pipeline["base_dir"]

    unauth_dir = base_dir / "unauthorized_documents"
    unauth_dir.mkdir()
    doc = unauth_dir / "secret.txt"
    doc.write_text("Unauthorized secret content", encoding="utf-8")

    # 1. scan_folder on unauthorized path returns 0
    indexed_count = pipeline.scan_folder(str(unauth_dir))
    assert indexed_count == 0

    # 2. process_file on unauthorized file returns None
    result = pipeline.process_file(str(doc))
    assert result is None
    assert repo.get_file_by_path(str(doc)) is None


def test_pipeline_immutability_multiformat(clean_pipeline):
    """TASK-06: Ingesting a variety of supported formats (TXT, MD, PDF, DOCX, PNG)
    must leave every source file 100% byte-for-byte immutable."""
    pipeline = clean_pipeline["pipeline"]
    repo = clean_pipeline["repo"]
    base_dir = clean_pipeline["base_dir"]

    auth_dir = base_dir / "user_vault"
    auth_dir.mkdir()
    repo.add_authorized_folder(str(auth_dir), is_recursive=True)

    # 1. Create plain text
    txt_file = auth_dir / "readme.txt"
    txt_file.write_text("SeekVault local desktop search notes.", encoding="utf-8")

    # 2. Create markdown
    md_file = auth_dir / "project.md"
    md_file.write_text("# Project Vanguard\nMilestones and architectural boundaries.", encoding="utf-8")

    # 3. Create PDF
    pdf_file = auth_dir / "sample.pdf"
    doc_pdf = fitz.open()
    page = doc_pdf.new_page()
    page.insert_text((50, 72), "SeekVault Evidence First Specification PDF")
    doc_pdf.save(str(pdf_file))
    doc_pdf.close()

    # 4. Create DOCX
    docx_file = auth_dir / "document.docx"
    doc_docx = docx.Document()
    doc_docx.add_heading("Meeting Minutes", 0)
    doc_docx.add_paragraph("Reviewed quarterly milestones and indexing performance.")
    doc_docx.save(str(docx_file))

    # 5. Create PNG
    png_file = auth_dir / "diagram.png"
    img = Image.new("RGB", (160, 120), color=(36, 50, 77))
    img.save(png_file)

    test_files = [txt_file, md_file, pdf_file, docx_file, png_file]

    # Record SHA-256, sizes, and timestamps before indexing
    pre_snapshots = {}
    for f in test_files:
        content = f.read_bytes()
        pre_snapshots[f] = {
            "hash": hashlib.sha256(content).hexdigest(),
            "size": len(content),
            "mtime": f.stat().st_mtime_ns
        }

    # Execute full scan and ingestion
    indexed_count = pipeline.scan_folder(str(auth_dir), is_recursive=True)
    assert indexed_count == len(test_files), f"Expected {len(test_files)} indexed files, got {indexed_count}"

    # Verify 100% byte-for-byte and hash immutability after indexing
    for f in test_files:
        post_content = f.read_bytes()
        post_hash = hashlib.sha256(post_content).hexdigest()
        post_size = len(post_content)
        post_mtime = f.stat().st_mtime_ns

        assert post_hash == pre_snapshots[f]["hash"], f"Immutability violated for {f.name}: hash changed!"
        assert post_size == pre_snapshots[f]["size"], f"Immutability violated for {f.name}: size changed!"
        assert post_mtime == pre_snapshots[f]["mtime"], f"Modification timestamp altered for {f.name}!"

        # Verify DB record is marked INDEXED
        rec = repo.get_file_by_path(str(f))
        assert rec is not None
        assert rec["status"] == "INDEXED"
        assert rec["error_detail"] is None


def test_pipeline_handles_corrupt_files_gracefully(clean_pipeline):
    """TASK-06: Corrupt PDF, DOCX, or unreadable files must not crash the pipeline,
    and must be marked as FAILED with error details recorded in SQLite."""
    pipeline = clean_pipeline["pipeline"]
    repo = clean_pipeline["repo"]
    base_dir = clean_pipeline["base_dir"]

    auth_dir = base_dir / "corrupt_test_folder"
    auth_dir.mkdir()
    repo.add_authorized_folder(str(auth_dir), is_recursive=True)

    # 1. Corrupt PDF: contains junk bytes, not valid PDF structure
    corrupt_pdf = auth_dir / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"JUNK_RANDOM_CORRUPT_BYTES_NOT_A_PDF_STREAM")

    # 2. Corrupt DOCX: not a valid zip archive
    corrupt_docx = auth_dir / "broken.docx"
    corrupt_docx.write_bytes(b"NOT_A_ZIP_CONTAINER")

    # Process files
    res_pdf = pipeline.process_file(str(corrupt_pdf))
    assert res_pdf is not None
    assert res_pdf["status"] == "FAILED"
    assert res_pdf["error_detail"] is not None
    assert len(res_pdf["error_detail"]) > 0

    res_docx = pipeline.process_file(str(corrupt_docx))
    assert res_docx is not None
    assert res_docx["status"] == "FAILED"
    assert res_docx["error_detail"] is not None

    # Verify repo.get_failed_files() returns both corrupt files
    failed_files = repo.get_failed_files()
    failed_names = [f["file_name"] for f in failed_files]
    assert "corrupt.pdf" in failed_names
    assert "broken.docx" in failed_names

    # Check that failed counts are accurate in folder file counts
    fid = repo.get_folder_for_path(str(corrupt_pdf))
    counts = repo.get_folder_file_counts()
    assert counts[fid]["failed"] == 2
    assert counts[fid]["indexed"] == 0


def test_pipeline_handles_empty_files_gracefully(clean_pipeline):
    """TASK-06: 0-byte text files must be handled gracefully without crashing,
    marked as INDEXED with 0 characters and 0 vectors."""
    pipeline = clean_pipeline["pipeline"]
    repo = clean_pipeline["repo"]
    base_dir = clean_pipeline["base_dir"]

    auth_dir = base_dir / "empty_files_folder"
    auth_dir.mkdir()
    repo.add_authorized_folder(str(auth_dir), is_recursive=True)

    empty_txt = auth_dir / "empty_notes.txt"
    empty_txt.write_text("", encoding="utf-8")
    assert empty_txt.stat().st_size == 0

    res = pipeline.process_file(str(empty_txt))
    assert res is not None
    assert res["status"] == "INDEXED"
    assert res["file_size"] == 0

    content = repo.get_file_content(res["id"])
    assert content["raw_char_count"] == 0

    # Ensure no vector was added for empty file
    assert not clean_pipeline["engine"].text_index.has_file(res["id"])


def test_chunking_retains_parent_file_mapping(clean_pipeline):
    """TASK-06: Multi-chunk long documents must store multiple vectors that
    all retain mapping to the exact parent file_id, enabling retrieval of deep content."""
    pipeline = clean_pipeline["pipeline"]
    repo = clean_pipeline["repo"]
    engine = clean_pipeline["engine"]
    base_dir = clean_pipeline["base_dir"]

    auth_dir = base_dir / "long_docs_vault"
    auth_dir.mkdir()
    repo.add_authorized_folder(str(auth_dir), is_recursive=True)

    # Create a 600-word document with distinct concepts in Chunk 1 and Chunk 2
    section1 = "Quantum telemetry protocol for deep space satellites with cryogenic cooling systems. " * 25
    section2 = "Acoustic resonance damping mechanisms in naval hydrofoil stabilizers under heavy cavitation. " * 25
    full_text = section1 + "\n\n" + section2

    long_doc = auth_dir / "engineering_compendium.txt"
    long_doc.write_text(full_text, encoding="utf-8")

    res = pipeline.process_file(str(long_doc))
    assert res is not None
    file_id = res["id"]

    # Verify multiple vectors exist in vector_mappings for this single file_id
    mappings = repo.get_vectors_for_file(file_id)
    assert len(mappings) >= 2, f"Expected at least 2 chunk vectors, got {len(mappings)}"
    for m in mappings:
        assert m["file_id"] == file_id
        assert m["modality"] == "TEXT"

    # Search for concept from section 1
    s1_results = engine.search_text("cryogenic cooling quantum telemetry", top_k=5)
    assert len(s1_results) > 0
    assert s1_results[0]["file_id"] == file_id

    # Search for concept from section 2
    s2_results = engine.search_text("naval hydrofoil acoustic resonance cavitation", top_k=5)
    assert len(s2_results) > 0
    assert s2_results[0]["file_id"] == file_id
