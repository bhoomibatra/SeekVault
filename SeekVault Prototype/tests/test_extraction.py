import pytest
from pathlib import Path
import tempfile
from PIL import Image
from seekvault.extraction.text_extractor import TextExtractor
from seekvault.extraction.image_extractor import ImageExtractor
from seekvault.extraction.ocr_extractor import OCRExtractor

def test_plain_text_extraction():
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Hello SeekVault Prototype!\nCandidate Elimination Algorithm notes.")
        tmp_path = Path(f.name)

    try:
        res = TextExtractor.extract(tmp_path)
        assert res["success"] is True
        assert "Candidate Elimination Algorithm" in res["text"]
    finally:
        tmp_path.unlink()

def test_image_metadata_extraction():
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp_path = Path(f.name)

    try:
        img = Image.new("RGB", (320, 240), color="red")
        img.save(tmp_path)
        
        meta = ImageExtractor.extract_metadata(tmp_path)
        assert meta["success"] is True
        assert meta["width"] == 320
        assert meta["height"] == 240
        assert meta["color_mode"] == "RGB"
    finally:
        tmp_path.unlink()

def test_ocr_fallback():
    # Should not raise exception even if tesseract is missing
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        tmp_path = Path(f.name)
    try:
        img = Image.new("RGB", (100, 100), color="white")
        img.save(tmp_path)
        res = OCRExtractor.extract_text(tmp_path)
        assert isinstance(res, dict)
        assert "text" in res
    finally:
        tmp_path.unlink()

def test_text_chunking_boundaries_and_overlap():
    # 1. Empty text returns empty list
    assert TextExtractor.chunk_text("") == []
    assert TextExtractor.chunk_text("   ") == []

    # 2. Text under chunk_size returns single chunk
    short_text = "This is a short sample text with seven words."
    chunks_short = TextExtractor.chunk_text(short_text, chunk_size=20, overlap=5)
    assert len(chunks_short) == 1
    assert chunks_short[0] == short_text

    # 3. Text exceeding chunk_size creates overlapping chunks
    # Create 300 numbered words: word0, word1, ..., word299
    words = [f"word{i}" for i in range(300)]
    full_text = " ".join(words)

    # chunk_size = 200, overlap = 50 -> step = 150
    # Chunk 0: words[0:200]
    # Chunk 1: words[150:300]
    chunks = TextExtractor.chunk_text(full_text, chunk_size=200, overlap=50)
    assert len(chunks) == 2

    chunk0_words = chunks[0].split()
    chunk1_words = chunks[1].split()

    assert len(chunk0_words) == 200
    assert chunk0_words[0] == "word0"
    assert chunk0_words[-1] == "word199"

    assert len(chunk1_words) == 150
    assert chunk1_words[0] == "word150"
    assert chunk1_words[-1] == "word299"

    # Verify overlap: chunk0's tail (words 150..199) equals chunk1's head (words 150..199)
    overlap_chunk0 = chunk0_words[150:]
    overlap_chunk1 = chunk1_words[:50]
    assert overlap_chunk0 == overlap_chunk1
    assert len(overlap_chunk0) == 50


def test_handler_is_temporary_file():
    from seekvault.monitoring.handler import FolderEventHandler

    # Temporary / editor lock patterns
    assert FolderEventHandler._is_temporary_file("C:/docs/~$Proposal.docx") is True
    assert FolderEventHandler._is_temporary_file("/path/to/.~lock.Doc.docx#") is True
    assert FolderEventHandler._is_temporary_file("~WRL0001.tmp") is True
    assert FolderEventHandler._is_temporary_file(".tmp_file.pdf") is True
    assert FolderEventHandler._is_temporary_file("C:/downloads/file.crdownload") is True
    assert FolderEventHandler._is_temporary_file("C:/downloads/data.part") is True
    assert FolderEventHandler._is_temporary_file("temp.tmp") is True
    assert FolderEventHandler._is_temporary_file("temp.temp") is True

    # Valid supported files
    assert FolderEventHandler._is_temporary_file("C:/docs/Proposal.docx") is False
    assert FolderEventHandler._is_temporary_file("C:/images/photo.png") is False
    assert FolderEventHandler._is_temporary_file("C:/files/notes.txt") is False
    assert FolderEventHandler._is_temporary_file("") is False


def test_handler_ignores_temporary_events():
    from unittest.mock import MagicMock
    from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileDeletedEvent, FileMovedEvent
    from seekvault.monitoring.handler import FolderEventHandler

    mock_pipeline = MagicMock()
    handler = FolderEventHandler(mock_pipeline)

    # 1. Created temporary file
    handler.on_created(FileCreatedEvent("C:/test/~$Report.docx"))
    mock_pipeline.process_file.assert_not_called()

    # 2. Modified temporary file
    handler.on_modified(FileModifiedEvent("C:/test/draft.tmp"))
    mock_pipeline.process_file.assert_not_called()

    # 3. Deleted temporary file
    handler.on_deleted(FileDeletedEvent("C:/test/~$Report.docx"))
    mock_pipeline.remove_file.assert_not_called()

    # 4. Moved temporary file to temporary file
    handler.on_moved(FileMovedEvent("C:/test/~WRL01.tmp", "C:/test/~WRL02.tmp"))
    mock_pipeline.process_file.assert_not_called()
    mock_pipeline.remove_file.assert_not_called()

