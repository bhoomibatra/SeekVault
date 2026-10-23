# SeekVault — Windows Setup, Operations & Architecture Guide
**Task:** TASK-03 — Reproducible Windows Setup & Architecture Validation  
**Date:** 2026-10-23  

---

## 1. Environment & Runtime Requirements

SeekVault is designed for **Windows 10/11 (64-bit)** with local CPU or GPU acceleration.

| Component | Target Version | Installed Runtime (Verified) |
|---|---|---|
| **Python** | 3.10.x – 3.11.x (64-bit) | Python 3.11.9 (64-bit) |
| **PyTorch** | >= 2.0.0 | 2.14.0+cpu |
| **Sentence-Transformers** | >= 2.2.0 | 6.1.0 |
| **FAISS** | faiss-cpu >= 1.7.4 | 1.15.1 |
| **Streamlit** | >= 1.30.0 | 1.64.0 |
| **Presidio Analyzer / Anonymizer** | >= 2.2.0 | 2.2.364 |
| **PyMuPDF** | >= 1.23.0 | 1.28.2 |
| **python-docx** | >= 1.0.0 | 1.2.0 |
| **Pillow** | >= 10.0.0 | 11.1.0 |
| **Watchdog** | >= 3.0.0 | 6.0.0 |
| **Pytest** | >= 7.4.0 | 8.3.4 |

---

## 2. Standardized Installation Steps

### Option A: Using Existing Environment
If you have an existing Python 3.11 virtual environment with machine learning packages:
```powershell
# Set environment variable pointing to the Python executable
$env:SEEKVAULT_PYTHON = "C:\Path\To\Your\python_env\python.exe"
```

### Option B: Clean Virtual Environment Creation
From `SeekVault Prototype/`:
```powershell
# 1. Create a clean virtual environment
py -3.11 -m venv venv

# 2. Activate environment
.\venv\Scripts\Activate.ps1

# 3. Upgrade pip and wheel
python -m pip install --upgrade pip setuptools wheel

# 4. Install PyTorch CPU (avoids 2GB+ CUDA wheels if GPU not needed)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 5. Install SeekVault dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt   # for running pytest & benchmarks

# 6. Pre-fetch offline model weights (for first-time offline setup)
python download_models.py
```

---

## 3. Operational Commands

### 3.1 Launch Application
- **Double-click:** `run_seekvault.bat` or right-click `run_seekvault.ps1` -> "Run with PowerShell"
- **PowerShell CLI:**
  ```powershell
  cd "SeekVault Prototype"
  .\run_seekvault.ps1
  ```
- **Direct Python CLI:**
  ```powershell
  $env:HF_HUB_OFFLINE = "1"
  $env:TRANSFORMERS_OFFLINE = "1"
  python -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false
  ```
The browser will automatically open to `http://localhost:8501`.

### 3.2 Run Diagnostics, Unit Tests & Verification
Run the complete automated regression and security test suite (119 tests):
```powershell
cd "SeekVault Prototype"
python -m pytest tests/ -v
```

Run 8-point end-to-end operational verification:
```powershell
python verify_e2e.py
```

Run retrieval quality & latency benchmark:
```powershell
python evaluation/benchmark.py
```

Run specific subsystem test suites:
```powershell
# Ingestion pipeline tests
python -m pytest tests/test_indexing_pipeline.py -v

# Privacy, PII redaction and zero-leakage tests
python -m pytest tests/test_privacy_security.py -v

# Access verification & security boundaries
python -m pytest tests/test_security_boundaries.py -v
```

### 3.3 Shutdown
- In the active terminal/command prompt window running Streamlit, press `Ctrl + C`.
- The application process, watchdog file monitoring threads, and database connections will gracefully terminate.

---

## 4. Application Data Directory Configuration

SeekVault stores persistent state (SQLite database, FAISS indices, and JSON metadata maps) in a user-writable directory.

- **Default location:** `SeekVault Prototype/data_storage/` (project-relative)
- **Custom location override:** Set `SEEKVAULT_DATA_DIR` in your environment or `.env`:
  ```powershell
  $env:SEEKVAULT_DATA_DIR = "$env:LOCALAPPDATA\SeekVault\data"
  ```
- SeekVault will automatically create parent directories if they do not exist.
- Source documents in authorized folders are **strictly read-only**; SeekVault never modifies or deletes original files.

---

## 5. Offline Operation Guarantee

SeekVault explicitly enforces local-only ML inference by setting:
```python
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
```
No document text, query embeddings, or telemetry ever leaves the host machine.
