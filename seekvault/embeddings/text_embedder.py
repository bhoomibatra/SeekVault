import numpy as np
from typing import List, Union
from seekvault.core.logger import logger

class TextEmbedder:
    """
    Sentence Transformers wrapper generating L2-normalized 384-dimensional text embeddings.
    Inner product dot product on unit-normalized vectors equals Cosine Similarity.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self.dimension = 384

    @property
    def model(self):
        if self._model is None:
            logger.info(f"TextEmbedder: Loading SentenceTransformer model '{self.model_name}'...")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self.dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"TextEmbedder: Model loaded successfully. Vector Dimension = {self.dimension}")
        return self._model

    def encode_text(self, text: str) -> np.ndarray:
        """
        Embeds a single text string into a normalized 1D float32 numpy array.
        """
        if not text or not text.strip():
            return np.zeros(self.dimension, dtype=np.float32)

        raw_vec = self.model.encode(text, convert_to_numpy=True, show_progress_bar=False)
        norm = np.linalg.norm(raw_vec)
        if norm > 0:
            raw_vec = raw_vec / norm
        return raw_vec.astype(np.float32)

    def encode_passages(self, passages: List[str]) -> np.ndarray:
        """
        Embeds a list of text passages into a 2D float32 numpy array (shape: N x dimension).
        """
        if not passages:
            return np.empty((0, self.dimension), dtype=np.float32)

        cleaned_passages = [p if p and p.strip() else " " for p in passages]
        raw_vecs = self.model.encode(cleaned_passages, convert_to_numpy=True, show_progress_bar=False)
        
        # L2-normalize each row
        norms = np.linalg.norm(raw_vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized_vecs = raw_vecs / norms
        return normalized_vecs.astype(np.float32)
