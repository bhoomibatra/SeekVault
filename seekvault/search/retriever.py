from typing import List, Dict, Any, Optional
from seekvault.embeddings.text_embedder import TextEmbedder
from seekvault.embeddings.faiss_manager import FAISSManager
from seekvault.search.access_verifier import AccessVerifier
from seekvault.core.database import get_db_connection
from seekvault.core.logger import logger

class SemanticSearchEngine:
    """
    Multimodal Semantic Search Engine providing natural language vector search
    across indexed documents and images, with query-time folder access verification.
    """

    def __init__(self, embedder: Optional[TextEmbedder] = None, faiss_mgr: Optional[FAISSManager] = None):
        self.embedder = embedder or TextEmbedder()
        self.faiss_mgr = faiss_mgr or FAISSManager()

    def search(
        self,
        query: str,
        top_k: int = 10,
        custom_db_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return []

        # 1. Generate text query embedding
        query_vector = self.embedder.encode_text(query.strip())

        # 2. Search FAISS index for top K candidates
        distances, faiss_ids = self.faiss_mgr.search(query_vector, top_k=top_k * 3)
        if not faiss_ids:
            return []

        # 3. Query SQLite for mapped entities & metadata
        conn = get_db_connection(custom_db_path)
        cursor = conn.cursor()
        
        results: List[Dict[str, Any]] = []
        seen_file_ids = set()

        try:
            for dist, fid in zip(distances, faiss_ids):
                cursor.execute(
                    """
                    SELECT m.entity_type, m.entity_id, m.file_id,
                           f.file_name, f.file_path, f.file_type, f.file_extension,
                           f.file_size, f.privacy_tier, f.modified_at,
                           c.raw_text, c.redacted_text, c.page_number
                    FROM faiss_index_mapping m
                    JOIN files f ON m.file_id = f.id
                    LEFT JOIN document_chunks c ON m.entity_type = 'document_chunk' AND m.entity_id = c.id
                    WHERE m.faiss_vector_id = ? AND f.indexing_status != 'DELETED'
                    """,
                    (fid,)
                )
                row = cursor.fetchone()
                if not row:
                    continue
                    
                record = dict(row)
                file_path = record["file_path"]

                # 4. REQUIREMENT 10: Query-time Access Verification
                if not AccessVerifier.is_file_accessible(file_path, custom_db_path=custom_db_path):
                    logger.debug(f"SearchEngine: Filtered out inaccessible file during query: {file_path}")
                    continue

                # 5. Format similarity score (Cosine Similarity percentage)
                raw_score = float(dist)
                similarity_percent = round(max(0.0, min(1.0, raw_score)) * 100, 1)

                matched_text = record.get("redacted_text") or record.get("raw_text") or ""

                results.append({
                    "file_id": record["file_id"],
                    "file_name": record["file_name"],
                    "file_path": record["file_path"],
                    "file_type": record["file_type"],
                    "file_extension": record["file_extension"],
                    "file_size": record["file_size"],
                    "privacy_tier": record["privacy_tier"],
                    "page_number": record.get("page_number", 1),
                    "matched_text": matched_text,
                    "similarity_score": similarity_percent,
                    "raw_score": raw_score,
                    "faiss_vector_id": fid
                })

                if len(results) >= top_k:
                    break

        finally:
            conn.close()

        # Sort results by raw similarity score descending
        results.sort(key=lambda x: x["raw_score"], reverse=True)
        return results
