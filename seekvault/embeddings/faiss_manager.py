import os
import faiss
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
from seekvault.config import INDEX_DIR
from seekvault.core.logger import logger

class FAISSManager:
    """
    Manages FAISS vector index (IndexIDMap2 over IndexFlatIP) for fast Cosine similarity search.
    Supports persistent disk storage and incremental vector additions/deletions.
    """

    def __init__(self, index_name: str = "seekvault_text.faiss", dimension: int = 384, custom_index_dir: Optional[str] = None):
        self.index_name = index_name
        self.dimension = dimension
        target_dir = Path(custom_index_dir) if custom_index_dir else INDEX_DIR
        self.index_path = target_dir / index_name
        self.index = self._load_or_create_index()

    def _load_or_create_index(self) -> faiss.IndexIDMap2:
        if self.index_path.exists():
            try:
                idx = faiss.read_index(str(self.index_path))
                logger.info(f"FAISSManager: Loaded existing vector index '{self.index_name}' with {idx.ntotal} vectors.")
                return idx
            except Exception as e:
                logger.error(f"FAISSManager: Failed to read index '{self.index_path}': {e}. Rebuilding clean index.")
                
        base_index = faiss.IndexFlatIP(self.dimension)
        index = faiss.IndexIDMap2(base_index)
        logger.info(f"FAISSManager: Initialized new IndexIDMap2 flat index with dimension {self.dimension}.")
        return index

    def save_index(self) -> None:
        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(self.index_path))
            logger.info(f"FAISSManager: Saved vector index with {self.index.ntotal} vectors to '{self.index_path}'.")
        except Exception as e:
            logger.error(f"FAISSManager: Failed to write FAISS index to disk: {e}")

    def add_vectors(self, vectors: np.ndarray, faiss_ids: List[int]) -> None:
        if len(vectors) == 0 or len(faiss_ids) == 0:
            return
            
        if len(vectors) != len(faiss_ids):
            raise ValueError(f"Vector count ({len(vectors)}) does not match ID count ({len(faiss_ids)}).")
            
        vecs_float32 = np.ascontiguousarray(vectors, dtype=np.float32)
        ids_int64 = np.ascontiguousarray(faiss_ids, dtype=np.int64)
        
        self.index.add_with_ids(vecs_float32, ids_int64)
        self.save_index()

    def remove_vectors(self, faiss_ids: List[int]) -> int:
        if not faiss_ids or self.index.ntotal == 0:
            return 0
            
        ids_int64 = np.ascontiguousarray(faiss_ids, dtype=np.int64)
        selector = faiss.IDSelectorBatch(ids_int64)
        removed_count = self.index.remove_ids(selector)
        if removed_count > 0:
            self.save_index()
            logger.info(f"FAISSManager: Removed {removed_count} vectors from index.")
        return removed_count

    def search(self, query_vector: np.ndarray, top_k: int = 10) -> Tuple[List[float], List[int]]:
        if self.index.ntotal == 0:
            return [], []
            
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
            
        vec_float32 = np.ascontiguousarray(query_vector, dtype=np.float32)
        k = min(top_k, self.index.ntotal)
        
        distances, ids = self.index.search(vec_float32, k)
        
        flat_distances = distances[0].tolist()
        flat_ids = ids[0].tolist()
        
        # Filter out invalid / unmapped IDs (-1)
        valid_results = [(d, i) for d, i in zip(flat_distances, flat_ids) if i != -1]
        
        if not valid_results:
            return [], []
            
        res_distances, res_ids = zip(*valid_results)
        return list(res_distances), list(res_ids)

    def reset_index(self) -> None:
        base_index = faiss.IndexFlatIP(self.dimension)
        self.index = faiss.IndexIDMap2(base_index)
        if self.index_path.exists():
            os.remove(self.index_path)
        logger.info("FAISSManager: Index reset to empty state.")
