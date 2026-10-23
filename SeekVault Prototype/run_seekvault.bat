@echo off
title SeekVault - Local Multimodal Search
echo ========================================================
echo Starting SeekVault Local Search Engine...
echo ========================================================
cd /d "%~dp0"
start "" "http://localhost:8501"
"C:\Users\hp\OneDrive\Documents\Saanjh\python_env\python.exe" -m streamlit run app.py --server.headless false --server.port 8501
pause
