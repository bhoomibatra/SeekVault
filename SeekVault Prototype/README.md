# SeekVault — Local-First Multimodal Semantic Search

> **100% Local-First, Privacy-Preserving Semantic Search & Document Organization Engine**  
> *Search documents and media using conceptual meaning—zero cloud dependencies, zero data leakage.*

---

## 🌟 Key Features

- **Hybrid & Semantic Search**: Combines Dense Vector Search (Sentence Transformers `all-MiniLM-L6-v2` and OpenAI CLIP `clip-ViT-B-32`) with SQLite FTS5 Full-Text Search via Reciprocal Rank Fusion (RRF).
- **Search Modes & Precision Filters**: Easily switch between **Hybrid**, **Semantic**, and **Keyword** modes, with dynamic folder scoping and file type filtering (PDF, DOCX, TXT, Images).
- **Sliding-Window Document Chunking**: Automatically slices long documents into overlapping segments so deep pages and sections are indexed and retrievable.
- **100% Local & Zero-Trust Boundary**: Operates strictly within user-authorized directories. Revoked or de-authorized folders are immediately suppressed at search time.
- **Privacy-Preserving Tiered Indexing**:
  - `FULL`: Standard documents indexed with complete searchable embeddings.
  - `REDACTED`: PII (Aadhaar, PAN, SSN, emails, phone numbers) sanitized using Presidio analyzer; vector index stores only sanitized representations and SQLite stores only masked entity tokens (`<EMAIL_...>`, `<PHONE_...>`).
  - `METADATA_ONLY`: Passwords and confidential credentials indexed solely by metadata—raw vectors and content snippets are never generated.
- **Original File Immutability**: Source files on disk are strictly read-only and never modified, renamed, or overwritten.
- **Cryptographic Duplicate & Version History**: SHA-256 hash clustering identifies duplicate files and calculated reclaimable space; conservative heuristic version suggestions with explicit user dismissal and restoration controls.
- **Native OS Shell Actions**: Open matching documents directly in default applications or highlight them in Windows Explorer with one click.
- **Operational Health & Vector Integrity**: Live telemetry diagnosing SQLite file records against FAISS vector counts with non-destructive self-healing.
- **Snapshot Backup & Restore**: Complete single-archive zip backups of SQLite database and FAISS index state with atomic restore.

---

## 📋 System Prerequisites

- **Operating System**: Windows 10 / 11 (64-bit), Linux, or macOS.
- **Python**: Python 3.10 or 3.11 (Python 3.11 recommended).
- **RAM**: Minimum 4 GB (8 GB recommended for multimodal image embedding).
- **Disk Space**: ~2 GB for PyTorch, Transformers, Sentence-Transformers, and FAISS packages.
- **Optional**: Tesseract OCR for extracting text embedded within image screenshots.

---

## 🚀 Quick Start

### 1. Installation

Clone or extract the repository, then install requirements:

```powershell
cd "SeekVault Prototype"
pip install -r requirements.txt
```

### 2. Launching SeekVault

#### Option A: One-Click Windows Launcher (Recommended)
Double-click either launcher script in the `SeekVault Prototype` folder:
- **`run_seekvault.bat`** (Windows Command Prompt launcher)
- **`run_seekvault.ps1`** (PowerShell launcher)

#### Option B: Manual Streamlit Startup
```powershell
streamlit run app.py
```
SeekVault will automatically open in your default browser at `http://localhost:8501`.

---

## 📖 Navigation & Operational Guide

1. **🔍 Search (Default Landing Page)**:
   - Type queries in natural language or exact keywords.
   - Toggle between **Hybrid (RRF)**, **Semantic**, and **Keyword (FTS5)** modes.
   - Filter by authorized folder or file type (PDF, Word, Text, Images).
   - View relevance badges (`Both`, `Semantic`, `Keyword`), masked snippets, copyable file paths, and launch files directly via **👁️ Open File** or **📂 Open Folder**.
2. **📁 File Library**:
   - Authorize directories for local indexing.
   - Safely revoke folder permissions with an explicit confirmation dialog (leaving original source files completely untouched).
   - View real-time indexing status for each file (`PENDING`, `INDEXED`, `FAILED`).
3. **🛡️ Privacy Center**:
   - Real-time offline mode verification (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`).
   - Clear transparency panel on data storage boundaries (Original Files vs SQLite vs FAISS).
   - De-identified PII entity audit table and category distribution.
4. **👯 Duplicates & Versions**:
   - SHA-256 duplicate clusters with calculated potential reclaimable storage space.
   - Heuristic version suggestions with explicit non-destructive guarantees and one-click dismiss / restore controls.
5. **🩺 System Health**:
   - Live telemetry on authorized folders, indexed files, and FAISS vector counts.
   - Automated vector integrity diagnosis with non-destructive **Heal & Sync Vector Index** action.
6. **⚙️ Settings**:
   - Model status and diagnostic health inspection.
   - Safe two-step index reset requiring explicit confirmation and re-syncing file states to `PENDING`.
   - Complete data snapshot backup and restore.

---

## 🧪 Testing & Verification

SeekVault includes an automated test suite (86 tests across 17 modules), end-to-end operational verification, and a diagnostic benchmark runner:

```powershell
# Run the complete test suite (86 tests)
pytest tests/ -v

# Run dedicated security & boundary tests
pytest tests/test_security_boundaries.py -v

# Run 8-point end-to-end operational verification
python verify_e2e.py

# Run diagnostic retrieval quality & latency benchmark
python evaluation/benchmark.py
```

---

## 📁 Repository Structure

```
SeekVault Prototype/
├── app.py                             # Streamlit application entry point
├── run_seekvault.bat                  # One-click Windows batch launcher
├── run_seekvault.ps1                  # One-click PowerShell launcher
├── requirements.txt                   # Python package dependencies
├── verify_e2e.py                      # End-to-end operational verification script
├── sample_data/                       # Curated sample datasets for testing
├── evaluation/                        # Retrieval benchmark runner & dataset
│   ├── benchmark.py                   # Benchmark execution tool (P@K, R@K, MRR, latency)
│   ├── eval_dataset.py                # Ground-truth multi-modal query dataset
│   └── BENCHMARK_REPORT.md            # Empirical performance & hardware report
├── seekvault/                         # Core Python package
│   ├── config.py                      # Global parameters, paths, model configs
│   ├── database/                      # SQLite schema, migrations, connection, repository, backup
│   ├── extraction/                    # PDF, DOCX, TXT, image & OCR extractors
│   ├── privacy/                       # Presidio analyzer, regex patterns, classifier
│   ├── embeddings/                    # Text (MiniLM) and image (CLIP) embedders, manager
│   ├── search/                        # FAISS vector store, FTS5, hybrid search engine, verifier
│   ├── monitoring/                    # Watchdog folder synchronization
│   ├── organization/                  # SHA-256 duplicate & version detectors
│   ├── ingestion/                     # Ingestion pipeline coordinator
│   └── ui/                            # Streamlit Obsidian Slate page components
└── tests/                             # 17 automated pytest test suites (86 tests)
```

---

## 🛡️ Privacy & Security Guarantee

All tokenization, privacy analysis, embedding inference, and vector indexing run **100% locally on your device**. SeekVault transmits **zero data, zero telemetry, and zero search terms** over the network.

