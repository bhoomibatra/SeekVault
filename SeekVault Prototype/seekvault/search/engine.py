from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from seekvault.config import (
    TEXT_INDEX_PATH, TEXT_METADATA_PATH, TEXT_EMBEDDING_DIM,
    IMAGE_INDEX_PATH, IMAGE_METADATA_PATH, IMAGE_EMBEDDING_DIM,
    SEARCH_DEFAULT_TOP_K, SEARCH_MIN_SCORE
)
from seekvault.database.repository import Repository
from seekvault.embeddings.manager import EmbeddingManager
from seekvault.search.faiss_index import FaissIndex
from seekvault.search.verifier import AccessVerifier
import logging

logger = logging.getLogger(__name__)

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

    def _enrich_result(self, file_rec: Dict[str, Any], score: float) -> Dict[str, Any]:
        """Attach snippet previews and entity metadata to result."""
        content = self.repository.get_file_content(file_rec["id"])
        entities = self.repository.get_detected_entities_for_file(file_rec["id"])
        
        preview = ""
        if content:
            # If redacted, show redacted preview to preserve privacy
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
            "preview": preview,
            "entities": entities,
            "visual_metadata": file_rec.get("visual_metadata")
        }

    def search_text(
        self,
        query: str,
        top_k: int = SEARCH_DEFAULT_TOP_K,
        min_score: float = SEARCH_MIN_SCORE
    ) -> List[Dict[str, Any]]:
        """Search text documents using Sentence Transformer semantic embeddings."""
        if not query or not query.strip():
            return []

        embedder = EmbeddingManager.get_text_embedder()
        q_vec = embedder.embed_text(query)
        # Search additional candidates to account for multiple chunks per file
        raw_candidates = self.text_index.search(q_vec, top_k=top_k * 4)

        # Zero-trust query-time authorization check
        verified = AccessVerifier.filter_results(raw_candidates, self.repository)

        # Deduplicate chunk matches by file_id, preserving the maximum similarity score
        best_by_file: Dict[int, Tuple[Dict[str, Any], float]] = {}
        for file_rec, score in verified:
            if score >= min_score:
                fid = file_rec["id"]
                if fid not in best_by_file or score > best_by_file[fid][1]:
                    best_by_file[fid] = (file_rec, score)

        # Sort deduplicated files by score descending
        sorted_files = sorted(best_by_file.values(), key=lambda x: x[1], reverse=True)

        results = []
        for file_rec, score in sorted_files[:top_k]:
            results.append(self._enrich_result(file_rec, score))

        return results

    def search_images(
        self,
        query: str,
        top_k: int = SEARCH_DEFAULT_TOP_K,
        min_score: float = SEARCH_MIN_SCORE
    ) -> List[Dict[str, Any]]:
        """Search images using natural language query via cross-modal CLIP embeddings."""
        if not query or not query.strip():
            return []

        embedder = EmbeddingManager.get_image_embedder()
        q_vec = embedder.embed_text_query(query)
        raw_candidates = self.image_index.search(q_vec, top_k=top_k * 2)

        # Zero-trust query-time authorization check
        verified = AccessVerifier.filter_results(raw_candidates, self.repository)

        best_by_file: Dict[int, Tuple[Dict[str, Any], float]] = {}
        for file_rec, score in verified:
            if score >= min_score:
                fid = file_rec["id"]
                if fid not in best_by_file or score > best_by_file[fid][1]:
                    best_by_file[fid] = (file_rec, score)

        sorted_files = sorted(best_by_file.values(), key=lambda x: x[1], reverse=True)

        results = []
        for file_rec, score in sorted_files[:top_k]:
            results.append(self._enrich_result(file_rec, score))

        return results

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
