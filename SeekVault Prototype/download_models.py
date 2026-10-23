"""
download_models.py — Pre-download and cache SeekVault ML models for offline operation.

When running SeekVault with HF_HUB_OFFLINE=1, models must be cached locally beforehand.
This utility temporarily enables network access to fetch and cache:
  1. all-MiniLM-L6-v2 (text embedding model, 384-d)
  2. clip-ViT-B-32 (multimodal vision embedding model, 512-d)

Usage:
  python download_models.py
"""

import os
import sys
from pathlib import Path
from PIL import Image
import numpy as np

# Temporarily enable network for HuggingFace model download
os.environ["HF_HUB_OFFLINE"] = "0"
os.environ["TRANSFORMERS_OFFLINE"] = "0"

print("=" * 60)
print("SeekVault Model Cache Initializer (Offline Setup)")
print("=" * 60)

cache_dir = os.environ.get("HF_HOME") or str(Path.home() / ".cache" / "huggingface" / "hub")
print(f"HuggingFace Cache Directory: {cache_dir}\n")

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("[ERROR] sentence-transformers is not installed. Please run: pip install -r requirements.txt")
    sys.exit(1)

# 1. Fetch Text Embedding Model
TEXT_MODEL_NAME = "all-MiniLM-L6-v2"
print(f"[1/2] Downloading & caching text model: {TEXT_MODEL_NAME} ...")
try:
    text_model = SentenceTransformer(TEXT_MODEL_NAME)
    # Warmup / verify inference
    vec = text_model.encode("SeekVault offline local search test", normalize_embeddings=True)
    assert len(vec) == 384
    print(f"      [OK] Text model ready ({len(vec)}-dimensional embeddings).")
except Exception as e:
    print(f"      [ERROR] Failed to download {TEXT_MODEL_NAME}: {e}")
    sys.exit(1)

# 2. Fetch Vision Embedding Model
IMAGE_MODEL_NAME = "clip-ViT-B-32"
print(f"\n[2/2] Downloading & caching vision model: {IMAGE_MODEL_NAME} ...")
try:
    image_model = SentenceTransformer(IMAGE_MODEL_NAME)
    # Warmup with dummy 64x64 test image
    dummy_img = Image.fromarray(np.zeros((64, 64, 3), dtype=np.uint8))
    img_vec = image_model.encode(dummy_img, normalize_embeddings=True)
    assert len(img_vec) == 512
    print(f"      [OK] Vision model ready ({len(img_vec)}-dimensional embeddings).")
except Exception as e:
    print(f"      [ERROR] Failed to download {IMAGE_MODEL_NAME}: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("SUCCESS: All models are cached locally.")
print("SeekVault is ready to run in 100% offline mode (HF_HUB_OFFLINE=1).")
print("=" * 60)
