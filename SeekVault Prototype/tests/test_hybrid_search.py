"""
test_hybrid_search.py — TASK-09 tests for hybrid FTS5+semantic search.

Tests cover:
  T1  FTS5-only: keyword match returns file
  T2  FTS5 empty query returns []
  T3  FTS5 folder-id filter excludes file from wrong folder
  T4  FTS5 file-type filter excludes IMAGE files when DOCUMENT requested
  T5  FTS5 no-result case for unrelated query
  T6  Hybrid merge: file found by both paths carries relevance_label="Both"
  T7  Hybrid keyword-only path: file not in semantic index still surfaced
  T8  Hybrid semantic-only path: model-found file surfaced when FTS misses it
  T9  Hybrid folder filter propagated to both paths
  T10 search_text_filtered applies folder filter
  T11 get_files_by_ids_filtered returns only allowed file types
  T12 result dicts contain expected keys
"""

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from seekvault.database.repository import Repository
from seekvault.search.engine import SearchEngine


@pytest.fixture()
def populated_repo(tmp_path):
    """
    Create two authorized folders, insert two INDEXED DOCUMENT files and one
    IMAGE file. File content is stored so FTS5 can match it.
    """
    db_file = tmp_path / "test_hybrid.db"
    repo = Repository(db_path=db_file)

    folder_a = tmp_path / "folder_a"
    folder_b = tmp_path / "folder_b"
    folder_a.mkdir()
    folder_b.mkdir()

    fid_a = repo.add_authorized_folder(str(folder_a))
    fid_b = repo.add_authorized_folder(str(folder_b))

    # ── file 1: DOCUMENT in folder_a with keyword "photosynthesis"
    file1 = folder_a / "biology.txt"
    file1.write_text("Plants use photosynthesis to convert sunlight into energy.")
    rid1 = repo.upsert_file(
        folder_id=fid_a, file_path=str(file1), file_name="biology.txt",
        file_extension=".txt", file_size=file1.stat().st_size,
        file_hash=hashlib.sha256(file1.read_bytes()).hexdigest(),
        file_type="DOCUMENT", modified_at="2026-01-01T00:00:00", status="INDEXED",
    )
    repo.save_file_content(
        rid1, raw_char_count=58,
        searchable_text_preview="Plants use photosynthesis to convert sunlight into energy.",
        redacted_preview="Plants use photosynthesis to convert sunlight into energy.",
    )

    # ── file 2: DOCUMENT in folder_b with keyword "thermodynamics"
    file2 = folder_b / "physics.txt"
    file2.write_text("Thermodynamics governs heat transfer in physical systems.")
    rid2 = repo.upsert_file(
        folder_id=fid_b, file_path=str(file2), file_name="physics.txt",
        file_extension=".txt", file_size=file2.stat().st_size,
        file_hash=hashlib.sha256(file2.read_bytes()).hexdigest(),
        file_type="DOCUMENT", modified_at="2026-01-01T00:00:00", status="INDEXED",
    )
    repo.save_file_content(
        rid2, raw_char_count=56,
        searchable_text_preview="Thermodynamics governs heat transfer in physical systems.",
        redacted_preview="Thermodynamics governs heat transfer in physical systems.",
    )

    # ── file 3: IMAGE in folder_a
    file3 = folder_a / "diagram.png"
    file3.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    rid3 = repo.upsert_file(
        folder_id=fid_a, file_path=str(file3), file_name="diagram.png",
        file_extension=".png", file_size=file3.stat().st_size,
        file_hash=hashlib.sha256(file3.read_bytes()).hexdigest(),
        file_type="IMAGE", modified_at="2026-01-01T00:00:00", status="INDEXED",
    )

    return repo, {
        "fid_a": fid_a, "fid_b": fid_b,
        "rid1": rid1, "rid2": rid2, "rid3": rid3,
    }


@pytest.fixture(autouse=True)
def mock_embedder():
    """Prevent loading real heavy ML weights during hybrid search unit tests."""
    with patch("seekvault.embeddings.manager.EmbeddingManager.get_text_embedder") as mock_get:
        embedder = MagicMock()
        embedder.embed_text.return_value = np.zeros(384, dtype=np.float32)
        mock_get.return_value = embedder
        yield embedder


def _make_engine(repo):
    """Build a SearchEngine with a real Repository and mock indices."""
    engine = SearchEngine.__new__(SearchEngine)
    engine.repository = repo
    engine.text_index = MagicMock()
    engine.text_index.search.return_value = []
    engine.image_index = MagicMock()
    engine.image_index.search.return_value = []
    return engine


# ─────────────────────────────────────────────────────────────────────────────
# T1  FTS5-only: keyword match returns the correct file
# ─────────────────────────────────────────────────────────────────────────────

def test_fts_keyword_match(populated_repo):
    repo, ids = populated_repo
    results = repo.fts_search_content("photosynthesis", top_k=5)
    assert len(results) >= 1
    matched_ids = [r["file_id"] for r in results]
    assert ids["rid1"] in matched_ids


# ─────────────────────────────────────────────────────────────────────────────
# T2  FTS5 empty query returns empty list
# ─────────────────────────────────────────────────────────────────────────────

def test_fts_empty_query(populated_repo):
    repo, _ = populated_repo
    assert repo.fts_search_content("") == []
    assert repo.fts_search_content("   ") == []


# ─────────────────────────────────────────────────────────────────────────────
# T3  FTS5 folder-id filter excludes file from wrong folder
# ─────────────────────────────────────────────────────────────────────────────

def test_fts_folder_filter(populated_repo):
    repo, ids = populated_repo
    results = repo.fts_search_content("photosynthesis", folder_ids=[ids["fid_b"]])
    matched_ids = [r["file_id"] for r in results]
    assert ids["rid1"] not in matched_ids


# ─────────────────────────────────────────────────────────────────────────────
# T4  FTS5 file-type filter excludes IMAGE files
# ─────────────────────────────────────────────────────────────────────────────

def test_fts_file_type_filter(populated_repo):
    repo, ids = populated_repo
    results = repo.fts_search_content("photosynthesis", file_types=["DOCUMENT"])
    matched_ids = [r["file_id"] for r in results]
    assert ids["rid3"] not in matched_ids


# ─────────────────────────────────────────────────────────────────────────────
# T5  FTS5 returns empty list for unrelated query
# ─────────────────────────────────────────────────────────────────────────────

def test_fts_no_results(populated_repo):
    repo, _ = populated_repo
    results = repo.fts_search_content("xyzzy_nonexistent_term_42")
    assert results == []


# ─────────────────────────────────────────────────────────────────────────────
# T6  Hybrid: file found by both paths → relevance_label="Both"
# ─────────────────────────────────────────────────────────────────────────────

def test_hybrid_label_both(populated_repo):
    repo, ids = populated_repo
    engine = _make_engine(repo)

    # Semantic index returns file 1 (file_id, score)
    engine.text_index.search.return_value = [(ids["rid1"], 0.85)]

    results = engine.search_hybrid("photosynthesis", top_k=10)
    found = next((r for r in results if r["file_id"] == ids["rid1"]), None)
    assert found is not None
    assert found["relevance_label"] == "Both"


# ─────────────────────────────────────────────────────────────────────────────
# T7  Hybrid keyword-only: file surfaced even without semantic hit
# ─────────────────────────────────────────────────────────────────────────────

def test_hybrid_keyword_only(populated_repo):
    repo, ids = populated_repo
    engine = _make_engine(repo)
    engine.text_index.search.return_value = []  # No semantic results

    results = engine.search_hybrid("photosynthesis", top_k=10)
    matched_ids = [r["file_id"] for r in results]
    assert ids["rid1"] in matched_ids
    found = next(r for r in results if r["file_id"] == ids["rid1"])
    assert found["relevance_label"] == "Keyword"


# ─────────────────────────────────────────────────────────────────────────────
# T8  Hybrid semantic-only: file surfaced when FTS misses it
# ─────────────────────────────────────────────────────────────────────────────

def test_hybrid_semantic_only(populated_repo):
    repo, ids = populated_repo
    engine = _make_engine(repo)

    # Semantic returns file 2; FTS has "photosynthesis" in file 1 only
    engine.text_index.search.return_value = [(ids["rid2"], 0.80)]

    results = engine.search_hybrid("photosynthesis", top_k=10)
    labels = {r["file_id"]: r["relevance_label"] for r in results}
    # rid1 → Keyword, rid2 → Semantic
    assert labels.get(ids["rid2"]) == "Semantic"


# ─────────────────────────────────────────────────────────────────────────────
# T9  Hybrid folder filter propagated: file from wrong folder excluded
# ─────────────────────────────────────────────────────────────────────────────

def test_hybrid_folder_filter(populated_repo):
    repo, ids = populated_repo
    engine = _make_engine(repo)

    results = engine.search_hybrid(
        "photosynthesis", top_k=10, folder_ids=[ids["fid_b"]]
    )
    matched_ids = [r["file_id"] for r in results]
    assert ids["rid1"] not in matched_ids


# ─────────────────────────────────────────────────────────────────────────────
# T10  search_text_filtered applies folder filter via semantic path
# ─────────────────────────────────────────────────────────────────────────────

def test_search_text_filtered_folder(populated_repo):
    repo, ids = populated_repo
    engine = _make_engine(repo)

    engine.text_index.search.return_value = [(ids["rid1"], 0.9)]

    results = engine.search_text_filtered(
        "photosynthesis", folder_ids=[ids["fid_b"]]
    )
    matched_ids = [r["file_id"] for r in results]
    assert ids["rid1"] not in matched_ids


# ─────────────────────────────────────────────────────────────────────────────
# T11  get_files_by_ids_filtered respects file_type filter
# ─────────────────────────────────────────────────────────────────────────────

def test_get_files_by_ids_filtered_type(populated_repo):
    repo, ids = populated_repo
    all_ids = [ids["rid1"], ids["rid2"], ids["rid3"]]

    doc_only = repo.get_files_by_ids_filtered(all_ids, file_types=["DOCUMENT"])
    assert ids["rid3"] not in doc_only
    assert ids["rid1"] in doc_only
    assert ids["rid2"] in doc_only


# ─────────────────────────────────────────────────────────────────────────────
# T12  Result dicts contain required keys
# ─────────────────────────────────────────────────────────────────────────────

def test_result_dict_keys(populated_repo):
    repo, ids = populated_repo
    engine = _make_engine(repo)

    results = engine.search_hybrid("photosynthesis", top_k=5)

    required_keys = {
        "file_id", "file_name", "file_path", "file_extension",
        "file_size", "file_type", "modified_at", "privacy_tier",
        "similarity_score", "relevance_label", "preview",
    }
    for r in results:
        assert required_keys.issubset(r.keys()), \
            f"Missing keys: {required_keys - r.keys()} in file_id={r.get('file_id')}"
