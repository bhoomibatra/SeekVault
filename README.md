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
- **Streamlit Interactive UI**: Dashboard telemetry, cross-modal search bar with preview cards, privacy audit logs, and authorized folder management.

---

## 🏗️ Project Architecture

```
SeekVault/
├── .gitignore
├── README.md
├── SEEKVAULT_IMPLEMENTATION_PRD.md       # Master engineering PRD & task specs
├── SeekVault_Updated_Synopsis.pdf         # Conceptual architecture & academic synopsis
└── SeekVault Prototype/
    ├── app.py                             # Streamlit main application entry point
    ├── requirements.txt                   # Production & testing dependencies
    ├── run_demo.py                        # Automated demo initialization
    ├── verify_e2e.py                      # 8-point end-to-end verification suite
    ├── ARCHITECTURE.md                    # Detailed system design
    ├── IMPLEMENTATION_PLAN.md             # Implementation specifications
    ├── WALKTHROUGH.md                     # Guided walkthrough
    ├── seekvault/                         # Core Python package
    │   ├── config.py                      # Global paths & hyperparameter constants
    │   ├── database/                      # SQLite schema, connection & repository
    │   ├── extraction/                    # PDF, DOCX, TXT, image & OCR extraction
    │   ├── privacy/                       # Analyzer, custom regex, classifier & sanitizer
    │   ├── embeddings/                    # Text & image embedding managers (MiniLM, CLIP)
    │   ├── search/                        # FAISS vector indices, engine & access verifier
    │   ├── monitoring/                    # Watchdog folder synchronization
    │   ├── organization/                  # Duplicate & version detectors
    │   ├── ingestion/                     # Ingestion pipeline coordinator
    │   └── ui/                            # Streamlit page modules & components
    ├── sample_data/                       # Sample test fixtures & generator script
    └── tests/                             # Automated pytest unit & integration suite
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11 (recommended)
- Tesseract OCR (optional, for image text OCR)

### 2. Install Dependencies
```bash
cd "SeekVault Prototype"
pip install -r requirements.txt
```

### 3. Run End-to-End Verification
```bash
python verify_e2e.py
```

### 4. Run Automated Test Suite
```bash
pytest tests/ -v
```

### 5. Launch Application
```bash
streamlit run app.py
```

---

## 🛡️ License

Independent Open-Source Software. Developed for local-first privacy research and high-performance desktop search.