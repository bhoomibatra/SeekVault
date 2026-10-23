@echo off
setlocal enabledelayedexpansion
title SeekVault - Privacy-First Local Search Engine

echo =====================================================================
echo                 SeekVault Desktop Application
echo        Privacy-First Multimodal Local Semantic Search Engine
echo =====================================================================
echo.

:: 1. Navigate to project root
cd /d "%~dp0SeekVault Prototype"

:: 2. Ensure data directories exist
if not exist "data_storage" mkdir "data_storage"
if not exist "data_storage\backups" mkdir "data_storage\backups"

:: 3. Configure offline & privacy environment variables
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"

:: 4. Locate Python Runtime
set "PYTHON_EXE="

if exist "C:\Users\hp\OneDrive\Documents\Saanjh\python_env\python.exe" (
    set "PYTHON_EXE=C:\Users\hp\OneDrive\Documents\Saanjh\python_env\python.exe"
    goto :PYTHON_FOUND
)

if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)

if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)

if exist "%~dp0SeekVault Prototype\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0SeekVault Prototype\venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)

echo [ERROR] Python environment was not found!
echo Please ensure Python 3.10+ is installed or virtual environment exists.
echo.
pause
exit /b 1

:PYTHON_FOUND
echo [INFO] Using Python runtime: !PYTHON_EXE!
echo [INFO] Launching SeekVault user interface on http://localhost:8501 ...
echo [INFO] Press Ctrl+C in this window anytime to terminate the application.
echo.

:: 5. Open Default Browser
start "" "http://localhost:8501"

:: 6. Launch Streamlit Application
"!PYTHON_EXE!" -m streamlit run app.py --server.port 8501 --server.headless false

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [NOTICE] SeekVault application terminated with exit code %ERRORLEVEL%.
    pause
)
