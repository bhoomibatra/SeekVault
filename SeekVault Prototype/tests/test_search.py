import pytest
import tempfile
from pathlib import Path
from seekvault.database.repository import Repository
from seekvault.database.connection import get_db_connection
from seekvault.database.schema import init_db
from seekvault.search.engine import SearchEngine
from seekvault.ingestion.pipeline import IngestionPipeline

@pytest.fixture
def test_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        db_file = root / "test_search.db"
        with get_db_connection(db_file) as conn:
            init_db(conn)

        repo = Repository(db_path=db_file)
        search_engine = SearchEngine(
            repository=repo,
            text_index_path=root / "text.faiss",
            text_meta_path=root / "text.json",
            image_index_path=root / "image.faiss",
            image_meta_path=root / "image.json"
        )
        pipeline = IngestionPipeline(repository=repo, search_engine=search_engine)

        auth_dir = root / "academic"
        auth_dir.mkdir()
        repo.add_authorized_folder(str(auth_dir))

        # Create two sample files
        f1 = auth_dir / "ml_unit3.txt"
        f1.write_text("Candidate elimination algorithm identifies version space hypotheses from training samples.")

        f2 = auth_dir / "dbms_lecture.txt"
        f2.write_text("Database normalization involves first normal form, second normal form, and BCNF relational decomposition.")

        pipeline.process_file(str(f1))
        pipeline.process_file(str(f2))

        yield repo, search_engine, pipeline, auth_dir

def test_semantic_text_search(test_env):
    repo, search_engine, pipeline, auth_dir = test_env

    # Natural language query 1
    results_ml = search_engine.search_text("notes about candidate elimination")
    assert len(results_ml) > 0
    assert results_ml[0]["file_name"] == "ml_unit3.txt"
    assert results_ml[0]["similarity_score"] > 0.40

    # Natural language query 2
    results_db = search_engine.search_text("database normalization forms")
    assert len(results_db) > 0
    assert results_db[0]["file_name"] == "dbms_lecture.txt"
    assert results_db[0]["similarity_score"] > 0.40

def test_chunked_long_document_search(test_env):
    repo, search_engine, pipeline, auth_dir = test_env

    # Create a long document (> 500 words)
    # The first 300 words are generic/filler text
    filler = " ".join(["The quick brown fox jumps over the lazy dog repeatedly in various permutations." for _ in range(25)])
    # The deep content is in chunk 2/3
    deep_content = (
        "Quantum entanglement in distributed consensus protocols enables instantaneous state verification "
        "across untrusted network nodes without classical Byzantine consensus round overhead."
    )
    long_doc = auth_dir / "quantum_consensus_report.txt"
    long_doc.write_text(f"{filler}\n\n{deep_content}\n\n{filler}")

    pipeline.process_file(str(long_doc))

    # Search for deep content placed in the middle/late chunk
    results = search_engine.search_text("quantum entanglement distributed consensus protocols", top_k=5)
    assert len(results) > 0

    # Ensure the long document matched
    matched_names = [r["file_name"] for r in results]
    assert "quantum_consensus_report.txt" in matched_names

    # Ensure deduplication: each file should only appear once in search results
    assert len(matched_names) == len(set(matched_names)), "Search results contain duplicate file entries!"

def test_automatic_vector_integrity_healing(test_env):
    repo, search_engine, pipeline, auth_dir = test_env

    # 1. Verify initial vectors exist
    f1_path = auth_dir / "ml_unit3.txt"
    f2_path = auth_dir / "dbms_lecture.txt"
    f1_rec = repo.get_file_by_path(str(f1_path))
    f2_rec = repo.get_file_by_path(str(f2_path))
    assert f1_rec is not None and f2_rec is not None

    assert search_engine.text_index.has_file(f1_rec["id"]) is True
    assert search_engine.text_index.has_file(f2_rec["id"]) is True

    # 2. Simulate FAISS index loss / corruption
    search_engine.text_index.reset()
    assert search_engine.text_index.index.ntotal == 0
    assert search_engine.text_index.has_file(f1_rec["id"]) is False
    assert search_engine.text_index.has_file(f2_rec["id"]) is False

    # Search now returns nothing
    assert len(search_engine.search_text("candidate elimination")) == 0

    # 3. Process f1 again: despite hash match, missing vector is detected & healed
    pipeline.process_file(str(f1_path))
    assert search_engine.text_index.has_file(f1_rec["id"]) is True
    assert search_engine.text_index.has_file(f2_rec["id"]) is False

    # Search for f1 now succeeds
    res1 = search_engine.search_text("candidate elimination")
    assert len(res1) > 0
    assert res1[0]["file_name"] == "ml_unit3.txt"

    # 4. Use batch reconcile_missing_vectors to heal remaining files (f2)
    healed_count = pipeline.reconcile_missing_vectors()
    assert healed_count >= 1
    assert search_engine.text_index.has_file(f2_rec["id"]) is True

    # Search for f2 now succeeds
    res2 = search_engine.search_text("database normalization")
    assert len(res2) > 0
    assert res2[0]["file_name"] == "dbms_lecture.txt"
