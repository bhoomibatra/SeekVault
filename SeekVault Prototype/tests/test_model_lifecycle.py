import os
import tempfile
from pathlib import Path
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from seekvault.embeddings.text_embedder import TextEmbedder, ModelUnavailableError
from seekvault.embeddings.image_embedder import ImageEmbedder
from seekvault.embeddings.manager import EmbeddingManager
from seekvault.search.engine import SearchEngine
from seekvault.database.repository import Repository
from seekvault import config


def test_embedding_dimensions_and_normalization():
    """TASK-08: Text embeddings must be normalized 384-d float32 vectors;
    image and cross-modal text query embeddings must be normalized 512-d float32 vectors."""
    text_embedder = EmbeddingManager.get_text_embedder()
    img_embedder = EmbeddingManager.get_image_embedder()

    # 1. Text embedding dimension
    sample_text = "SeekVault local privacy-first architecture and memory bounds."
    text_vec = text_embedder.embed_text(sample_text)
    assert isinstance(text_vec, np.ndarray)
    assert text_vec.shape == (config.TEXT_EMBEDDING_DIM,)
    assert text_vec.dtype == np.float32

    # L2-norm must be ~1.0 (normalized)
    norm = np.linalg.norm(text_vec)
    assert np.isclose(norm, 1.0, atol=1e-4), f"Text vector is not L2-normalized: norm={norm}"

    # 2. Vision cross-modal text query dimension
    query_vec = img_embedder.embed_text_query("mountain landscape with pine trees")
    assert isinstance(query_vec, np.ndarray)
    assert query_vec.shape == (config.IMAGE_EMBEDDING_DIM,)
    assert query_vec.dtype == np.float32

    query_norm = np.linalg.norm(query_vec)
    assert np.isclose(query_norm, 1.0, atol=1e-4), f"Vision query vector is not L2-normalized: norm={query_norm}"


def test_shared_multimodal_embedding_space():
    """TASK-08: An image and a text query must project into the shared 512-d space
    where dot product corresponds directly to cosine similarity."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "test_color_square.png"
        img = Image.new("RGB", (100, 100), color=(30, 144, 255))
        img.save(img_path)

        img_embedder = EmbeddingManager.get_image_embedder()
        img_vec = img_embedder.embed_image(img_path)
        query_vec = img_embedder.embed_text_query("a bright blue square image")

        assert img_vec.shape == (512,)
        assert query_vec.shape == (512,)

        # Dot product of two L2-normalized vectors is in [-1, 1]
        cosine_sim = float(np.dot(img_vec, query_vec))
        assert -1.0 <= cosine_sim <= 1.0


def test_singleton_lifecycle_prevents_duplicate_allocations():
    """TASK-08: EmbeddingManager must retain a single instance of each embedder
    and underlying transformer to avoid RAM bloat and redundant initializations."""
    EmbeddingManager.reset()

    # First retrieval
    t1 = EmbeddingManager.get_text_embedder()
    i1 = EmbeddingManager.get_image_embedder()

    # Second retrieval
    t2 = EmbeddingManager.get_text_embedder()
    i2 = EmbeddingManager.get_image_embedder()

    # Must be the exact same instances in memory
    assert t1 is t2, "TextEmbedder is not a singleton!"
    assert i1 is i2, "ImageEmbedder is not a singleton!"


def test_embedding_manager_diagnostics_status():
    """TASK-08: EmbeddingManager.get_models_status() provides structured diagnostic info."""
    status = EmbeddingManager.get_models_status()

    assert "text_model" in status
    assert "image_model" in status
    assert "offline_mode" in status
    assert "cache_dir" in status

    assert status["text_model"]["name"] == config.TEXT_EMBEDDING_MODEL
    assert status["text_model"]["dimension"] == 384

    assert status["image_model"]["name"] == config.IMAGE_EMBEDDING_MODEL
    assert status["image_model"]["dimension"] == 512


def test_missing_model_raises_model_unavailable_error_no_fake_results():
    """TASK-08: When a model fails to load, ModelUnavailableError is raised with
    clear diagnostic details. SearchEngine must NEVER return fake search results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        repo = Repository(db_path=base_dir / "test.db")
        engine = SearchEngine(
            repository=repo,
            text_index_path=base_dir / "t.faiss",
            text_meta_path=base_dir / "t.json",
            image_index_path=base_dir / "i.faiss",
            image_meta_path=base_dir / "i.json"
        )

        mock_unavailable = MagicMock(side_effect=ModelUnavailableError(
            "nonexistent-model",
            FileNotFoundError("Model weights not found in local cache")
        ))

        with patch.object(TextEmbedder, "embed_text", mock_unavailable):
            # Attempt text search when embedder is unavailable
            with pytest.raises(ModelUnavailableError) as exc_info:
                engine.search_text("machine learning notes")

            assert "nonexistent-model" in str(exc_info.value)
            assert "Offline Mode" in str(exc_info.value)
