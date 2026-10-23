# SeekVault Desktop Deployment Guide

This document describes the local standalone Windows desktop installation and one-click deployment for SeekVault.

---

## 1. One-Click Launch Options

You can launch SeekVault using any of the following methods:

| Launcher | Location | Description |
| :--- | :--- | :--- |
| **Desktop Shortcut** | `Desktop\SeekVault.lnk` | **Recommended:** Double-click the shield icon on your Windows Desktop. |
| **Batch Launcher** | `Launch_SeekVault.bat` | Root-level batch script that locates Python, checks data directories, opens your browser, and runs SeekVault. |
| **Silent Launcher** | `Launch_SeekVault_Silent.vbs` | Runs SeekVault in the background without keeping a visible command prompt window open. |
| **PowerShell Launcher** | `run_seekvault.ps1` | Advanced launcher with automatic virtualenv detection and error reporting. |

---

## 2. Desktop Shortcut Setup & Regeneration

If you move the project directory or need to recreate the desktop shortcut, run:
```powershell
powershell -ExecutionPolicy Bypass -File .\Create_Desktop_Shortcut.ps1
```
This automatically configures:
- **Target:** `Launch_SeekVault.bat`
- **Working Directory:** SeekVault Project Root
- **Icon:** Native Windows Security Shield icon (`imageres.dll, 102`)
- **Location:** Current user's Windows Desktop folder (`Desktop\SeekVault.lnk`)

---

## 3. Environment & Offline Isolation

SeekVault runs entirely locally on your Windows machine with zero telemetry or cloud leakage:
- **Zero Cloud Dependence:** Hugging Face Hub and Transformers run with `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`.
- **Zero Usage Stats:** Streamlit telemetry is disabled (`STREAMLIT_BROWSER_GATHER_USAGE_STATS=false`).
- **Local Storage:** SQLite database (`seekvault.db`) and FAISS indices are contained strictly inside `data_storage/`.
- **Immutability:** Original files on disk are never altered, moved, or deleted.

---

## 4. Stopping the Application

To shut down SeekVault:
- If running via **`Launch_SeekVault.bat`**: Press `Ctrl + C` in the command window.
- If running in the background: Close the browser tab and stop the process via Task Manager (Python background process) or run:
  ```powershell
  Stop-Process -Name python -ErrorAction SilentlyContinue
  ```

---

## 5. Verification & Test Suite

All 119 automated unit and integration tests can be verified at any time:
```powershell
pytest tests/
```
