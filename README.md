# SeekVault

> **Local-First, Privacy-Preserving Multimodal Semantic File Search & Organization Engine**

SeekVault is an independent, local-first personal file search engine that organizes documents, lecture notes, financial statements, and images using natural language queries without sending your private files or search terms to external clouds.

---

## 🌟 Key Features

- **Multimodal Semantic Search**: Natural language retrieval across PDFs, DOCX, TXT, and images (JPEG, PNG) using sentence transformers and CLIP cross-modal vision embeddings.
- **Sliding-Window Document Chunking**: Overlapping chunk extraction ensures deep-page content in long documents is indexed and searchable.
- **Zero-Trust Query-Time Authorization**: Enforces strict folder boundary containment with Windows path case-folding; revoked or unauthorized folders are filtered out instantly at search time.
- **Automated Privacy Tiers**:
  - `FULL`: Clean text indexed with semantic search preview.
  - `REDACTED`: PII (Aadhaar, PAN, emails, phones) detected via Presidio/regex and sanitized in previews.
  - `METADATA_ONLY`: Passwords and confidential secrets indexed solely by filename and metadata without vector leakage.
- **Exact Duplicate & Version Detection**: SHA-256 cryptographic clustering for duplicates; semantic similarity and filename heuristics for document version trees.
- **Streamlit Interactive UI**: 6 focused modules: Search, My Files, Indexing Status, Privacy, Duplicates, and Settings.

---

## 🏗️ Project Architecture

```
SeekVault/
├── .gitignore
├── README.md
├── Launch_SeekVault.bat                  # Root desktop wrapper launcher
├── Launch_SeekVault_Silent.vbs          # Silent background launcher
├── Create_Desktop_Shortcut.ps1          # Windows desktop shortcut generator
├── DESKTOP_DEPLOYMENT_GUIDE.md          # Windows desktop deployment guide
└── SeekVault Prototype/
    ├── app.py                             # Streamlit main application entry point
    ├── run_seekvault.bat                  # One-click Windows batch launcher
    ├── run_seekvault.ps1                  # One-click PowerShell launcher
    ├── download_models.py                 # Offline model pre-fetch utility
    ├── requirements.txt                   # Production package dependencies (pinned)
    ├── requirements-dev.txt               # Development & test dependencies (pytest, etc.)
    ├── run_demo.py                        # Automated demo initialization
    ├── verify_e2e.py                      # 8-point isolated end-to-end verification
    ├── ARCHITECTURE.md                    # Detailed system design
    ├── IMPLEMENTATION_PLAN.md             # Implementation specifications
    ├── WALKTHROUGH.md                     # Guided walkthrough
    ├── evaluation/                        # Retrieval & privacy evaluation benchmark
    │   ├── benchmark.py                   # Latency, MRR, P@K, Presidio F1 evaluator
    │   ├── eval_dataset.py                # Labeled ground truth queries & PII samples
    │   └── BENCHMARK_REPORT.md            # Hardware, latency & F1 metric report
    ├── seekvault/                         # Core Python package
    │   ├── config.py                      # Global paths & hyperparameter constants
    │   ├── database/                      # SQLite schema, connection, repository, backup
    │   ├── extraction/                    # PDF, DOCX, TXT, image & OCR extraction
    │   ├── privacy/                       # Analyzer, custom regex, classifier & sanitizer
    │   ├── embeddings/                    # Text & image embedding managers (MiniLM, CLIP)
    │   ├── search/                        # FAISS vector indices, engine & access verifier
    │   ├── monitoring/                    # Watchdog folder synchronization
    │   ├── organization/                  # Duplicate & version detectors
    │   ├── ingestion/                     # Ingestion pipeline coordinator
    │   └── ui/                            # Streamlit page modules & components
    ├── sample_data/                       # Sample test fixtures & generator script
    └── tests/                             # 20 automated pytest test suites (119 tests)
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+ (Python 3.11 recommended)
- Tesseract OCR (optional, for image text OCR)

### 2. Install Dependencies
```bash
cd "SeekVault Prototype"
pip install -r requirements.txt
pip install -r requirements-dev.txt     # for testing & evaluation
python download_models.py               # pre-fetch offline models
```

### 3. Run End-to-End Verification
```bash
python verify_e2e.py
```

### 4. Run Automated Test Suite
```bash
pytest tests/ -v                        # 119 tests passing
```

### 5. Launch Application
```bash
.\run_seekvault.bat                     # or: streamlit run app.py
```

---

## 🛡️ License

Independent Open-Source Software. Developed for local-first privacy research and high-performance desktop search.