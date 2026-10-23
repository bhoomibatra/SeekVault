import os
from pathlib import Path
from typing import Dict, Any, Optional
from seekvault.embeddings.text_embedder import TextEmbedder
from seekvault.embeddings.image_embedder import ImageEmbedder
from seekvault.config import (
    TEXT_EMBEDDING_MODEL, TEXT_EMBEDDING_DIM,
    IMAGE_EMBEDDING_MODEL, IMAGE_EMBEDDING_DIM
)

class EmbeddingManager:
    _text_embedder: Optional[TextEmbedder] = None
    _image_embedder: Optional[ImageEmbedder] = None

    @classmethod
    def get_text_embedder(cls) -> TextEmbedder:
        """Retrieve the singleton TextEmbedder instance to prevent duplicate model allocations."""
        if cls._text_embedder is None:
            cls._text_embedder = TextEmbedder()
        return cls._text_embedder

    @classmethod
    def get_image_embedder(cls) -> ImageEmbedder:
        """Retrieve the singleton ImageEmbedder instance to prevent duplicate vision model allocations."""
        if cls._image_embedder is None:
            cls._image_embedder = ImageEmbedder()
        return cls._image_embedder

    @classmethod
    def reset(cls) -> None:
        """Reset cached embedder instances (useful for testing and configuration changes)."""
        cls._text_embedder = None
        cls._image_embedder = None

    @classmethod
    def get_models_status(cls) -> Dict[str, Any]:
        """Return diagnostic health and readiness status for both embedding models."""
        cache_dir = os.environ.get("HF_HOME") or str(Path.home() / ".cache" / "huggingface" / "hub")
        offline_mode = os.environ.get("HF_HUB_OFFLINE", "0") in ("1", "true", "True")

        text_inst = cls._text_embedder
        image_inst = cls._image_embedder

        return {
            "offline_mode": offline_mode,
            "cache_dir": cache_dir,
            "text_model": {
                "name": TEXT_EMBEDDING_MODEL,
                "dimension": TEXT_EMBEDDING_DIM,
                "initialized": text_inst is not None and text_inst._model is not None,
                "available": text_inst.is_available() if text_inst else TextEmbedder().is_available()
            },
            "image_model": {
                "name": IMAGE_EMBEDDING_MODEL,
                "dimension": IMAGE_EMBEDDING_DIM,
                "initialized": image_inst is not None and image_inst._model is not None,
                "available": image_inst.is_available() if image_inst else ImageEmbedder().is_available()
            }
        }
