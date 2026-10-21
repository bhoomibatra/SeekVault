from typing import List, Union
from pathlib import Path
import numpy as np
from PIL import Image
from sentence_transformers import SentenceTransformer
from seekvault.config import IMAGE_EMBEDDING_MODEL
import logging

logger = logging.getLogger(__name__)

class ImageEmbedder:
    def __init__(self, model_name: str = IMAGE_EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            logger.info(f"Loading multimodal vision model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_image(self, image_path: Union[str, Path]) -> np.ndarray:
        """Generate normalized 512-d CLIP embedding for an image."""
        model = self._load_model()
        with Image.open(image_path) as img:
            rgb_img = img.convert("RGB")
            vec = model.encode(rgb_img, normalize_embeddings=True, show_progress_bar=False)
            return np.array(vec, dtype=np.float32)

    def embed_text_query(self, text_query: str) -> np.ndarray:
        """Embed a natural language text query into the CLIP cross-modal space."""
        model = self._load_model()
        vec = model.encode(text_query, normalize_embeddings=True, show_progress_bar=False)
        return np.array(vec, dtype=np.float32)
