import json
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import numpy as np
import faiss
import logging

logger = logging.getLogger(__name__)

class FaissIndex:
    def __init__(self, dimension: int, index_path: Optional[Path] = None, meta_path: Optional[Path] = None):
        self.dimension = dimension
        self.index_path = index_path
        self.meta_path = meta_path
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product on normalized vectors = Cosine Similarity
        self.vector_ids: List[int] = []  # Maps FAISS index row -> file_id
        self._last_loaded_mtime: float = 0.0
        
        # Load from disk if files exist
        if self.index_path and self.meta_path and self.index_path.exists() and self.meta_path.exists():
            self.load()

    def _check_and_reload(self) -> None:
        """Reload index from disk if the on-disk index file was modified externally."""
        if self.index_path and self.index_path.exists():
            try:
                mtime = self.index_path.stat().st_mtime
                if mtime > self._last_loaded_mtime:
                    logger.info("On-disk FAISS index updated. Hot-reloading into memory.")
                    self.load()
            except Exception as e:
                logger.error(f"Error checking index mtime for reload: {e}")

    def has_file(self, file_id: int) -> bool:
        """Check whether at least one vector for the given file_id exists in the index."""
        self._check_and_reload()
        return file_id in self.vector_ids

    def add_vector(self, file_id: int, vector: np.ndarray) -> int:
        """Add a single normalized vector to the FAISS index."""
        # If vector is 1D, reshape to (1, D)
        vec = np.ascontiguousarray(vector, dtype=np.float32)
        if len(vec.shape) == 1:
            vec = vec.reshape(1, -1)

        # L2-normalize defensively to guarantee cosine similarity
        faiss.normalize_L2(vec)

        faiss_id = self.index.ntotal
        self.index.add(vec)
        self.vector_ids.append(file_id)
        self.save()
        return faiss_id

    def search(self, query_vector: np.ndarray, top_k: int = 10) -> List[Tuple[int, float]]:
        """Search nearest vectors using cosine similarity. Returns list of (file_id, score)."""
        self._check_and_reload()
        if self.index.ntotal == 0:
            return []

        q_vec = np.ascontiguousarray(query_vector, dtype=np.float32)
        if len(q_vec.shape) == 1:
            q_vec = q_vec.reshape(1, -1)

        faiss.normalize_L2(q_vec)

        actual_k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(q_vec, actual_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and idx < len(self.vector_ids):
                file_id = self.vector_ids[idx]
                results.append((file_id, float(score)))

        return results

    def remove_file(self, file_id: int) -> bool:
        """Remove vectors for a given file_id by rebuilding index without it."""
        if file_id not in self.vector_ids:
            return False

        # Rebuild index without the matching file_id
        keep_indices = [i for i, fid in enumerate(self.vector_ids) if fid != file_id]
        if not keep_indices:
            self.reset()
            return True

        # Extract remaining vectors
        remaining_vectors = []
        for i in keep_indices:
            vec = self.index.reconstruct(i)
            remaining_vectors.append(vec)

        remaining_matrix = np.array(remaining_vectors, dtype=np.float32)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(remaining_matrix)
        self.vector_ids = [self.vector_ids[i] for i in keep_indices]
        self.save()
        return True

    def reset(self) -> None:
        """Clear the entire index and memory mappings."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.vector_ids = []
        self.save()

    def save(self) -> None:
        if self.index_path and self.meta_path:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self.index, str(self.index_path))
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump(self.vector_ids, f)
            if self.index_path.exists():
                self._last_loaded_mtime = self.index_path.stat().st_mtime

    def load(self) -> None:
        if self.index_path and self.meta_path and self.index_path.exists() and self.meta_path.exists():
            try:
                self.index = faiss.read_index(str(self.index_path))
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    self.vector_ids = json.load(f)
                self._last_loaded_mtime = self.index_path.stat().st_mtime
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors.")
            except Exception as e:
                logger.error(f"Error loading FAISS index: {e}")
                self.reset()

