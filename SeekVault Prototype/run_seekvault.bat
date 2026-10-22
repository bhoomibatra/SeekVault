@echo off
setlocal enabledelayedexpansion
title SeekVault - Local-First Semantic Search

echo ======================================================
echo           SeekVault Desktop Launcher
echo   Privacy-First Multimodal Semantic Search Engine
echo ======================================================
echo.

cd /d "%~dp0"

:: 1. Check if python is available
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in your PATH!
    echo Please install Python 3.10 or 3.11 from python.org and add it to PATH.
    echo.
    pause
    exit /b 1
)

:: 2. Display Python version
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [INFO] Using: %%i

:: 3. Launch Streamlit Application
echo [INFO] Starting SeekVault local application...
echo [INFO] Opening default browser at http://localhost:8501
echo.
python -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] SeekVault exited with code: %ERRORLEVEL%
    pause
)
