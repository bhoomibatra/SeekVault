# SeekVault — Local-First Multimodal Semantic Search

> **100% Local-First, Privacy-Preserving Semantic Search & Document Organization Engine**  
> *Search documents and media using conceptual meaning—zero cloud dependencies, zero data leakage.*

---

## 🌟 Key Features

- **Natural Language Semantic Search**: Search across PDFs, DOCX, TXT, MD, and images (PNG, JPG, JPEG) using Sentence Transformers (`all-MiniLM-L6-v2`) and OpenAI CLIP (`clip-ViT-B-32`).
- **Sliding-Window Document Chunking**: Automatically slices long documents into overlapping segments so deep pages and sections are indexed and searchable.
- **100% Local & Zero-Trust Boundary**: Operates strictly within user-authorized directories. Revoked or de-authorized folders are immediately suppressed at search time.
- **Privacy-Preserving Tiered Indexing**:
  - `FULL`: Standard documents indexed with complete searchable embeddings.
  - `REDACTED`: PII (Aadhaar, PAN, SSN, emails, phone numbers) sanitized using Presidio analyzer; vector index stores only sanitized representations.
  - `METADATA_ONLY`: Passwords and confidential credentials indexed solely by metadata—raw vectors are never generated.
- **Original File Immutability**: Source files on disk are strictly read-only and never modified, renamed, or overwritten.
- **Cryptographic Duplicate & Version History**: SHA-256 hash clustering identifies duplicate files and reclaimable storage; semantic embeddings detect sequential document revision chains.
- **Native OS Shell Actions**: Open matching documents directly in default applications or highlight them in Windows Explorer with one click.
- **Self-Healing Vector Indices**: Disk modification monitoring and auto-healing routines reconcile out-of-sync FAISS vectors on the fly.

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

## 📖 First-Run Guide

1. **Authorize a Folder**:
   - Open the sidebar and click **📁 Authorized Folders**.
   - Enter the full path of any directory on your computer (e.g., `D:\Documents\Projects`).
   - Click **Authorize Folder**. SeekVault scans the files, runs privacy classification, and generates vector embeddings.
2. **Search Your Files**:
   - Navigate to **🔍 Semantic Search**.
   - Type natural language queries like:
     - *"draft agreement with nondisclosure clause"*
     - *"quarterly electricity or utility bill"*
     - *"red car parked outside"*
     - *"terminal connection error screenshot"*
   - Use the **👁️ Open File** and **📂 Open in Folder** buttons to launch files directly in Windows Explorer.
3. **Inspect Duplicates & Versions**:
   - Navigate to **👯 Duplicates & Versions** to view potential reclaimable disk space and document revision chains.

---

## 🧪 Testing & Verification

SeekVault includes a comprehensive automated test suite and an end-to-end operational verification script:

```powershell
# Run the complete test suite (25+ tests)
pytest tests/ -v

# Run dedicated security & boundary tests
pytest tests/test_security_boundaries.py -v

# Run 8-point operational verification with auto-healing
python verify_e2e.py
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
├── seekvault/                         # Core Python package
│   ├── config.py                      # Global parameters, paths, model configs
│   ├── database/                      # SQLite schema, connection, repository
│   ├── extraction/                    # PDF, DOCX, TXT, image & OCR extractors
│   ├── privacy/                       # Presidio analyzer, regex patterns, classifier
│   ├── embeddings/                    # Text (MiniLM) and image (CLIP) embedders
│   ├── search/                        # FAISS vector store, search engine, verifier
│   ├── monitoring/                    # Watchdog folder synchronization
│   ├── organization/                  # SHA-256 duplicate & version detectors
│   ├── ingestion/                     # Ingestion pipeline coordinator
│   └── ui/                            # Streamlit page components
└── tests/                             # Automated pytest test suites
```

---

## 🛡️ Privacy & Security Guarantee

All tokenization, privacy analysis, embedding inference, and vector indexing run **100% locally on your device**. SeekVault transmits **zero data, zero telemetry, and zero search terms** over the network.
