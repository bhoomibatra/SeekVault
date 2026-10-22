"""
benchmark.py — Diagnostic Evaluation Benchmark Tool for SeekVault

Computes retrieval quality metrics (Precision@1, Precision@5, Recall@5, MRR)
and query execution latency (ms) across multimodal queries.
"""

import time
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
from seekvault.search.engine import SearchEngine
from evaluation.eval_dataset import BENCHMARK_QUERIES

class BenchmarkRunner:
    def __init__(self, search_engine: SearchEngine, queries: Optional[List[Dict[str, Any]]] = None):
        self.search_engine = search_engine
        self.queries = queries or BENCHMARK_QUERIES

    def evaluate(self, top_k: int = 5, warmup: bool = True) -> Dict[str, Any]:
        """Execute benchmark queries and compute evaluation metrics."""
        if warmup:
            # Pre-load in-memory weights to measure genuine query & retrieval latency
            try:
                self.search_engine.search_all("warmup initialization query", top_k=1, min_score=0.99)
            except Exception:
                pass

        results_log = []
        p1_list = []
        p5_list = []
        r5_list = []
        rr_list = []
        latency_list = []

        for q_entry in self.queries:
            query_text = q_entry["query"]
            expected = set(q_entry["expected_files"])

            # Measure latency with high-precision counter
            start_t = time.perf_counter()
            retrieved = self.search_engine.search_all(query_text, top_k=top_k, min_score=0.10)
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0
            latency_list.append(elapsed_ms)

            retrieved_names = [r["file_name"] for r in retrieved]

            # Precision@1
            p1 = 1.0 if (retrieved_names and retrieved_names[0] in expected) else 0.0
            p1_list.append(p1)

            # Precision@K & Recall@K
            hits = [name for name in retrieved_names if name in expected]
            pk = len(hits) / float(top_k) if top_k > 0 else 0.0
            rk = len(hits) / float(len(expected)) if expected else 0.0
            p5_list.append(pk)
            r5_list.append(rk)

            # Reciprocal Rank (MRR)
            reciprocal_rank = 0.0
            hit_rank = None
            for rank_idx, name in enumerate(retrieved_names, start=1):
                if name in expected:
                    reciprocal_rank = 1.0 / rank_idx
                    hit_rank = rank_idx
                    break
            rr_list.append(reciprocal_rank)

            results_log.append({
                "id": q_entry["id"],
                "query": query_text,
                "category": q_entry.get("category", "General"),
                "expected": list(expected),
                "retrieved": retrieved_names,
                "first_hit_rank": hit_rank,
                "p@1": p1,
                "p@5": pk,
                "r@5": rk,
                "mrr": reciprocal_rank,
                "latency_ms": round(elapsed_ms, 2)
            })

        summary = {
            "total_queries": len(self.queries),
            "mean_precision_at_1": float(np.mean(p1_list)) if p1_list else 0.0,
            "mean_precision_at_5": float(np.mean(p5_list)) if p5_list else 0.0,
            "mean_recall_at_5": float(np.mean(r5_list)) if r5_list else 0.0,
            "mrr": float(np.mean(rr_list)) if rr_list else 0.0,
            "mean_latency_ms": float(np.mean(latency_list)) if latency_list else 0.0,
            "median_latency_ms": float(np.median(latency_list)) if latency_list else 0.0,
            "p95_latency_ms": float(np.percentile(latency_list, 95)) if latency_list else 0.0,
            "query_results": results_log
        }

        return summary

    def generate_markdown_report(self, summary: Dict[str, Any]) -> str:
        """Render a formatted markdown performance report."""
        lines = [
            "# SeekVault Retrieval Quality & Latency Benchmark Report",
            "",
            "## 📊 Executive Summary Metrics",
            "",
            f"- **Total Benchmark Queries**: `{summary['total_queries']}`",
            f"- **Mean Reciprocal Rank (MRR)**: `{summary['mrr']:.4f}`",
            f"- **Precision @ 1 (P@1)**: `{summary['mean_precision_at_1'] * 100:.2f}%`",
            f"- **Precision @ 5 (P@5)**: `{summary['mean_precision_at_5'] * 100:.2f}%`",
            f"- **Recall @ 5 (R@5)**: `{summary['mean_recall_at_5'] * 100:.2f}%`",
            f"- **Mean Query Latency**: `{summary['mean_latency_ms']:.2f} ms`",
            f"- **Median Latency**: `{summary['median_latency_ms']:.2f} ms`",
            f"- **95th Percentile Latency (P95)**: `{summary['p95_latency_ms']:.2f} ms`",
            "",
            "## 📋 Detailed Query Results",
            "",
            "| ID | Query | Expected Target | Top Result | Hit Rank | MRR | Latency |",
            "| :---: | :--- | :--- | :--- | :---: | :---: | :---: |"
        ]

        for q in summary["query_results"]:
            top_hit = q["retrieved"][0] if q["retrieved"] else "[None]"
            expected_str = ", ".join(q["expected"])
            rank_str = str(q["first_hit_rank"]) if q["first_hit_rank"] else "-"
            lines.append(
                f"| {q['id']} | {q['query']} | `{expected_str}` | `{top_hit}` | {rank_str} | {q['mrr']:.2f} | {q['latency_ms']:.1f}ms |"
            )

        return "\n".join(lines)


def run_benchmark(search_engine: SearchEngine) -> Dict[str, Any]:
    """Convenience helper to execute benchmark and print summary."""
    runner = BenchmarkRunner(search_engine)
    summary = runner.evaluate()
    report = runner.generate_markdown_report(summary)
    return {
        "summary": summary,
        "markdown_report": report
    }
