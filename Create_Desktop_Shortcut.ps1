# SeekVault Desktop Shortcut Generator
# Creates a one-click desktop shortcut for SeekVault on the user's Windows Desktop

$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LauncherPath = Join-Path $ProjectDir "Launch_SeekVault.bat"

if (-not (Test-Path $LauncherPath)) {
    Write-Host "[ERROR] Could not find launcher at $LauncherPath" -ForegroundColor Red
    exit 1
}

$ShortcutPath = Join-Path $DesktopPath "SeekVault.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $LauncherPath
$Shortcut.WorkingDirectory = $ProjectDir
$Shortcut.Description = "SeekVault - Privacy-First Multimodal Semantic Search Engine"

# Set a native Windows security shield / vault icon if available
$SystemDir = [Environment]::GetFolderPath("System")
$ShieldIcon = Join-Path $SystemDir "imageres.dll"
if (Test-Path $ShieldIcon) {
    $Shortcut.IconLocation = "$ShieldIcon, 102"  # Blue/gold shield icon
}

$Shortcut.Save()

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  SeekVault Desktop Deployment Successful!                 " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Desktop Shortcut Created: $ShortcutPath" -ForegroundColor Yellow
Write-Host "Target Launcher:          $LauncherPath" -ForegroundColor White
Write-Host "Working Directory:        $ProjectDir" -ForegroundColor White
Write-Host ""
Write-Host "You can now launch SeekVault by double-clicking the shortcut on your Desktop." -ForegroundColor Green
