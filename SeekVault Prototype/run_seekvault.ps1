# SeekVault PowerShell Desktop Launcher
[CmdletBinding()]
param()

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "          SeekVault Desktop Launcher                  " -ForegroundColor Cyan
Write-Host "  Privacy-First Multimodal Semantic Search Engine     " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Find Python executable
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    Write-Host "[ERROR] Python was not found in your system PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from python.org and ensure it is added to your PATH." -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

$PyVersion = & python --version 2>&1
Write-Host "[INFO] Detected Python runtime: $PyVersion" -ForegroundColor Green

# 2. Launch Streamlit Application
Write-Host "[INFO] Starting SeekVault application on http://localhost:8501..." -ForegroundColor Green
Write-Host ""

& python -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] SeekVault exited with error code: $LASTEXITCODE" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
}
