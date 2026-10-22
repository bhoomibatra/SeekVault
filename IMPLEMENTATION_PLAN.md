# SeekVault Architectural Implementation Plan

This implementation plan details the multi-phase engineering roadmap for building **SeekVault**, a local-first, privacy-aware multimodal semantic search and organization engine.

> [!IMPORTANT]
> **Strict Non-Mutation Policy**: Original user files within authorized folders must **never** be altered, written to, or moved by SeekVault. All privacy masking and indexing operations are performed strictly in memory.

---

## Technical Stack Summary
- **Language**: Python 3.10+
- **Frontend / UI**: Streamlit
- **Document Parsers**: PyMuPDF (`fitz`), `python-docx`
- **Image & OCR**: Pillow (`PIL`), Tesseract OCR (`pytesseract`)
- **Text Embeddings**: Sentence Transformers (`all-MiniLM-L6-v2`)
- **Visual Embeddings**: CLIP (`openai/clip-vit-base-patch32`) / SigLIP
- **Privacy & Redaction**: Microsoft Presidio (`presidio-analyzer`, `presidio-anonymizer`) + Custom Regex Rules
- **File System Watcher**: Watchdog
- **Vector Search Engine**: FAISS (`faiss-cpu`)
- **Metadata Store**: SQLite 3
- **Optional Local LLM**: Ollama (`llama3` / `llava`)

---

## Phase 1: Core Foundation & Configuration
Establish central configuration, logging, database setup, and core utility modules.

### Components & Tasks
1. **[NEW] `seekvault/config.py`**
   - Define directory constants (`DATA_DIR`, `DB_PATH`, `INDEX_DIR`).
   - Define model defaults (`all-MiniLM-L6-v2`, `clip-vit-base-patch32`).
   - Configure sensitivity threshold rules and supported extension white-lists (`.pdf`, `.docx`, `.txt`, `.md`, `.png`, `.jpg`, `.jpeg`, `.bmp`, `.webp`).
2. **[NEW] `seekvault/core/logger.py`**
   - Configure structured console logging and file logging (`seekvault.log`).
3. **[NEW] `seekvault/core/database.py`**
   - Implement SQLite connection manager with WAL mode enabled.
   - Implement schema initialization script matching the schema in `DATABASE.md`.
   - Provide CRUD helper functions for `authorized_folders`, `files`, `document_chunks`, `image_metadata`, and `faiss_index_mapping`.

---

## Phase 2: Ingestion & Extraction Engine
Develop parser abstractions for text documents and images with hash computation.

### Components & Tasks
1. **[NEW] `seekvault/ingestion/hasher.py`**
   - Implement `compute_sha256(file_path)` for binary exact hash matching.
   - Implement `compute_phash(image_path)` using perceptual hashing for visual similarity comparison.
2. **[NEW] `seekvault/ingestion/document_parser.py`**
   - Implement PyMuPDF text extractor for PDF files (page-by-page text extraction).
   - Implement `python-docx` text extractor for DOCX files.
   - Implement plain text/markdown readers.
   - Implement sliding-window text chunker (chunk size = 500 chars, overlap = 50 chars).
3. **[NEW] `seekvault/ingestion/image_parser.py`**
   - Implement Pillow image reader & metadata extractor (width, height, format, EXIF orientation).
   - Implement Tesseract OCR wrapper (`pytesseract`) to extract textual content from screenshots and scanned images.

---

## Phase 3: Privacy & Sensitivity Classification Engine
Build the 3-tier privacy decision system using Microsoft Presidio and custom Regex.

### Components & Tasks
1. **[NEW] `seekvault/privacy/presidio_scanner.py`**
   - Initialize `AnalyzerEngine` and `AnonymizerEngine`.
   - Define custom Regex recognizers for Indian PAN, Aadhaar, SSN, Passport numbers, API keys, and custom phone/email patterns.
2. **[NEW] `seekvault/privacy/sensitivity_scorer.py`**
   - Analyze detected entities and compute a sensitivity score.
   - Categorize output into:
     - `FULL`: Zero/low sensitivity.
     - `REDACTED`: Moderate sensitivity (e.g. emails, phone numbers).
     - `METADATA_ONLY`: High sensitivity (e.g. credit cards, SSNs, financial IDs).
3. **[NEW] `seekvault/privacy/anonymizer.py`**
   - Perform in-memory text redaction by replacing sensitive spans with anonymized tokens (`<EMAIL>`, `<PHONE_NUMBER>`, `<PERSON>`).

---

## Phase 4: Embedding Engine & FAISS Vector Index
Build vector generation abstractions and persistent FAISS vector indices.

### Components & Tasks
1. **[NEW] `seekvault/embeddings/text_embedder.py`**
   - Wrap `SentenceTransformer` to produce L2-normalized 384-dimensional text embeddings.
2. **[NEW] `seekvault/embeddings/visual_embedder.py`**
   - Wrap CLIP `openai/clip-vit-base-patch32` to produce L2-normalized 512-dimensional visual embeddings (image encoder) and text embeddings (text encoder).
3. **[NEW] `seekvault/embeddings/faiss_manager.py`**
   - Maintain `seekvault_text.faiss` (`IndexIDMap2(IndexFlatIP(384))`) and `seekvault_visual.faiss` (`IndexIDMap2(IndexFlatIP(512))`).
   - Implement thread-safe vector addition, vector deletion by ID (`remove_ids`), and disk persistence (`write_index`/`read_index`).

---

## Phase 5: Folder Authorization Guard & Continuous Monitoring
Implement authorization controls and real-time Watchdog file monitoring.

### Components & Tasks
1. **[NEW] `seekvault/monitoring/folder_guard.py`**
   - Path verification module that checks if a file path belongs to an active record in `authorized_folders`. Prevents path traversal vulnerabilities.
2. **[NEW] `seekvault/monitoring/watcher.py`**
   - Implement Watchdog `FileSystemEventHandler` watching active authorized folders.
   - Implement debounced event queue (1.5-second window) handling `on_created`, `on_modified`, `on_deleted`, and `on_moved`.
   - Trigger background pipeline updates upon file system events.

---

## Phase 6: Organization, Duplicate & Version Engine
Identify exact duplicates, visual duplicates, and version chains.

### Components & Tasks
1. **[NEW] `seekvault/organization/duplicate_detector.py`**
   - Match incoming SHA-256 hashes against indexed records in SQLite.
   - Compute Hamming distance between image pHashes ($\le 5$ triggers visual duplicate flag).
2. **[NEW] `seekvault/organization/version_manager.py`**
   - Perform cosine similarity search on document text chunks ($> 0.85$ similarity threshold).
   - Evaluate filename stems to group related file versions (e.g. `Thesis_v1.docx`, `Thesis_v2.docx`).
   - Automatically assign canonical status (`is_canonical = 1`) to the file with the newest modification timestamp.

---

## Phase 7: Hybrid Search & Access Verification Pipeline
Build cross-modal search retrieval, score fusion, and query-time authorization filtering.

### Components & Tasks
1. **[NEW] `seekvault/search/query_processor.py`**
   - Parse search queries. Optionally query local Ollama instance for query expansion or intent extraction.
2. **[NEW] `seekvault/search/retriever.py`**
   - Query `seekvault_text.faiss` using Sentence Transformers query vector.
   - Query `seekvault_visual.faiss` using CLIP text encoder vector.
3. **[NEW] `seekvault/search/access_verifier.py`**
   - Filter search result candidates in real time to ensure their folder path is currently authorized before presenting results.
4. **[NEW] `seekvault/search/ranker.py`**
   - Normalize and fuse vector similarity scores, deduplicate version chains, and return final ranked results with similarity percentages and privacy badges.

---

## Phase 8: Streamlit User Interface
Develop interactive multi-page web application.

### Components & Tasks
1. **[NEW] `seekvault/ui/app.py`**
   - Main entry point with sidebar navigation, system state, and global CSS styling.
2. **[NEW] `seekvault/ui/pages/1_Search.py`**
   - Multimodal search bar, query mode selector (All, Documents, Images), similarity threshold filter, and search result cards with file previews.
3. **[NEW] `seekvault/ui/pages/2_Folders.py`**
   - Folder selector, authorized directory table, toggle recursive switch, add/remove folder buttons, and manual re-index control.
4. **[NEW] `seekvault/ui/pages/3_Privacy.py`**
   - Privacy dashboard showing distribution of `FULL`, `REDACTED`, and `METADATA_ONLY` files, entity detection audit logs, and in-memory redaction inspector.
5. **[NEW] `seekvault/ui/pages/4_Duplicates.py`**
   - Duplicate file manager displaying exact duplicates, visual duplicates, version clusters, and total disk space savings.
6. **[NEW] `seekvault/ui/pages/5_Health.py`**
   - Index metrics, FAISS vector count, SQLite table statistics, Watchdog status, and log viewer.

---

## Phase 9: Verification, Benchmarking & Evaluation

### Automated Tests (`tests/`)
1. **`tests/test_parsers.py`**: Test extraction on PDF, DOCX, TXT, and image OCR.
2. **`tests/test_privacy.py`**: Test Presidio and custom Regex entity detection & redaction across synthetic datasets with sensitive identifiers.
3. **`tests/test_authorization.py`**: Validate directory traversal protection and query-time folder access filtering.
4. **`tests/test_duplicates.py`**: Verify SHA-256 matching, pHash distance, and version tree grouping.
5. **`tests/test_search.py`**: Verify text search and cross-modal image search retrieval accuracy.
6. **`tests/test_zero_touch.py`**: Assert that original files inside authorized directories are **never modified** (verify MD5/SHA-256 checksums before and after full indexing).

### Benchmarks
- **Privacy F1 Score**: Target $\ge 0.92$ on entity extraction tests.
- **Retrieval Precision@K & MRR**: Evaluate on standard query benchmark set.
- **Latency Benchmark**: Measure document parsing and embedding throughput (pages/sec, images/sec).
