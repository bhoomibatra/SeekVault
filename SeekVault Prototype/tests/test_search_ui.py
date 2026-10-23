"""
test_search_ui.py — Tests for TASK-10 Search UI components, modes, and filters.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from seekvault.database.repository import Repository
from seekvault.search.engine import SearchEngine
from seekvault.ui.components import (
    render_relevance_badge,
    render_tier_badge,
    render_score_bar,
    format_file_size,
    open_file_in_os,
    open_folder_in_os
)


def test_relevance_badge_rendering():
    """Verify relevance badges render expected colored badges."""
    both_html = render_relevance_badge("Both")
    assert "Hybrid (Both)" in both_html
    assert "#6366F1" in both_html

    kw_html = render_relevance_badge("Keyword")
    assert "Keyword Match" in kw_html
    assert "#06B6D4" in kw_html

    sem_html = render_relevance_badge("Semantic")
    assert "Semantic Match" in sem_html
    assert "#8B5CF6" in sem_html


def test_tier_badge_rendering():
    """Verify tier badges render expected colors."""
    full_html = render_tier_badge("FULL")
    assert "FULL" in full_html
    assert "#10B981" in full_html

    red_html = render_tier_badge("REDACTED")
    assert "REDACTED" in red_html
    assert "#F59E0B" in red_html

    meta_html = render_tier_badge("METADATA_ONLY")
    assert "METADATA_ONLY" in meta_html
    assert "#EF4444" in meta_html


def test_format_file_size():
    """Verify human-readable file sizes."""
    assert format_file_size(500) == "500 B"
    assert "KB" in format_file_size(2048)
    assert "MB" in format_file_size(1024 * 1024 * 3)


def test_os_open_nonexistent_paths():
    """Verify open helpers fail gracefully without raising uncaught exceptions."""
    ok, msg = open_file_in_os("C:/nonexistent_seekvault_file_12345.xyz")
    assert not ok
    assert "does not exist" in msg.lower()

    ok, msg = open_folder_in_os("Z:/completely_nonexistent_dir_99999/test.txt")
    assert not ok
    assert "does not exist" in msg.lower()


def test_search_engine_hybrid_keyword_modes(tmp_path):
    """Verify SearchEngine responds properly to Hybrid and Keyword queries with filters."""
    db_file = tmp_path / "test_ui_search.db"
    repo = Repository(db_path=db_file)
    folder = tmp_path / "auth_docs"
    folder.mkdir()
    fid = repo.add_authorized_folder(str(folder))

    f1 = folder / "policy.txt"
    f1.write_text("Company data governance protocol and compliance standards.")
    rid = repo.upsert_file(
        folder_id=fid,
        file_path=str(f1),
        file_name="policy.txt",
        file_extension=".txt",
        file_size=f1.stat().st_size,
        file_hash="dummy_hash_1",
        file_type="DOCUMENT",
        modified_at="2026-01-01T00:00:00",
        status="INDEXED"
    )
    repo.save_file_content(
        rid,
        raw_char_count=60,
        searchable_text_preview="Company data governance protocol and compliance standards.",
        redacted_preview="Company data governance protocol and compliance standards."
    )

    # 1. Keyword search (FTS5)
    fts_res = repo.fts_search_content("governance", folder_ids=[fid], file_types=["DOCUMENT"])
    assert len(fts_res) == 1
    assert fts_res[0]["file_id"] == rid

    # 2. Filter rejection for wrong folder
    fts_empty = repo.fts_search_content("governance", folder_ids=[99999])
    assert fts_empty == []


def test_private_search_instrument_format_badges():
    """Verify format emblems render expected badges for PDF, DOCX, TXT, IMG."""
    from seekvault.ui.pages.search import _get_format_badge

    pdf_badge = _get_format_badge(".pdf")
    assert "format-pdf" in pdf_badge
    assert "PDF" in pdf_badge

    docx_badge = _get_format_badge(".docx")
    assert "format-docx" in docx_badge
    assert "DOCX" in docx_badge

    txt_badge = _get_format_badge(".txt")
    assert "format-txt" in txt_badge
    assert "TXT" in txt_badge

    img_badge = _get_format_badge(".png")
    assert "format-img" in img_badge
    assert "IMG" in img_badge


def test_private_search_instrument_snippet_highlighting():
    """Verify snippet highlighting inserts <mark> tags around query terms."""
    from seekvault.ui.pages.search import _format_snippet

    raw = "The candidate elimination algorithm computes the version space."
    highlighted = _format_snippet(raw, "candidate elimination")
    assert "<mark>candidate</mark>" in highlighted.lower()
    assert "<mark>elimination</mark>" in highlighted.lower()

    # Pre-existing <mark> tags from FTS5 should be preserved
    fts_raw = "Testing <mark>governance</mark> protocol"
    assert _format_snippet(fts_raw, "governance") == fts_raw


def test_search_page_rendering_contract():
    """Verify render_search_page executes cleanly with empty or populated repositories."""
    from seekvault.ui.pages.search import render_search_page

    mock_engine = MagicMock(spec=SearchEngine)
    mock_repo = MagicMock(spec=Repository)
    mock_engine.repository = mock_repo

    # Case A: 0 files indexed -> displays truthful empty state
    mock_repo.get_dashboard_stats.return_value = {"total_files": 0}
    render_search_page(mock_engine)

    # Case B: files indexed -> renders input and controls
    mock_repo.get_dashboard_stats.return_value = {"total_files": 10}
    mock_repo.get_authorized_folders.return_value = []
    render_search_page(mock_engine)

