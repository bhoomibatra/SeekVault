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

# Enforce offline mode in environment
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"

# 1. Find Python executable (checks custom env var, project venvs, then PATH)
$PythonExe = $null

if ($env:SEEKVAULT_PYTHON -and (Test-Path $env:SEEKVAULT_PYTHON)) {
    $PythonExe = $env:SEEKVAULT_PYTHON
}

if (-not $PythonExe) {
    $CandidateEnvs = @(
        "$ScriptDir\venv\Scripts\python.exe",
        "$ScriptDir\.venv\Scripts\python.exe",
        "$ScriptDir\..\venv\Scripts\python.exe",
        "$ScriptDir\..\.venv\Scripts\python.exe",
        "C:\Users\hp\OneDrive\Documents\Saanjh\python_env\Scripts\python.exe",
        "C:\Users\hp\OneDrive\Documents\Saanjh\python_env\python.exe"
    )

    foreach ($envPath in $CandidateEnvs) {
        if (Test-Path $envPath) {
            $PythonExe = $envPath
            break
        }
    }
}

if (-not $PythonExe) {
    $Cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($Cmd) {
        $PythonExe = "python"
    }
}

if (-not $PythonExe) {
    Write-Host "[ERROR] Python was not found in your system PATH or virtual environment!" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from python.org and ensure it is added to your PATH." -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

$PyVersion = & $PythonExe --version 2>&1
Write-Host "[INFO] Detected Python runtime: $PyVersion ($PythonExe)" -ForegroundColor Green

# 2. Launch Streamlit Application
Write-Host "[INFO] Starting SeekVault application on http://localhost:8501..." -ForegroundColor Green
Write-Host ""

& $PythonExe -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] SeekVault exited with error code: $LASTEXITCODE" -ForegroundColor Red
    Read-Host "Press Enter to exit..."
}
