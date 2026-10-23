# SeekVault: Prototype Implementation Plan

## 1. Project Directory Structure

```
SeekVault Prototype/
├── ARCHITECTURE.md                  # Detailed system architecture & design
├── IMPLEMENTATION_PLAN.md           # Implementation blueprint and demo guide
├── app.py                           # Streamlit main entry point
├── requirements.txt                 # Project dependencies
├── run_demo.py                      # One-click demo initialization script
├── seekvault/                       # Core modular application package
│   ├── __init__.py
│   ├── config.py                    # Global paths, constants, and hyperparameters
│   ├── database/                    # SQLite database layer
│   │   ├── __init__.py
│   │   ├── connection.py            # SQLite thread-safe connection manager
│   │   ├── schema.py                # Table schemas, migrations, and DDL
│   │   └── repository.py            # CRUD operations for folders, files, PII, vectors
│   ├── extraction/                  # Multimodal content extraction
│   │   ├── __init__.py
│   │   ├── text_extractor.py        # PDF (PyMuPDF), DOCX (python-docx), TXT
│   │   ├── image_extractor.py       # Pillow-based metadata, dimensions, EXIF
│   │   └── ocr_extractor.py         # Tesseract OCR extraction with graceful fallback
│   ├── privacy/                     # Privacy detection & tiered indexing
│   │   ├── __init__.py
│   │   ├── recognizers.py           # Custom Regex (Aadhaar, Phone, PAN, ID, Credit Card)
│   │   ├── analyzer.py              # Presidio Analyzer integration + entity detection
│   │   ├── sanitizer.py             # Redaction / placeholder substitution engine
│   │   └── classifier.py            # Tier classification (FULL, REDACTED, METADATA_ONLY)
│   ├── embeddings/                  # Semantic embedding models
│   │   ├── __init__.py
│   │   ├── text_embedder.py         # Sentence-Transformers (all-MiniLM-L6-v2)
│   │   ├── image_embedder.py        # CLIP (clip-ViT-B-32) cross-modal embedder
│   │   └── manager.py               # Singleton lazy-loader for AI models
│   ├── search/                      # FAISS vector storage & retrieval
│   │   ├── __init__.py
│   │   ├── faiss_index.py           # FAISS IndexFlatIP wrapper for save/load/search
│   │   ├── engine.py                # Unified multimodal query processor & ranker
│   │   └── verifier.py              # Query-time folder authorization & access verifier
│   ├── monitoring/                  # Continuous folder synchronization
│   │   ├── __init__.py
│   │   ├── handler.py               # Watchdog event handler (Create, Modify, Delete, Move)
│   │   └── watcher.py               # Background observer lifecycle manager
│   ├── organization/                # Deduplication and version tracking
│   │   ├── __init__.py
│   │   ├── duplicate_detector.py    # SHA-256 cryptographic hash collision clusterer
│   │   └── version_detector.py      # Embedding cosine similarity + name heuristic versioner
│   ├── ingestion/                   # End-to-end pipeline coordinator
│   │   ├── __init__.py
│   │   └── pipeline.py              # Ingestion flow: Discovery -> Extract -> Privacy -> Embed -> Index
│   └── ui/                          # Streamlit UI modules
│       ├── __init__.py
│       ├── components.py            # Reusable UI widgets, badges, cards, metrics
│       └── pages/
│           ├── search.py            # Cross-modal search with preview, filters, and scores
│           ├── file_library.py      # My Files: Authorized folders & indexed file inventory
│           ├── system_health.py     # Indexing Status: telemetry, health, watchdog status
│           ├── privacy_center.py    # Privacy: tier breakdown, PII audit, zero raw PII view
│           ├── duplicates_versions.py # Duplicates: duplicate clusters and version trees
│           └── settings.py          # Settings: model paths, offline verification, maintenance
├── sample_data/                     # Curated realistic test files for college demo
│   ├── authorized_academic/         # Standard academic notes (Machine Learning, DBMS)
│   ├── authorized_personal/         # Sensitive documents (contains phone, email, Aadhaar)
│   ├── authorized_images/           # Images (red car, classroom, Java code screenshot)
│   ├── authorized_versions/         # Versions of report (Report_Draft_v1.docx, Report_Final.docx)
│   └── unauthorized_folder/         # Folder outside whitelist to test access rejection
└── tests/                           # Automated validation suite
    ├── test_database.py
    ├── test_extraction.py
    ├── test_privacy.py
    ├── test_embeddings.py
    ├── test_search.py
    ├── test_access_verification.py
    └── test_organization.py
```

---

## 2. Feature-by-Feature Demonstration Strategy

Here is exactly how every requested feature will be demonstrated during a live evaluation:

### Feature 1: Folder Authorization
* **Demonstration Mechanism**:
  * In the **Authorized Folders** UI, the user adds `sample_data/authorized_academic` and `sample_data/authorized_personal`.
  * The system validates the path, saves it to the SQLite `authorized_folders` table, and triggers ingestion.
  * To demonstrate exclusion, the user places a sensitive file in `sample_data/unauthorized_folder`. SeekVault ignores it completely.
  * Removing a folder in the UI immediately deactivates it.

### Feature 2: Multimodal File Processing & Text/OCR Extraction
* **Demonstration Mechanism**:
  * Supports `.pdf`, `.docx`, `.txt`, `.jpg`, `.jpeg`, `.png`.
  * A PDF (`ML_Unit3_Notes.pdf`) is parsed using `PyMuPDF`.
  * A DOCX (`Project_Proposal.docx`) is parsed using `python-docx`.
  * An image containing text (`java_error_screenshot.png`) is processed using `Pillow` and `pytesseract` to extract the terminal error message.
  * The UI **Indexed Files** tab displays extracted character count, word count, and extracted text preview.

### Feature 3: Privacy Detection & Tiered Indexing (`FULL`, `REDACTED`, `METADATA_ONLY`)
* **Demonstration Mechanism**:
  * Ingest a clean academic paper: Classified as **`FULL`**. Vector embedding reflects 100% of raw content.
  * Ingest a student application form with email (`arohikar@example.com`), phone number (`+91 9876543210`), and an Aadhaar/PAN ID:
    * Presidio + Custom Regex flags sensitive tokens.
    * Classified as **`REDACTED`**.
    * The original file on disk is completely untouched.
    * In SQLite, the search representation shows `Contact: <EMAIL>, Phone: <PHONE_NUMBER>, ID: <ID_NUM>`.
    * Sentence Transformer embeds the *redacted* string into FAISS.
  * Ingest an extreme/confidential file (e.g. `Confidential_Passwords.txt`):
    * Classified as **`METADATA_ONLY`**.
    * Zero content vectors are inserted into FAISS. The search only matches its filename/metadata.
  * In the **Privacy Center** UI, a visual breakdown displays detected entity counts (Emails, Phones, Names, IDs).

### Feature 4: Text Semantic Search
* **Demonstration Mechanism**:
  * The user inputs conceptual queries that do **not** appear as verbatim keywords or filenames:
    * Query: *"notes about candidate elimination"* $\to$ Retrieves `ML_Unit3.pdf` with top similarity score (e.g., 0.82), even though the file is named `ML_Unit3.pdf`.
    * Query: *"database normalization"* $\to$ Retrieves `DBMS_Lecture_4.docx`.
    * Query: *"Java exception notes"* $\to$ Retrieves documents and code snippets referencing `NullPointerException` and `try-catch`.
  * Vector search runs via FAISS Inner Product on normalized embeddings, displaying ranked results with similarity scores (0.0 to 1.0).

### Feature 5: Image Semantic Search (Cross-Modal Text-to-Image)
* **Demonstration Mechanism**:
  * The user switches search tab or chooses Multimodal/Image search.
  * Query: *"red car near a building"* $\to$ Converts text to CLIP vector $\to$ FAISS searches image embeddings $\to$ returns `car_parked.jpg` with high similarity!
  * Query: *"screenshot containing Java error"* $\to$ Returns `java_error_screenshot.png`.
  * Query: *"photo of a classroom"* $\to$ Returns `lecture_hall.jpg`.
  * Streamlit displays rich image thumbnails, dimensions, and visual metadata directly in the search cards.

### Feature 6: Image Analysis & Metadata
* **Demonstration Mechanism**:
  * Displays resolution, format, color space, aspect ratio, EXIF data (if present), and OCR text detected inside the image.
  * Ollama integration check: If Ollama is running locally with `llava` or `moondream`, it queries local endpoint for automated captioning; if Ollama is absent, it seamlessly falls back to visual metadata + OCR keywords without throwing errors or requiring any cloud API.

### Feature 7: Continuous Monitoring (Watchdog)
* **Demonstration Mechanism**:
  * The **Indexing Status** page shows an active green badge: `"Watchdog: Active"`.
  * During the live demo, a new file `Live_Demo_Notes.txt` is copied into `authorized_academic/`.
  * Within 1-2 seconds, Watchdog detects the event, debounces, processes the file, updates SQLite, and adds it to the FAISS index automatically.
  * Search immediately finds the new file without restarting the app.
  * Deleting a file removes it from active search.

### Feature 8: Query-Time Access Verification
* **Demonstration Mechanism**:
  * Suppose `Personal_Doc.pdf` was indexed while `sample_data/authorized_personal` was authorized.
  * The user goes to **My Files** and deauthorizes/toggles `sample_data/authorized_personal`.
  * The user immediately runs a search query that would have matched `Personal_Doc.pdf`.
  * **Result**: `Personal_Doc.pdf` is strictly **NOT** returned!
  * The query verifier confirms that even though the vector may technically linger in FAISS, zero-trust verification suppresses any file whose current folder is unauthorized or whose file was deleted.

### Feature 9: Exact Duplicate Detection
* **Demonstration Mechanism**:
  * Two identical files with different filenames (e.g., `ML_Unit3.pdf` and `ML_Copy_Final.pdf`) are in authorized folders.
  * The SHA-256 hash engine groups them in the **Duplicates** tab:
    * Displays duplicate clusters, individual paths, and redundant disk storage footprint.

### Feature 10: Document Version Detection
* **Demonstration Mechanism**:
  * Ingest `Research_Paper_Draft_v1.docx` and `Research_Paper_Draft_v2.docx` (which has 85-95% semantic similarity and similar base names).
  * The version detector identifies them as sequential versions of the same document based on high cosine similarity and temporal timestamps.
  * The UI presents a clean visual version tree showing the evolution of the document.

### Feature 11: SQLite Database
* **Demonstration Mechanism**:
  * All authorized folders, files, hashes, privacy classifications, indexing status, detected entities, and FAISS vector mappings are cleanly organized in a local `seekvault.db` file.
  * Can be inspected directly or viewed via the **My Files** tab.

### Feature 12: Streamlit User Interface
* **Demonstration Mechanism**:
  * Clean, polished sidebar navigation across 6 dedicated views:
    * 🔍 **Search**: Unified search bar, modality filters (All / Documents / Images), privacy filter, result cards with score bars and previews.
    * 📁 **My Files**: Folder authorization manager, recursive flags, add/delete controls, safe file inventory.
    * 📊 **Indexing Status**: System health telemetry, KPI stat cards, background watchdog activity pill.
    * 🛡️ **Privacy**: Visual breakdown of privacy tiers, table of detected PII per file, zero raw PII display.
    * 👥 **Duplicates**: Grouped expandable cards for duplicates and version chains.
    * ⚙️ **Settings**: Model paths, offline verification, backup and factory reset controls.

---

## 3. Step-by-Step Implementation Strategy

1. **Step 1: Configuration & Database Foundation**
   * Implement `config.py` with default paths, model weights, and constants.
   * Implement SQLite schema in `database/schema.py` and connection manager in `database/connection.py`.
   * Implement `database/repository.py` with complete CRUD operations.

2. **Step 2: Multimodal Extraction Engine**
   * Implement `extraction/text_extractor.py` for PDF, DOCX, TXT.
   * Implement `extraction/image_extractor.py` for Pillow metadata.
   * Implement `extraction/ocr_extractor.py` for Tesseract OCR with resilient fallback.

3. **Step 3: Privacy Engine & Tier Classifier**
   * Implement `privacy/recognizers.py` for custom regex patterns (Aadhaar, PAN, phone numbers).
   * Implement `privacy/analyzer.py` wrapping Presidio Analyzer.
   * Implement `privacy/sanitizer.py` for placeholder replacement.
   * Implement `privacy/classifier.py` for `FULL`, `REDACTED`, `METADATA_ONLY` classification.

4. **Step 4: Semantic Embeddings & FAISS Indexing**
   * Implement `embeddings/text_embedder.py` using `all-MiniLM-L6-v2`.
   * Implement `embeddings/image_embedder.py` using `clip-ViT-B-32`.
   * Implement `search/faiss_index.py` wrapping FAISS IndexFlatIP.
   * Implement `search/engine.py` for text and image semantic search.
   * Implement `search/verifier.py` for query-time access verification.

5. **Step 5: Organization (Duplicate & Version Detection)**
   * Implement `organization/duplicate_detector.py` using SHA-256 hashes.
   * Implement `organization/version_detector.py` using embedding similarity.

6. **Step 6: Continuous Monitoring**
   * Implement `monitoring/handler.py` and `monitoring/watcher.py` using Watchdog.
   * Implement background debounced file-event processing.

7. **Step 7: Ingestion Pipeline Orchestrator**
   * Implement `ingestion/pipeline.py` linking discovery, extraction, privacy, embedding, and indexing.

8. **Step 8: Streamlit Frontend**
   * Implement `seekvault/ui/components.py` for UI styling, badges, and cards.
   * Implement pages: Search, My Files, Indexing Status, Privacy, Duplicates, Settings.
   * Implement root `app.py`.

9. **Step 9: Sample Data & Comprehensive Automated Test Suite**
   * Generate realistic sample files (PDFs, DOCX, TXT, images with text, versions, duplicates).
   * Write and run tests for all core modules (`pytest tests/`).

10. **Step 10: Verification & Demo Script**
    * Create `run_demo.py` for effortless one-command execution and college demonstration.
