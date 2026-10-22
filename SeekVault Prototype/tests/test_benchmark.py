import pytest
import tempfile
from pathlib import Path
from seekvault.database.repository import Repository
from seekvault.database.connection import get_db_connection
from seekvault.database.schema import init_db
from seekvault.search.engine import SearchEngine
from seekvault.ingestion.pipeline import IngestionPipeline
from evaluation.eval_dataset import BENCHMARK_QUERIES
from evaluation.benchmark import BenchmarkRunner, run_benchmark

def test_benchmark_dataset_integrity():
    """Verify that the evaluation dataset contains valid, structured query definitions."""
    assert len(BENCHMARK_QUERIES) >= 15, "Benchmark dataset should define at least 15 queries."
    for q in BENCHMARK_QUERIES:
        assert "id" in q
        assert "query" in q and len(q["query"].strip()) > 0
        assert "expected_files" in q and len(q["expected_files"]) > 0
        assert "modality" in q and q["modality"] in ("DOCUMENT", "IMAGE")

@pytest.fixture
def eval_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        db_file = root / "benchmark_test.db"
        with get_db_connection(db_file) as conn:
            init_db(conn)

        repo = Repository(db_path=db_file)
        search_engine = SearchEngine(
            repository=repo,
            text_index_path=root / "text_bench.faiss",
            text_meta_path=root / "text_bench.json",
            image_index_path=root / "image_bench.faiss",
            image_meta_path=root / "image_bench.json",
        )
        pipeline = IngestionPipeline(repository=repo, search_engine=search_engine)

        auth_dir = root / "authorized"
        auth_dir.mkdir()
        repo.add_authorized_folder(str(auth_dir))

        # Seed target test documents
        doc1 = auth_dir / "ML_Unit3_Notes.pdf.txt"
        doc1.write_text(
            "Candidate elimination algorithm identifies version space hypotheses from training samples.",
            encoding="utf-8"
        )
        # Give it the expected name in SQLite
        pipeline.process_file(str(doc1))

        doc2 = auth_dir / "DBMS_Lecture_4.docx.txt"
        doc2.write_text(
            "Database normalization involves first normal form, second normal form, and BCNF relational decomposition.",
            encoding="utf-8"
        )
        pipeline.process_file(str(doc2))

        doc3 = auth_dir / "Java_Concurrency_Notes.txt"
        doc3.write_text(
            "Java concurrency threads synchronization locks and executor thread pool.",
            encoding="utf-8"
        )
        pipeline.process_file(str(doc3))

        yield {
            "repo": repo,
            "search_engine": search_engine,
            "pipeline": pipeline,
            "auth_dir": auth_dir,
            "file_names": [doc1.name, doc2.name, doc3.name]
        }

def test_benchmark_runner_metrics(eval_env):
    """Test metric computation and latency benchmarks."""
    search_engine = eval_env["search_engine"]
    f_names = eval_env["file_names"]

    # Define targeted test queries for the seeded files
    targeted_queries = [
        {
            "id": 1,
            "query": "candidate elimination algorithm version space",
            "expected_files": [f_names[0]],
            "category": "Machine Learning"
        },
        {
            "id": 2,
            "query": "database normalization BCNF relational decomposition",
            "expected_files": [f_names[1]],
            "category": "Database Systems"
        },
        {
            "id": 3,
            "query": "java concurrency threads synchronization locks",
            "expected_files": [f_names[2]],
            "category": "Computer Science"
        }
    ]

    runner = BenchmarkRunner(search_engine, queries=targeted_queries)
    summary = runner.evaluate(top_k=5, warmup=True)

    assert summary["total_queries"] == 3
    assert summary["mrr"] >= 0.60, f"Expected MRR >= 0.60, got {summary['mrr']}"
    assert summary["mean_precision_at_1"] >= 0.60
    assert summary["mean_latency_ms"] < 350.0  # Warm retrieval < 350ms on CPU

    # Test report generation
    markdown_report = runner.generate_markdown_report(summary)
    assert "# SeekVault Retrieval Quality & Latency Benchmark Report" in markdown_report
    assert "Mean Reciprocal Rank (MRR)" in markdown_report
    assert "Precision @ 1 (P@1)" in markdown_report
