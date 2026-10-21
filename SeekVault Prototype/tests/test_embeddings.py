import pytest
import numpy as np
from seekvault.embeddings.manager import EmbeddingManager

def test_text_embedder():
    embedder = EmbeddingManager.get_text_embedder()
    vec = embedder.embed_text("Candidate elimination algorithm and machine learning concepts")
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (384,)
    # Check L2 normalization
    norm = np.linalg.norm(vec)
    assert abs(norm - 1.0) < 1e-4

def test_semantic_similarity_ranking():
    embedder = EmbeddingManager.get_text_embedder()
    q_vec = embedder.embed_text("candidate elimination machine learning")
    doc1_vec = embedder.embed_text("Notes on version space and candidate elimination in ML")
    doc2_vec = embedder.embed_text("Recipe for baking chocolate chip cookies in oven")

    sim1 = float(np.dot(q_vec, doc1_vec))
    sim2 = float(np.dot(q_vec, doc2_vec))

    # Relevant document must have significantly higher similarity than irrelevant document
    assert sim1 > sim2
    assert sim1 > 0.50
