@echo off
setlocal enabledelayedexpansion
title SeekVault - Privacy-First Local Search Engine

:: Parse command line flags
set "SILENT_MODE=0"
set "DOWNLOAD_MODELS=0"
for %%A in (%*) do (
    if /i "%%~A"=="--silent" set "SILENT_MODE=1"
    if /i "%%~A"=="-s" set "SILENT_MODE=1"
    if /i "%%~A"=="--download-models" set "DOWNLOAD_MODELS=1"
)

:: 1. Navigate to directory containing app.py
cd /d "%~dp0"
if not exist "app.py" (
    echo [ERROR] app.py not found in "%~dp0"!
    if "!SILENT_MODE!"=="0" pause
    exit /b 1
)

:: 2. Load environment variables from .env if present
if exist ".env" (
    for /f "usebackq tokens=1* delims==" %%I in (".env") do (
        set "KEY=%%I"
        set "VAL=%%J"
        if not "!KEY:~0,1!"=="#" (
            if not "!KEY!"=="" set "!KEY!=!VAL!"
        )
    )
)
if exist "..\.env" (
    for /f "usebackq tokens=1* delims==" %%I in ("..\.env") do (
        set "KEY=%%I"
        set "VAL=%%J"
        if not "!KEY:~0,1!"=="#" (
            if not "!KEY!"=="" set "!KEY!=!VAL!"
        )
    )
)

:: Defaults for host and port
if "%SEEKVAULT_HOST%"=="" set "SEEKVAULT_HOST=localhost"
if "%SEEKVAULT_PORT%"=="" set "SEEKVAULT_PORT=8501"

:: 3. Python discovery order: SEEKVAULT_PYTHON, project venv/.venv, then PATH
set "PYTHON_EXE="

if defined SEEKVAULT_PYTHON (
    if exist "%SEEKVAULT_PYTHON%" (
        set "PYTHON_EXE=%SEEKVAULT_PYTHON%"
        goto :PYTHON_FOUND
    )
)

if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)
if exist "%~dp0..\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0..\venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)
if exist "%~dp0..\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0..\.venv\Scripts\python.exe"
    goto :PYTHON_FOUND
)

where python >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_EXE=python"
    goto :PYTHON_FOUND
)

echo =====================================================================
echo [ERROR] Python was not found in SEEKVAULT_PYTHON, virtual environment, or system PATH!
echo Please install Python 3.10+ and add it to your PATH, or set SEEKVAULT_PYTHON.
echo =====================================================================
if "!SILENT_MODE!"=="0" pause
exit /b 1

:PYTHON_FOUND

:: If requested --download-models, run download_models.py
if "!DOWNLOAD_MODELS!"=="1" (
    echo [INFO] Running model downloader...
    "!PYTHON_EXE!" download_models.py
    if "!SILENT_MODE!"=="0" pause
    exit /b %ERRORLEVEL%
)

:: 4. Verify Streamlit is importable
"!PYTHON_EXE!" -c "import streamlit" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Streamlit is not installed or importable in: !PYTHON_EXE!
    echo Please install dependencies via: !PYTHON_EXE! -m pip install -r requirements.txt
    if "!SILENT_MODE!"=="0" pause
    exit /b 1
)

:: 5. Enforce offline mode and disable telemetry
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"

:: 6. Ensure data storage directories exist
if not exist "data_storage" mkdir "data_storage"
if not exist "data_storage\backups" mkdir "data_storage\backups"

:: 7. Check if port is already in use by SeekVault
netstat -ano | findstr /R /C:":%SEEKVAULT_PORT% .*LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] SeekVault server is already running on http://%SEEKVAULT_HOST%:%SEEKVAULT_PORT%/
    echo [INFO] Opening user interface in your default browser...
    start "" "http://%SEEKVAULT_HOST%:%SEEKVAULT_PORT%"
    exit /b 0
)

echo =====================================================================
echo                 SeekVault Desktop Application
echo        Privacy-First Multimodal Local Semantic Search Engine
echo =====================================================================
echo [INFO] Python Runtime: !PYTHON_EXE!
echo [INFO] Serving on:     http://%SEEKVAULT_HOST%:%SEEKVAULT_PORT%
echo [INFO] Offline Mode:   HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1
echo [INFO] Press Ctrl+C in this console window anytime to shut down.
echo =====================================================================
echo.

:: 8. Launch Streamlit (Streamlit opens the browser once automatically when headless is false)
"!PYTHON_EXE!" -m streamlit run app.py --server.port %SEEKVAULT_PORT% --server.address %SEEKVAULT_HOST% --server.headless false

if %ERRORLEVEL% NEQ 0 (
    echo [NOTICE] SeekVault terminated with exit code %ERRORLEVEL%.
    if "!SILENT_MODE!"=="0" pause
)
