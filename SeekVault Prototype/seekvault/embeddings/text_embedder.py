from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
from seekvault.config import TEXT_EMBEDDING_MODEL
import logging

logger = logging.getLogger(__name__)

class TextEmbedder:
    def __init__(self, model_name: str = TEXT_EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            logger.info(f"Loading text embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

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
