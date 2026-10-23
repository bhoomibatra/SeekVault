# SeekVault PowerShell Desktop Launcher
[CmdletBinding()]
param(
    [switch]$Silent,
    [switch]$DownloadModels
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Verify app.py exists
if (-not (Test-Path "$ScriptDir\app.py")) {
    Write-Host "[ERROR] app.py not found in $ScriptDir!" -ForegroundColor Red
    if (-not $Silent) { Read-Host "Press Enter to exit..." }
    exit 1
}

# 2. Load .env if present
$EnvFiles = @("$ScriptDir\.env", "$ScriptDir\..\.env")
foreach ($ef in $EnvFiles) {
    if (Test-Path $ef) {
        Get-Content $ef | ForEach-Object {
            $line = $_.Trim()
            if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
                $parts = $line.Split("=", 2)
                $k = $parts[0].Trim()
                $v = $parts[1].Trim()
                [Environment]::SetEnvironmentVariable($k, $v, "Process")
            }
        }
    }
}

$HostName = if ($env:SEEKVAULT_HOST) { $env:SEEKVAULT_HOST } else { "localhost" }
$Port = if ($env:SEEKVAULT_PORT) { [int]$env:SEEKVAULT_PORT } else { 8501 }

# 3. Discover Python runtime: SEEKVAULT_PYTHON, project venv/.venv, then PATH
$PythonExe = $null

if ($env:SEEKVAULT_PYTHON -and (Test-Path $env:SEEKVAULT_PYTHON)) {
    $PythonExe = $env:SEEKVAULT_PYTHON
}

if (-not $PythonExe) {
    $CandidateEnvs = @(
        "$ScriptDir\venv\Scripts\python.exe",
        "$ScriptDir\.venv\Scripts\python.exe",
        "$ScriptDir\..\venv\Scripts\python.exe",
        "$ScriptDir\..\.venv\Scripts\python.exe"
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
    Write-Host "[ERROR] Python was not found in SEEKVAULT_PYTHON, virtual environment, or system PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from python.org and ensure it is added to your PATH." -ForegroundColor Yellow
    if (-not $Silent) { Read-Host "Press Enter to exit..." }
    exit 1
}

# 4. If --download-models requested
if ($DownloadModels) {
    Write-Host "[INFO] Running model downloader..." -ForegroundColor Cyan
    & $PythonExe download_models.py
    if (-not $Silent) { Read-Host "Press Enter to exit..." }
    exit $LASTEXITCODE
}

# 5. Verify Streamlit is importable
$CheckStreamlit = & $PythonExe -c "import streamlit" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Streamlit is not importable in: $PythonExe" -ForegroundColor Red
    Write-Host "Please install dependencies via: & '$PythonExe' -m pip install -r requirements.txt" -ForegroundColor Yellow
    if (-not $Silent) { Read-Host "Press Enter to exit..." }
    exit 1
}

# 6. Enforce offline mode and disable telemetry
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:STREAMLIT_BROWSER_GATHER_USAGE_STATS = "false"

# 7. Ensure data directories exist
if (-not (Test-Path "$ScriptDir\data_storage")) { New-Item -ItemType Directory -Path "$ScriptDir\data_storage" | Out-Null }
if (-not (Test-Path "$ScriptDir\data_storage\backups")) { New-Item -ItemType Directory -Path "$ScriptDir\data_storage\backups" | Out-Null }

# 8. Check if port is already in use by SeekVault
$PortActive = $false
try {
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) { $PortActive = $true }
} catch {
    # Fallback to Test-NetConnection
    $test = Test-NetConnection -ComputerName $HostName -Port $Port -WarningAction SilentlyContinue
    if ($test.TcpTestSucceeded) { $PortActive = $true }
}

if ($PortActive) {
    Write-Host "[INFO] SeekVault server is already running on http://$HostName`:$Port/" -ForegroundColor Green
    Write-Host "[INFO] Opening user interface in your default browser..." -ForegroundColor Cyan
    Start-Process "http://$HostName`:$Port"
    exit 0
}

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "          SeekVault Desktop Launcher                  " -ForegroundColor Cyan
Write-Host "  Privacy-First Multimodal Semantic Search Engine     " -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "[INFO] Detected Python runtime: $PythonExe" -ForegroundColor Green
Write-Host "[INFO] Starting SeekVault application on http://$HostName`:$Port ..." -ForegroundColor Green
Write-Host "[INFO] Offline Mode: HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1" -ForegroundColor Gray
Write-Host ""

& $PythonExe -m streamlit run app.py --server.port $Port --server.address $HostName --server.headless false

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[NOTICE] SeekVault exited with code: $LASTEXITCODE" -ForegroundColor Yellow
    if (-not $Silent) { Read-Host "Press Enter to exit..." }
}
