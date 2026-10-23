from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from seekvault.config import (
    TEXT_INDEX_PATH, TEXT_METADATA_PATH, TEXT_EMBEDDING_DIM,
    IMAGE_INDEX_PATH, IMAGE_METADATA_PATH, IMAGE_EMBEDDING_DIM,
    SEARCH_DEFAULT_TOP_K, SEARCH_MIN_SCORE
)
from seekvault.database.repository import Repository
from seekvault.search.faiss_index import FaissIndex
from seekvault.search.verifier import AccessVerifier
import logging

logger = logging.getLogger(__name__)

# Reciprocal Rank Fusion constant (k=60 is the standard default)
_RRF_K = 60


def _rrf_score(rank: int) -> float:
    """Reciprocal Rank Fusion score for a single result at 1-indexed `rank`."""
    return 1.0 / (_RRF_K + rank)


class SearchEngine:
    def __init__(
        self,
        repository: Optional[Repository] = None,
        text_index_path: Path = TEXT_INDEX_PATH,
        text_meta_path: Path = TEXT_METADATA_PATH,
        image_index_path: Path = IMAGE_INDEX_PATH,
        image_meta_path: Path = IMAGE_METADATA_PATH
    ):
        self.repository = repository or Repository()
        self.text_index = FaissIndex(TEXT_EMBEDDING_DIM, text_index_path, text_meta_path)
        self.image_index = FaissIndex(IMAGE_EMBEDDING_DIM, image_index_path, image_meta_path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _enrich_result(
        self,
        file_rec: Dict[str, Any],
        score: float,
        excerpt: str = "",
        relevance_label: str = "Semantic"
    ) -> Dict[str, Any]:
        """Attach snippet previews and entity metadata to a result record."""
        content = self.repository.get_file_content(file_rec["id"])
        entities = self.repository.get_detected_entities_for_file(file_rec["id"])

        preview = excerpt  # prefer FTS excerpt when available
        if not preview and content:
            if file_rec.get("privacy_tier") == "REDACTED":
                preview = content.get("redacted_preview") or content.get("searchable_text_preview", "")
            elif file_rec.get("privacy_tier") == "METADATA_ONLY":
                preview = "[CONTENT HIDDEN - METADATA ONLY INDEXING]"
            else:
                preview = content.get("searchable_text_preview", "")

        return {
            "file_id": file_rec["id"],
            "file_name": file_rec["file_name"],
            "file_path": file_rec["file_path"],
            "file_extension": file_rec["file_extension"],
            "file_size": file_rec["file_size"],
            "file_type": file_rec["file_type"],
            "modified_at": file_rec["modified_at"],
            "privacy_tier": file_rec["privacy_tier"],
            "similarity_score": round(float(score), 4),
            "relevance_label": relevance_label,   # "Keyword" | "Semantic" | "Both"
            "preview": preview,
            "entities": entities,
            "visual_metadata": file_rec.get("visual_metadata"),
        }

    def _semantic_candidates(
        self,
        query: str,
        top_k: int,
        min_score: float,
        folder_ids: Optional[List[int]] = None,
        file_types: Optional[List[str]] = None,
    ) -> Dict[int, Tuple[Dict[str, Any], float]]:
        """Run semantic search and return {file_id: (file_rec, score)} dict.

        Applies optional folder/type post-filters via the repository.
        """
        from seekvault.embeddings.manager import EmbeddingManager  # lazy — avoids numpy at import time
        embedder = EmbeddingManager.get_text_embedder()
        q_vec = embedder.embed_text(query)
        raw_candidates = self.text_index.search(q_vec, top_k=top_k * 4)

        # Zero-trust query-time authorization
        verified = AccessVerifier.filter_results(raw_candidates, self.repository)

        # Optionally apply folder / file-type filter
        if folder_ids or file_types:
            candidate_ids = [rec["id"] for rec, _ in verified]
            allowed = self.repository.get_files_by_ids_filtered(
                candidate_ids, folder_ids=folder_ids, file_types=file_types
            )
            verified = [(rec, sc) for rec, sc in verified if rec["id"] in allowed]

        # Deduplicate by file_id, keep best score
        best: Dict[int, Tuple[Dict[str, Any], float]] = {}
        for file_rec, score in verified:
            if score >= min_score:
                fid = file_rec["id"]
                if fid not in best or score > best[fid][1]:
                    best[fid] = (file_rec, score)
        return best

    # ------------------------------------------------------------------
    # Public API — original methods (unchanged signatures)
    # ------------------------------------------------------------------

    def search_text(
        self,
        query: str,
        top_k: int = SEARCH_DEFAULT_TOP_K,
        min_score: float = SEARCH_MIN_SCORE
    ) -> List[Dict[str, Any]]:
        """Search text documents using Sentence Transformer semantic embeddings."""
        if not query or not query.strip():
            return []

        best = self._semantic_candidates(query, top_k, min_score)
        sorted_files = sorted(best.values(), key=lambda x: x[1], reverse=True)

        return [
            self._enrich_result(rec, score)
            for rec, score in sorted_files[:top_k]
        ]

    def search_images(
        self,
        query: str,
        top_k: int = SEARCH_DEFAULT_TOP_K,
        min_score: float = SEARCH_MIN_SCORE
    ) -> List[Dict[str, Any]]:
        """Search images using natural language query via cross-modal CLIP embeddings."""
        if not query or not query.strip():
            return []

        from seekvault.embeddings.manager import EmbeddingManager  # lazy
        embedder = EmbeddingManager.get_image_embedder()
        q_vec = embedder.embed_text_query(query)
        raw_candidates = self.image_index.search(q_vec, top_k=top_k * 2)

        verified = AccessVerifier.filter_results(raw_candidates, self.repository)

        best: Dict[int, Tuple[Dict[str, Any], float]] = {}
        for file_rec, score in verified:
            if score >= min_score:
                fid = file_rec["id"]
                if fid not in best or score > best[fid][1]:
                    best[fid] = (file_rec, score)

        sorted_files = sorted(best.values(), key=lambda x: x[1], reverse=True)
        return [
            self._enrich_result(rec, score)
            for rec, score in sorted_files[:top_k]
        ]

    def search_all(
        self,
        query: str,
        top_k: int = SEARCH_DEFAULT_TOP_K,
        min_score: float = SEARCH_MIN_SCORE
    ) -> List[Dict[str, Any]]:
        """Combined multimodal search across documents and images."""
        doc_results = self.search_text(query, top_k=top_k, min_score=min_score)
        img_results = self.search_images(query, top_k=top_k, min_score=min_score)

        combined = doc_results + img_results
        combined.sort(key=lambda x: x["similarity_score"], reverse=True)
        return combined[:top_k]

    # ------------------------------------------------------------------
    # New: Hybrid (FTS5 keyword + Semantic) search with filters
    # ------------------------------------------------------------------

    def search_text_filtered(
        self,
        query: str,
        top_k: int = SEARCH_DEFAULT_TOP_K,
        min_score: float = SEARCH_MIN_SCORE,
        folder_ids: Optional[List[int]] = None,
        file_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Semantic-only search with optional folder/type filters.

        Wraps ``search_text`` and passes filter parameters through the
        semantic candidate pipeline.
        """
        if not query or not query.strip():
            return []

        best = self._semantic_candidates(
            query, top_k, min_score,
            folder_ids=folder_ids, file_types=file_types
        )
        sorted_files = sorted(best.values(), key=lambda x: x[1], reverse=True)
        return [
            self._enrich_result(rec, score)
            for rec, score in sorted_files[:top_k]
        ]

    def search_keyword(
        self,
        query: str,
        top_k: int = SEARCH_DEFAULT_TOP_K,
        folder_ids: Optional[List[int]] = None,
        file_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Exact/Keyword-only search using SQLite FTS5 index."""
        if not query or not query.strip():
            return []

        fts_raw = self.repository.fts_search_content(
            query,
            top_k=top_k,
            folder_ids=folder_ids,
            file_types=file_types,
        )
        fids = [row["file_id"] for row in fts_raw]
        if not fids:
            return []

        file_recs = self.repository.get_files_by_ids_filtered(
            fids, folder_ids=folder_ids, file_types=file_types
        )
        results: List[Dict[str, Any]] = []
        for row in fts_raw:
            fid = row["file_id"]
            rec = file_recs.get(fid)
            if not rec:
                continue
            results.append(
                self._enrich_result(
                    rec,
                    score=abs(float(row.get("rank", 1.0))),
                    excerpt=row.get("excerpt", ""),
                    relevance_label="Keyword",
                )
            )
        return results

    def search_hybrid(
        self,
        query: str,
        top_k: int = SEARCH_DEFAULT_TOP_K,
        min_score: float = SEARCH_MIN_SCORE,
        folder_ids: Optional[List[int]] = None,
        file_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Hybrid search: merges FTS5 keyword results and FAISS semantic results.

        Uses Reciprocal Rank Fusion (RRF) to combine the two ranked lists into
        a single ranked result list.  Each result carries a ``relevance_label``
        of "Keyword", "Semantic", or "Both" to indicate which retrieval path(s)
        found it.

        Parameters
        ----------
        query:
            Natural-language or keyword query string.
        top_k:
            Maximum number of results to return (default from config).
        min_score:
            Minimum FAISS cosine-similarity threshold for semantic candidates.
        folder_ids:
            Optional allow-list of folder IDs.  If supplied, only files whose
            ``folder_id`` is in this list are returned.
        file_types:
            Optional allow-list of file type strings (e.g. ``["DOCUMENT"]``).
        """
        if not query or not query.strip():
            return []

        # ── 1. Keyword (FTS5) candidates ────────────────────────────────────
        fts_raw = self.repository.fts_search_content(
            query,
            top_k=top_k * 3,
            folder_ids=folder_ids,
            file_types=file_types,
        )
        # fts_raw is already sorted by BM25 (best first after abs() normalise)
        fts_ranked: Dict[int, Tuple[int, Dict[str, Any], str]] = {}
        for rank, row in enumerate(fts_raw, start=1):
            fid = row["file_id"]
            fts_ranked[fid] = (rank, row, row.get("excerpt", ""))

        # ── 2. Semantic candidates ──────────────────────────────────────────
        try:
            sem_best = self._semantic_candidates(
                query, top_k, min_score,
                folder_ids=folder_ids, file_types=file_types
            )
        except Exception as exc:
            # Model unavailable — fall back to keyword-only
            logger.warning("Semantic search unavailable, falling back to FTS5: %s", exc)
            sem_best = {}

        sem_sorted = sorted(sem_best.items(), key=lambda x: x[1][1], reverse=True)
        sem_ranked: Dict[int, int] = {
            fid: rank for rank, (fid, _) in enumerate(sem_sorted, start=1)
        }

        # ── 3. Reciprocal Rank Fusion ────────────────────────────────────────
        all_fids = set(fts_ranked) | set(sem_ranked)
        rrf_scores: Dict[int, float] = {}
        for fid in all_fids:
            score = 0.0
            if fid in fts_ranked:
                score += _rrf_score(fts_ranked[fid][0])
            if fid in sem_ranked:
                score += _rrf_score(sem_ranked[fid])
            rrf_scores[fid] = score

        sorted_fids = sorted(all_fids, key=lambda fid: rrf_scores[fid], reverse=True)

        # ── 4. Fetch file records for any FIDs that came from FTS but not sem ─
        sem_file_recs: Dict[int, Dict[str, Any]] = {
            fid: rec for fid, (rec, _) in sem_best.items()
        }
        fts_only_fids = [fid for fid in sorted_fids if fid not in sem_file_recs]
        if fts_only_fids:
            extra = self.repository.get_files_by_ids_filtered(
                fts_only_fids, folder_ids=folder_ids, file_types=file_types
            )
            sem_file_recs.update(extra)

        # ── 5. Build enriched result list ───────────────────────────────────
        results: List[Dict[str, Any]] = []
        for fid in sorted_fids[:top_k]:
            file_rec = sem_file_recs.get(fid)
            if file_rec is None:
                continue  # was filtered out by authorization

            in_fts = fid in fts_ranked
            in_sem = fid in sem_ranked

            if in_fts and in_sem:
                label = "Both"
            elif in_fts:
                label = "Keyword"
            else:
                label = "Semantic"

            excerpt = fts_ranked[fid][2] if in_fts else ""
            sem_score = sem_best[fid][1] if in_sem else rrf_scores[fid]

            results.append(
                self._enrich_result(
                    file_rec,
                    score=rrf_scores[fid],
                    excerpt=excerpt,
                    relevance_label=label,
                )
            )
            # Override similarity_score with the RRF score for consistent sorting
            results[-1]["similarity_score"] = round(rrf_scores[fid], 6)
            results[-1]["semantic_score"] = round(sem_score, 4)

        return results
