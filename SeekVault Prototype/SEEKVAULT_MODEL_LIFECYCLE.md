# SeekVault — Embedding Providers & Model Lifecycle Guide
**Task:** TASK-08 — Embedding Providers, Model Lifecycles, and Shared Embedding Spaces  
**Date:** 2026-10-23  
**Status:** Implemented & Verified  

---

## 1. Model Specifications & Roles

SeekVault employs two local transformer models configured for CPU/GPU inference.

| Attribute | Text Semantic Search Model | Vision / Multimodal Model |
|---|---|---|
| **Repository Name** | `sentence-transformers/all-MiniLM-L6-v2` | `sentence-transformers/clip-ViT-B-32` |
| **Primary Architecture** | BERT-based Cross-Encoder/Bi-Encoder (MiniLM) | OpenAI CLIP (Vision Transformer ViT-B/32) |
| **Modality** | Unimodal Text (Documents, Code, Markdown) | Multimodal (Text Query ↔ Image Content) |
| **Embedding Dimension** | **384** float32 dimensions | **512** float32 dimensions |
| **Max Token Length** | 256 WordPiece tokens | 77 tokens (text query), 224x224 RGB image |
| **Parameter Count** | ~22.7 Million parameters | ~151 Million parameters |
| **Disk Storage** | ~90 MB on disk | ~600 MB on disk |
| **RAM Footprint (Inference)** | ~120 MB RAM | ~750 MB RAM |
| **Open Source License** | Apache License 2.0 | MIT License / Apache License 2.0 |

---

## 2. Shared Multimodal Embedding Space

To enable finding images via natural language concepts (e.g., searching *"sunset over mountain ridge"* or *"handwritten meeting whiteboard"* without needing manual image tags):

1. **Image Indexing:**
   - The visual image is preprocessed into a 224x224 RGB tensor.
   - Passed through `ImageEmbedder.embed_image(path)`.
   - Generates a normalized **512-dimensional vector** residing in CLIP's joint visual space.
   - Vector is stored in `image_index.faiss`.

2. **Query Execution:**
   - When natural language query is searched across images, `ImageEmbedder.embed_text_query(query)` passes the query text through CLIP's text transformer.
   - Generates a normalized **512-dimensional vector** residing in the exact same joint space.
   - Nearest neighbors are queried via Inner Product (Cosine Similarity) in FAISS.

3. **Separation of Modalities:**
   - Unimodal document text vectors (384-d, `all-MiniLM-L6-v2`) and visual CLIP vectors (512-d, `clip-ViT-B-32`) are kept strictly separated in independent FAISS indices (`text_index.faiss` and `image_index.faiss`).
   - Dimension mismatches are impossible by architectural separation.

---

## 3. Offline Mode & Local Cache Hierarchy

SeekVault guarantees that all semantic search and inference runs strictly offline on the user's workstation.

### Offline Enforcement
The following environment variables are enforced in `config.py` and Windows launchers (`run_seekvault.bat`, `run_seekvault.ps1`):
```bash
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

### Cache Location & Discovery
Model weights are resolved in this priority order:
1. `HF_HOME` environment variable (if explicitly customized).
2. Standard user HuggingFace cache: `%USERPROFILE%\.cache\huggingface\hub\`:
   - `models--sentence-transformers--all-MiniLM-L6-v2/`
   - `models--sentence-transformers--clip-ViT-B-32/`
3. Fallback to `TORCH_HOME` cache.

---

## 4. Lifecycle & Singleton Management

To prevent high RAM consumption and redundant model initialization:
- `seekvault.embeddings.manager.EmbeddingManager` provides cached singleton access via `get_text_embedder()` and `get_image_embedder()`.
- Models are loaded lazily on first embedding demand and retained in memory for the life of the application.
- `EmbeddingManager.get_models_status()` provides real-time health checks without re-triggering model downloads.

---

## 5. Failure Policy: Zero Fake Results

If local model weights are absent or corrupt while operating in offline mode:
- `ModelUnavailableError` is raised with explicit diagnostics containing model name, cache directory, and offline settings.
- **Rule:** SeekVault **never** returns fake/mock search results, random matches, or synthetic rankings upon model failure.
- Search interfaces honestly report an index-not-ready state to the user.
