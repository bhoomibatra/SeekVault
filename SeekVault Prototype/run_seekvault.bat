@echo off
setlocal enabledelayedexpansion
title SeekVault - Local-First Semantic Search

echo ======================================================
echo           SeekVault Desktop Launcher
echo   Privacy-First Multimodal Semantic Search Engine
echo ======================================================
echo.

cd /d "%~dp0"

:: 1. Detect Python executable (checks local/known virtualenvs first, then PATH)
set "PYTHON_EXE="

if exist "C:\Users\hp\OneDrive\Documents\Saanjh\python_env\Scripts\python.exe" (
    set "PYTHON_EXE=C:\Users\hp\OneDrive\Documents\Saanjh\python_env\Scripts\python.exe"
) else if exist "C:\Users\hp\OneDrive\Documents\Saanjh\python_env\python.exe" (
    set "PYTHON_EXE=C:\Users\hp\OneDrive\Documents\Saanjh\python_env\python.exe"
) else if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
) else if exist "%~dp0..\venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0..\venv\Scripts\python.exe"
) else (
    where python >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set "PYTHON_EXE=python"
    )
)

if "%PYTHON_EXE%"=="" (
    echo [ERROR] Python was not found in your PATH or virtual environment!
    echo Please install Python 3.10 or 3.11 from python.org and add it to PATH.
    echo.
    pause
    exit /b 1
)

:: 2. Display Python version
for /f "tokens=*" %%i in ('"%PYTHON_EXE%" --version 2^>^&1') do echo [INFO] Using Python: %%i

:: 3. Launch Streamlit Application
echo [INFO] Starting SeekVault local application...
echo [INFO] Opening default browser at http://localhost:8501
echo.
"%PYTHON_EXE%" -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] SeekVault exited with code: %ERRORLEVEL%
    pause
)
