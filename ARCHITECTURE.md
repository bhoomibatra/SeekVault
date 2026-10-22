# SeekVault System Architecture Specification

## 1. System Architecture Overview

SeekVault is a local-first, privacy-preserving multimodal semantic file search and organization engine for personal and academic files. It enables natural language searching across documents (PDF, DOCX, TXT, MD) and images (PNG, JPG, BMP, WEBP, screenshots, scans) using deep semantic embeddings without relying on external cloud APIs or sending user data outside the local machine.

### Key Architecture Principles
- **Local-First Boundary**: All parsing, optical character recognition (OCR), sensitivity screening, embedding generation, vector indexing, metadata storage, and optional LLM/VLM processing execute 100% locally on the host machine.
- **Strict File Non-Mutation (Zero-Touch Original File Policy)**: Original user files inside authorized directories are **never** altered, modified, appended to, or relocated by SeekVault. All privacy enforcement (redaction, masking, metadata-only tiering) is applied **in-memory** to derived text/features before vector creation or database insertion.
- **Folder-Scoped Authorization**: SeekVault operates strictly on folders explicitly white-listed by the user. Un-authorized directories are completely invisible to the indexing pipeline, the continuous monitoring subsystem, and query results.
- **Multi-Tiered Privacy-Aware Indexing**: Each file is dynamically evaluated using Microsoft Presidio and custom Regex heuristics to assign one of three privacy tiers:
  1. `FULL`: Low/zero sensitivity; raw extracted text embedded and indexed.
  2. `REDACTED`: Moderate sensitivity (e.g. contain emails, phone numbers, names); sensitive entities are replaced with placeholders in memory, and only anonymized text is embedded and stored.
  3. `METADATA_ONLY`: High sensitivity (e.g., financial cards, national IDs, security credentials); no text or visual embeddings are generated; only non-content file metadata (path, file size, format, modified time) is stored in SQLite.
- **Dual Vector Space Engine**: Utilizes Sentence Transformers for high-density document text retrieval and CLIP/SigLIP for joint image-text cross-modal retrieval (e.g., searching for "photo of red car near building" returns visual image matches).

```
 +-----------------------------------------------------------------------------------+
 |                              LOCAL USER DEVICE BOUNDARY                           |
 |                                                                                   |
 |  +--------------------+       +-------------------------------------------------+ |
 |  | Authorized Folders | ----> | Watchdog Monitoring Subsystem                   | |
 |  | (PDF, DOCX, IMG)   |       | (Detects Create, Modify, Delete, Move Events)   | |
 |  +--------------------+       +-------------------------------------------------+ |
 |            |                                           |                          |
 |            v                                           v                          |
 |  +------------------------------------------------------------------------------+ |
 |  | Text & Image Ingestion Pipeline                                             | |
 |  | (PyMuPDF, python-docx, Pillow, Tesseract OCR)                               | |
 |  +------------------------------------------------------------------------------+ |
 |                                        |                                          |
 |                                        v                                          |
 |  +------------------------------------------------------------------------------+ |
 |  | Privacy Classification & Redaction Engine                                   | |
 |  | (Microsoft Presidio + Custom Regex -> Sensitivity Scorer -> Tier Assignment) | |
 |  +------------------------------------------------------------------------------+ |
 |            |                                   |                               |
 |      [FULL / REDACTED]                  [METADATA_ONLY]                           |
 |            |                                   |                               |
 |            v                                   v                               |
 |  +-------------------+               +---------------------------------------+ |
 |  | Embedding Engine  |               | Metadata Persistence                  | |
 |  | (SentenceTransformers             | (File attributes, privacy logs, hashes| |
 |  |  & CLIP/SigLIP)   |               |  saved to SQLite)                     | |
 |  +-------------------+               +---------------------------------------+ |
 |            |                                   ^                               |
 |            v                                   |                               |
 |  +-------------------+                         |                               |
 |  | FAISS Vector Store| ------------------------+                               |
 |  | (Text & Visual    |                                                         |
 |  |  Indices)         |                                                         |
 |  +-------------------+                                                         |
 |            ^                                                                   |
 |            |                                                                   |
 |  +------------------------------------------------------------------------------+ |
 |  | Streamlit UI & Search Engine                                                 | |
 |  | (Query parser, Dual Retrieval, Access Guard, Duplicate/Version Manager)     | |
 |  +------------------------------------------------------------------------------+ |
 +-----------------------------------------------------------------------------------+
```

---

## 2. Technology Stack Alignment

| Layer / Domain | Technology Choice | Architectural Purpose & Rationale |
| :--- | :--- | :--- |
| **User Interface** | **Streamlit** | Desktop-grade local web UI providing interactive folder management, real-time index stats, privacy audit tables, visual search results, and duplicate management. |
| **Document Processing** | **PyMuPDF (`fitz`)**, **`python-docx`** | Fast, zero-overhead local extraction of text and metadata from PDF files (`fitz`) and Word documents (`python-docx`). |
| **Image & OCR Engine** | **Pillow (`PIL`)**, **Tesseract OCR (`pytesseract`)** | Image ingestion, resizing, format conversion (Pillow) and offline text extraction from screenshots, scanned documents, and infographics (Tesseract). |
| **Text Semantic Embeddings** | **Sentence Transformers** (`all-MiniLM-L6-v2` / `all-mpnet-base-v2`) | Generates dense 384d / 768d text embeddings for document chunks and user search queries. |
| **Cross-Modal Embeddings** | **CLIP / SigLIP** (`openai/clip-vit-base-patch32` or `google/siglip-base-patch16-224`) | Produces joint text-image embedding spaces enabling natural language text queries against raw visual content. |
| **Privacy & PII Detection** | **Microsoft Presidio** (`presidio-analyzer`, `presidio-anonymizer`) + **Custom Regex** | In-memory detection of sensitive entities (names, emails, phone numbers, SSNs, credit cards) and rule-based redaction prior to embedding. |
| **File System Watcher** | **Watchdog** | Background event driven watcher that observes authorized folder trees and emits events on file creation, modification, deletion, or rename/move. |
| **Vector Indexing** | **FAISS (`faiss-cpu`)** | Ultra-fast local similarity search and vector indexing using L2 or Inner Product (Cosine) similarity search. |
| **Relational Metadata Store**| **SQLite 3** | File system state, index mapping, hash lookup tables, version linkage, privacy audit logs, and folder authorization rules stored in a local `.db` file. |
| **Optional LLM/VLM** | **Ollama** (Local `llama3` / `llava`) | Optional local processing for query understanding, image auto-captioning, and search result synthesis without sending data externally. |

---

## 3. Module Breakdown

The codebase is organized modularly under `seekvault/`:

```
seekvault/
│
├── config.py                   # Central configuration (paths, model names, threshold constants)
├── core/
│   ├── logger.py               # Application-wide structured logging setup
│   └── database.py             # SQLite connection pooling, schema initialization, transactional helper functions
│
├── ingestion/
│   ├── document_parser.py      # Extract text & metadata from PDF, DOCX, TXT, MD
│   ├── image_parser.py         # Image metadata extraction, resizing, Tesseract OCR wrapper
│   └── hasher.py               # SHA-256 calculation & Image pHash calculation
│
├── privacy/
│   ├── presidio_scanner.py     # Microsoft Presidio Analyzer wrapper + custom regex patterns
│   ├── sensitivity_scorer.py   # Privacy classification decision engine (FULL, REDACTED, METADATA_ONLY)
│   └── anonymizer.py           # In-memory text masking & placeholder insertion
│
├── embeddings/
│   ├── text_embedder.py        # SentenceTransformers wrapper for text chunks & queries
│   ├── visual_embedder.py      # CLIP/SigLIP wrapper for image pixels & text queries
│   └── faiss_manager.py        # FAISS index setup, vector addition/deletion, disk persistence
│
├── monitoring/
│   ├── folder_guard.py         # Path validation, authorized folder registry, permission checker
│   └── watcher.py              # Watchdog event handler and debounced index updater thread
│
├── search/
│   ├── query_processor.py      # Natural language query parsing, optional Ollama expansion
│   ├── retriever.py            # Vector retrieval from FAISS text and visual indices
│   ├── ranker.py               # Score normalization, fusion ranking, threshold filtering
│   └── access_verifier.py      # Query-time folder authorization filter
│
├── organization/
│   ├── duplicate_detector.py   # Exact hash matching & perceptual hash Hamming distance calculation
│   └── version_manager.py      # Near-duplicate text detection & version chain tree builder
│
└── ui/
    ├── app.py                  # Main Streamlit application entry point
    ├── components/             # Reusable UI widgets (cards, file previewers, privacy badges)
    └── pages/                  # Streamlit view pages (Search, Folders, Privacy, Duplicates, Health)
```

---

## 4. System Data Flow

```
                           +------------------------+
                           |  Authorized File Path  |
                           +------------------------+
                                       |
                                       v
                        +------------------------------+
                        |  Hasher (SHA-256 & pHash)   |
                        +------------------------------+
                                       |
                   +-------------------+-------------------+
                   |                                       |
        [Document: PDF/DOCX/TXT]                    [Image: PNG/JPG]
                   |                                       |
                   v                                       v
       +-----------------------+               +-----------------------+
       | PyMuPDF / docx Parser |               | Pillow + Tesseract    |
       | Extract Raw Text      |               | Extract OCR & Pixels  |
       +-----------------------+               +-----------------------+
                   |                                       |
                   +-------------------+-------------------+
                                       |
                                       v
                   +---------------------------------------+
                   |  Presidio + Regex Sensitivity Scan    |
                   +---------------------------------------+
                                       |
               +-----------------------+-----------------------+
               |                       |                       |
        (Sensitivity = Low)   (Sensitivity = Med)     (Sensitivity = High)
               |                       |                       |
               v                       v                       v
          [Tier: FULL]          [Tier: REDACTED]     [Tier: METADATA_ONLY]
               |                       |                       |
         Raw Text embedded     Redacted Text embedded   No content embedded
               |                       |                       |
               +-----------------------+                       |
                           |                                   |
                           v                                   v
             +---------------------------+           +------------------+
             | SentenceTransformers/CLIP |           | Record Metadata  |
             | Vector Embeddings         |           | Only in SQLite   |
             +---------------------------+           +------------------+
                           |                                   ^
                           v                                   |
             +---------------------------+                     |
             | FAISS Index (Text/Visual) |                     |
             | Map ID to SQLite Record   | --------------------+
             +---------------------------+
```

---

## 5. Privacy Classification Workflow

SeekVault enforces a 3-tier privacy classification model to guarantee privacy without sacrificing search utility.

```
                        +----------------------------+
                        | Extracted Text / OCR Text  |
                        +----------------------------+
                                      |
                                      v
                        +----------------------------+
                        | Presidio Entity Detection  |
                        | + Custom Regex Matching    |
                        +----------------------------+
                                      |
                                      v
                        +----------------------------+
                        | Compute Sensitivity Score  |
                        +----------------------------+
                                      |
         +----------------------------+----------------------------+
         |                            |                            |
  [Score == 0]            [0 < Score <= Threshold]        [Score > Threshold OR
         |                            |                   Critical PII Detected]
         v                            v                            v
  +--------------+            +-----------------+          +-----------------------+
  | Tier 1: FULL |            | Tier 2: REDACTED|          | Tier 3: METADATA_ONLY |
  +--------------+            +-----------------+          +-----------------------+
  | - Raw text   |            | - Replace PII   |          | - Store file metadata |
  |   embedded   |            |   in-memory     |          |   in SQLite           |
  | - Full text  |            |   with tokens   |          | - Skip text & visual  |
  |   indexed    |            | - Embed anonym- |          |   vector embeddings   |
  +--------------+            |   ized text     |          | - File title searchable|
                              +-----------------+          +-----------------------+
```

### Classification Rules & Entities
1. **Critical Entities (Forces `METADATA_ONLY`)**:
   - Credit Card / Bank Account Numbers
   - National Identification Numbers (SSN, Passport, Aadhaar, PAN)
   - Password / Private Key strings
2. **Moderate Entities (Triggers `REDACTED`)**:
   - Email Addresses
   - Phone Numbers
   - Individual Person Names
   - Physical Addresses / Locations
   - Date of Birth
3. **In-Memory Redaction Execution**:
   - Original file on disk is untouched.
   - Text extracted in memory is passed to `presidio-anonymizer`.
   - Sensitive tokens are replaced with `<EMAIL>`, `<PHONE_NUMBER>`, `<PERSON>`.
   - The anonymized text is passed to Sentence Transformers / CLIP.

---

## 6. Document Processing Workflow

```
[Start Document Ingestion]
           |
           v
[Verify Folder Authorization (FolderGuard)]
           |  (Authorized)
           v
[Compute SHA-256 Hash] ---> [Check SQLite for Existing SHA-256]
                                      |
                    +-----------------+-----------------+
                    |                                   |
             (Hash Exists)                       (New/Modified File)
                    |                                   |
                    v                                   v
       [Flag as Duplicate / Version]         [Extract Text & Metadata]
                                             (PyMuPDF / python-docx / txt)
                                                        |
                                                        v
                                             [Chunk Text into Passages]
                                             (Sliding Window: 500 chars, 50 overlap)
                                                        |
                                                        v
                                             [Run Privacy Classification]
                                             (Full / Redacted / Metadata-Only)
                                                        |
                                                        v
                                             [Generate Embeddings for Chunks]
                                             (Sentence Transformers)
                                                        |
                                                        v
                                             [Write DB Record & FAISS Vectors]
```

---

## 7. Image Processing Workflow

```
[Start Image Ingestion]
           |
           v
[Verify Folder Authorization (FolderGuard)]
           |
           v
[Load Image via Pillow] ---> [Extract EXIF Metadata & Compute SHA-256 + pHash]
                                      |
                                      v
                             [Run Tesseract OCR]
                                      |
                  +-------------------+-------------------+
                  |                                       |
           (Text Detected)                         (No Text Found)
                  |                                       |
                  v                                       v
    [Privacy Scan on OCR Text]             [Generate Visual Embedding]
                  |                        (CLIP / SigLIP Image Encoder)
      +-----------+-----------+                           |
      |                       |                           |
[FULL/REDACTED]        [METADATA_ONLY]                    |
      |                       |                           |
      v                       v                           |
[Generate Visual       [Store Metadata                    |
 & Text Embeddings]    Only in SQLite]                    |
      |                       |                           |
      +-----------+-----------+                           |
                  |                                       |
                  v                                       v
      [Insert into SQLite DB & FAISS Image Index] <-------+
```

---

## 8. Search and Ranking Workflow

```
[User Enters Natural Language Query]
                 |
                 v
[Query Preprocessing & Optional Ollama Expansion]
                 |
                 v
   +-------------+-------------+
   |                           |
   v                           v
[SentenceTransformers]     [CLIP Text Encoder]
(Generate Text Query Vector)(Generate Cross-Modal Vector)
   |                           |
   v                           v
[FAISS Text Index Search]   [FAISS Visual Index Search]
(Top-K Document Chunks)     (Top-K Visual Images)
   |                           |
   +-------------+-------------+
                 |
                 v
[Combine & Normalize Similarity Scores (Cosine Similarity)]
                 |
                 v
[Folder Access Verification (Query-Time Access Guard)]
(Filter out results whose file paths are no longer authorized)
                 |
                 v
[Group Duplicates & Collapse Version Chains]
(Present Canonical file with version dropdown)
                 |
                 v
[Return Ranked Result List to Streamlit UI]
```

---

## 9. Duplicate & Version Detection Design

SeekVault implements a multi-stage approach to manage file redundancies:

```
                      +-----------------------------+
                      |       Incoming File         |
                      +-----------------------------+
                                     |
                                     v
                      +-----------------------------+
                      | Exact Hash Match (SHA-256)   |
                      +-----------------------------+
                                     |
                      +--------------+--------------+
                      |                             |
               (Match Found)                 (No Exact Match)
                      |                             |
                      v                             v
           [Flag Exact Duplicate]       +------------------------+
           (Link to existing        | Media Type Check       |
            canonical ID)           +------------------------+
                                                    |
                                    +---------------+---------------+
                                    |                               |
                               [Document]                        [Image]
                                    |                               |
                                    v                               v
                      +---------------------------+   +---------------------------+
                      | Text Similarity (Cosine)  |   | Visual pHash Hamming Dist |
                      | Threshold > 0.85          |   | Distance <= 5             |
                      +---------------------------+   +---------------------------+
                                    |                               |
                                    +---------------+---------------+
                                                    |
                                                    v
                                    +-------------------------------+
                                    | Near-Duplicate / Version Tree |
                                    | Set canonical = newer modtime |
                                    +-------------------------------+
```

1. **Exact Duplicate Detection**:
   - SHA-256 binary hash comparison during ingestion.
   - If an identical SHA-256 hash exists in SQLite, the new file is registered as an `exact_duplicate` of the canonical file. Processing stops before embedding generation to save compute resources.
2. **Visual Image Duplicate Detection**:
   - Perceptual Hash (pHash) generated for image files.
   - Hamming distance between pHashes is checked. If distance $\le 5$, the image is classified as a visual near-duplicate.
3. **Document Versioning & Near-Duplicates**:
   - Document chunks are evaluated against indexed documents using Cosine Similarity on Sentence Transformer embeddings.
   - If document text similarity $> 0.85$ and filenames share a root stem (e.g., `Report_v1.docx` and `Report_v2.docx`), SeekVault groups them into a single `version_group`.
   - The file with the latest modification timestamp is assigned as the `is_canonical` file.

---

## 10. Folder Authorization & Access Verification Design

Security and privacy require strict folder isolation:

1. **User Authorization Flow**:
   - The user explicitly registers authorized folder paths via the Streamlit interface.
   - Paths are validated using `os.path.realpath` to resolve symlinks and prevent directory traversal attacks.
   - Authorized root paths are stored in the SQLite `authorized_folders` table.
2. **Ingestion & Monitoring Scope**:
   - Watchdog monitors **only** active authorized folder paths.
   - Any file outside authorized boundaries is rejected immediately at the `FolderGuard` level.
3. **Query-Time Access Guard (Double Verification)**:
   - When a search is performed, FAISS returns candidate result IDs.
   - Before returning candidate files to the Streamlit UI, `AccessVerifier` checks every candidate file path against the currently active `authorized_folders` list.
   - If a folder was revoked/de-authorized by the user after indexing, its files are filtered out of search results **in real-time** without requiring index deletion.

---

## 11. Continuous File Monitoring Design

SeekVault keeps its index synchronized with the file system using Python `watchdog`:

```
+-------------------------------------------------------------------------------+
|                             WATCHDOG OBSERVER THREAD                          |
|                                                                               |
|  [File Created]     [File Modified]     [File Deleted]      [File Moved]      |
|        |                   |                  |                  |            |
|        v                   v                  v                  v            |
|  +-------------------------------------------------------------------------+  |
|  |                    Debounced Event Queue (1.5s delay)                  |  |
|  +-------------------------------------------------------------------------+  |
+------------------------------------+------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------------+
|                           BACKGROUND EVENT WORKER                             |
|                                                                               |
|   - ON CREATED  : Run full ingestion pipeline -> update SQLite & FAISS        |
|   - ON MODIFIED : Remove old FAISS vectors -> re-run ingestion -> update DB   |
|   - ON DELETED  : Soft-delete in SQLite (`indexing_status = DELETED`) & FAISS |
|   - ON MOVED    : Update file_path in SQLite DB without re-embedding         |
+-------------------------------------------------------------------------------+
```

- **Debounce Strategy**: File write operations (e.g. saving a PDF) often fire multiple OS events. The `watchdog` handler uses a 1.5-second debounce window per file path to prevent duplicate redundant processing.

---

## 12. Streamlit UI Structure

The UI is built with Streamlit and organized into 5 primary modules:

1. **Sidebar Navigation**:
   - System Status Indicator (Index count, Active Watchers, Ollama Status).
   - Mode Selector:
     - 🔍 **Search & Explore** (Multimodal natural language search bar, image search, similarity threshold slider, result cards).
     - 📂 **Authorized Folders** (Folder browser, add/remove authorized directories, force re-index button).
     - 🛡️ **Privacy & Audit** (Privacy tier distribution metrics, entity detection logs, redacted preview inspector).
     - 🔗 **Duplicates & Versions** (Duplicate clusters, version history tree, space recovery metrics).
     - ⚙️ **System Health** (FAISS index stats, SQLite database stats, log viewer).

---

## 13. Testing Strategy

1. **Unit Testing (`pytest`)**:
   - **Parsers**: Test PyMuPDF, python-docx, Pillow, and Tesseract wrappers with sample files.
   - **Privacy Engine**: Verify Presidio entity detection and redaction accuracy across test text strings containing emails, phone numbers, SSNs, and credit cards.
   - **Hashing & Similarity**: Test SHA-256, pHash Hamming distance, and cosine distance math.
   - **Access Guard**: Verify path validation logic and directory traversal protection.
2. **Integration Testing**:
   - End-to-end test from folder monitoring -> file addition -> privacy scan -> embedding -> FAISS retrieval -> UI rendering.
   - Verification that original test files retain their original MD5/SHA-256 hashes on disk (Zero-Touch Verification).
3. **Evaluation Benchmarks**:
   - **Privacy Detection F1-Score**: Target $\ge 0.92$ on standard PII test samples.
   - **Search Quality**: Evaluate Precision@K, Recall@K, and MRR (Mean Reciprocal Rank) on a sample dataset of 100 queries.
   - **Indexing Latency**: Measure throughput (files/sec and pages/sec) across documents and images.
