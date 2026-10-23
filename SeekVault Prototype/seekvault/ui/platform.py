"""
platform.py — Native Windows integration utilities for SeekVault.
Provides native folder/file pickers, file launching, and Explorer reveal.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


def pick_folder_dialog(title: str = "Select a folder to authorize for SeekVault") -> Optional[str]:
    """Launch native Windows FolderBrowserDialog via PowerShell with TopMost owner."""
    if sys.platform != "win32":
        return None

    # PowerShell script to show FolderBrowserDialog in front of all windows
    ps_cmd = f"""
    Add-Type -AssemblyName System.Windows.Forms
    $form = New-Object System.Windows.Forms.Form
    $form.TopMost = $true
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = '{title}'
    $dialog.ShowNewFolderButton = $false
    $result = $dialog.ShowDialog($form)
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {{
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        Write-Output $dialog.SelectedPath
    }}
    $form.Dispose()
    """
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=120
        )
        out = res.stdout.strip()
        if out and os.path.isdir(out):
            return os.path.normpath(out)
    except Exception:
        pass
    return None


def pick_files_dialog(title: str = "Select documents or images to add to SeekVault") -> List[str]:
    """Launch native Windows OpenFileDialog via PowerShell with TopMost owner."""
    if sys.platform != "win32":
        return []

    ps_cmd = f"""
    Add-Type -AssemblyName System.Windows.Forms
    $form = New-Object System.Windows.Forms.Form
    $form.TopMost = $true
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Multiselect = $true
    $dialog.Title = '{title}'
    $dialog.Filter = 'Documents & Media (*.pdf;*.docx;*.txt;*.md;*.png;*.jpg;*.jpeg)|*.pdf;*.docx;*.txt;*.md;*.png;*.jpg;*.jpeg|All Files (*.*)|*.*'
    $result = $dialog.ShowDialog($form)
    if ($result -eq [System.Windows.Forms.DialogResult]::OK) {{
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        $dialog.FileNames | ForEach-Object {{ Write-Output $_ }}
    }}
    $form.Dispose()
    """
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=120
        )
        lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
        return [os.path.normpath(p) for p in lines if os.path.isfile(p)]
    except Exception:
        pass
    return []


def open_file_in_os(file_path: str) -> Tuple[bool, str]:
    """Launch the file with its default registered system application."""
    if not file_path:
        return False, "Invalid file path."

    # Try resolving relative path if needed
    p = Path(file_path)
    if not p.is_absolute():
        p = Path.cwd() / p

    if not p.exists():
        return False, f"File does not exist on disk: {p}"

    try:
        resolved = str(p.resolve())
        if sys.platform == "win32":
            os.startfile(resolved)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", resolved])
        else:
            subprocess.Popen(["xdg-open", resolved])
        return True, "File opened successfully."
    except Exception as exc:
        return False, f"Failed to open file: {exc}"


def open_folder_in_os(file_path: str) -> Tuple[bool, str]:
    """Open containing directory in Windows File Explorer with the target file highlighted."""
    if not file_path:
        return False, "Invalid file path."

    p = Path(file_path)
    if not p.is_absolute():
        p = Path.cwd() / p

    norm_path = os.path.normpath(str(p.resolve()))
    parent_dir = os.path.dirname(norm_path)

    try:
        if sys.platform == "win32":
            if os.path.exists(norm_path):
                subprocess.Popen(["explorer", f"/select,{norm_path}"])
            elif os.path.exists(parent_dir):
                subprocess.Popen(["explorer", parent_dir])
            else:
                return False, f"Directory does not exist: {parent_dir}"
        elif sys.platform == "darwin":
            target = norm_path if os.path.exists(norm_path) else parent_dir
            subprocess.Popen(["open", "-R", target])
        else:
            target = parent_dir if os.path.exists(parent_dir) else norm_path
            subprocess.Popen(["xdg-open", target])
        return True, "Opened folder in File Explorer."
    except Exception as exc:
        return False, f"Failed to open folder: {exc}"

