import os
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
from seekvault.config import TEXT_EMBEDDING_MODEL, TEXT_EMBEDDING_DIM
import logging

logger = logging.getLogger(__name__)


class ModelUnavailableError(RuntimeError):
    """Raised when an embedding model cannot be loaded (missing from cache, offline, or corrupt)."""
    def __init__(self, model_name: str, original_error: Exception):
        cache_dir = os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface/hub")
        msg = (
            f"Text embedding model '{model_name}' is unavailable.\n"
            f"Details: {original_error}\n"
            f"Cache Location: {cache_dir}\n"
            f"Offline Mode: HF_HUB_OFFLINE={os.environ.get('HF_HUB_OFFLINE', '0')}.\n"
            f"Remedy: Verify local model weights exist in cache or run online initialization."
        )
        super().__init__(msg)
        self.model_name = model_name
        self.original_error = original_error


class TextEmbedder:
    def __init__(self, model_name: str = TEXT_EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None
        self.dimension = TEXT_EMBEDDING_DIM

    def _load_model(self):
        if self._model is None:
            logger.info(f"Loading text embedding model: {self.model_name}")
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception as e:
                logger.error(f"Failed to load text embedding model '{self.model_name}': {e}")
                raise ModelUnavailableError(self.model_name, e) from e
        return self._model

    def is_available(self) -> bool:
        """Check if model can be loaded without throwing unhandled exceptions."""
        try:
            self._load_model()
            return True
        except Exception:
            return False

    def embed_text(self, text: str) -> np.ndarray:
        """Generate normalized 384-d embedding for single text snippet."""
        model = self._load_model()
        vec = model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        return np.array(vec, dtype=np.float32)

    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """Generate normalized embeddings for batch of texts."""
        if not texts:
            return np.empty((0, 384), dtype=np.float32)
        model = self._load_model()
        vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.array(vecs, dtype=np.float32)
