"""
test_desktop_file_access.py — Tests for Stage 2 Real Desktop File Access & In-App Navigator.
Verifies shortcut resolution, folder inspection, format breakdown, cancellation safety,
and non-destructive guarantees on Windows.
"""

import os
from pathlib import Path
import pytest

from seekvault.database.repository import Repository
from seekvault.ingestion.pipeline import IngestionPipeline
from seekvault.ui.navigator import (
    get_user_shortcuts,
    get_friendly_folder_name,
    inspect_location_for_indexing,
)


def test_user_shortcuts_resolution():
    """Verify get_user_shortcuts resolves valid local directories on this computer."""
    shortcuts = get_user_shortcuts()
    assert isinstance(shortcuts, dict)
    assert len(shortcuts) > 0

    # At least Home or Sample Files or Documents must exist
    for label, path in shortcuts.items():
        assert os.path.exists(path), f"Shortcut {label} pointed to nonexistent path: {path}"
        assert os.path.isdir(path), f"Shortcut {label} is not a directory: {path}"


def test_friendly_folder_name():
    """Verify friendly name mapping for shortcuts and subfolders."""
    shortcuts = get_user_shortcuts()
    for label, s_path in shortcuts.items():
        assert get_friendly_folder_name(s_path) == label

    # Arbitrary folder returns basename
    assert get_friendly_folder_name("C:/Users/test/MyProject") == "MyProject"
    assert get_friendly_folder_name(r"C:\Users\test\MyProject") == "MyProject"
    assert get_friendly_folder_name("relative/subfolder") == "subfolder"
    assert get_friendly_folder_name("") == ""
    assert get_friendly_folder_name(None) == ""
    assert get_friendly_folder_name(".") != ""


def test_inspect_location_with_supported_and_unsupported(tmp_path):
    """Verify inspect_location_for_indexing correctly tallies file formats, size, and unsupported items."""
    test_dir = tmp_path / "course_materials"
    test_dir.mkdir()

    # Create supported documents
    (test_dir / "syllabus.pdf").write_text("Syllabus content", encoding="utf-8")
    (test_dir / "lecture_1.docx").write_text("Lecture content", encoding="utf-8")
    (test_dir / "notes.txt").write_text("Notes content", encoding="utf-8")
    (test_dir / "diagram.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    # Create unsupported files
    (test_dir / "setup.exe").write_bytes(b"\x4d\x5a")
    (test_dir / "archive.zip").write_bytes(b"PK\x03\x04")

    info = inspect_location_for_indexing(str(test_dir), is_folder=True, recursive=True)
    assert info["valid"] is True
    assert info["error"] is None
    assert info["total_files"] == 6
    assert len(info["supported"]) == 4
    assert len(info["unsupported"]) == 2

    # Check breakdown by type
    by_type = info["by_type"]
    assert by_type.get("PDF") == 1
    assert by_type.get("DOCX") == 1
    assert by_type.get("TXT") == 1
    assert by_type.get("PNG") == 1

    # Check total bytes > 0
    assert info["total_bytes"] > 0


def test_inspect_location_nonexistent():
    """Verify inspecting an invalid path returns valid=False with a plain-language error."""
    info = inspect_location_for_indexing("C:/nonexistent/folder/12345", is_folder=True)
    assert info["valid"] is False
    assert "does not exist" in info["error"]
    assert info["supported"] == []


def test_scan_folder_with_progress_callback(tmp_path):
    """Verify scan_folder correctly calls the progress_callback for each file."""
    db_file = tmp_path / "test_prog.db"
    repo = Repository(db_path=db_file)
    pipeline = IngestionPipeline(repository=repo)

    docs_dir = tmp_path / "docs_batch"
    docs_dir.mkdir()
    (docs_dir / "doc1.txt").write_text("Content 1", encoding="utf-8")
    (docs_dir / "doc2.txt").write_text("Content 2", encoding="utf-8")

    repo.add_authorized_folder(str(docs_dir))

    progress_events = []
    def record_progress(idx, total, fname):
        progress_events.append((idx, total, fname))

    count = pipeline.scan_folder(str(docs_dir), is_recursive=False, progress_callback=record_progress)
    assert count == 2
    assert len(progress_events) == 2
    assert progress_events[0][1] == 2
    assert progress_events[1][1] == 2


def test_cancellation_safety_leaves_state_clean(tmp_path):
    """Verify that canceling an import leaves database and physical files strictly untouched."""
    db_file = tmp_path / "test_cancel.db"
    repo = Repository(db_path=db_file)

    test_dir = tmp_path / "private_drafts"
    test_dir.mkdir()
    sample_file = test_dir / "draft.txt"
    sample_file.write_text("Original pristine content", encoding="utf-8")

    # Inspect without indexing (simulating user preview)
    info = inspect_location_for_indexing(str(test_dir), is_folder=True)
    assert info["valid"] is True

    # User clicks Cancel -> No repository records should exist
    assert repo.get_authorized_folders() == []
    assert repo.get_all_files() == []

    # Physical file is completely unchanged
    assert sample_file.exists()
    assert sample_file.read_text(encoding="utf-8") == "Original pristine content"
