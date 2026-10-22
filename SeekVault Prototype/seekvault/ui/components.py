import streamlit as st
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple

def open_file_in_os(file_path: str) -> Tuple[bool, str]:
    """Launch the file using its default registered application."""
    if not file_path or not os.path.exists(file_path):
        return False, f"File does not exist on disk: {file_path}"

    try:
        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", file_path])
        else:
            subprocess.Popen(["xdg-open", file_path])
        return True, "File opened successfully."
    except Exception as e:
        return False, f"Failed to open file: {e}"

def open_folder_in_os(file_path: str) -> Tuple[bool, str]:
    """Open containing directory in file explorer with the file selected/highlighted."""
    if not file_path:
        return False, "Invalid file path."

    norm_path = os.path.normpath(file_path)
    parent_dir = os.path.dirname(norm_path)

    try:
        if sys.platform == "win32":
            if os.path.exists(norm_path):
                subprocess.Popen(["explorer", f"/select,{norm_path}"])
            elif os.path.exists(parent_dir):
                subprocess.Popen(["explorer", parent_dir])
            else:
                return False, f"Folder does not exist: {parent_dir}"
        elif sys.platform == "darwin":
            target = norm_path if os.path.exists(norm_path) else parent_dir
            subprocess.Popen(["open", "-R", target])
        else:
            target = parent_dir if os.path.exists(parent_dir) else norm_path
            subprocess.Popen(["xdg-open", target])
        return True, "Folder opened successfully."
    except Exception as e:
        return False, f"Failed to open folder: {e}"


def render_tier_badge(tier: str) -> str:
    """Return colored HTML badge for privacy tiers."""
    colors = {
        "FULL": "#10B981",       # Emerald green
        "REDACTED": "#F59E0B",   # Amber / Orange
        "METADATA_ONLY": "#EF4444" # Red
    }
    color = colors.get(tier, "#6B7280")
    return f"""<span style="background-color: {color}20; color: {color}; border: 1px solid {color}50; padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.82rem;">{tier}</span>"""

def render_score_bar(score: float) -> str:
    """Render a visual similarity percentage bar."""
    pct = max(0, min(100, int(score * 100)))
    color = "#3B82F6" if pct > 65 else ("#F59E0B" if pct > 45 else "#9CA3AF")
    return f"""
    <div style="background-color: #E5E7EB; border-radius: 4px; height: 8px; width: 100%; margin-top: 4px;">
        <div style="background-color: {color}; width: {pct}%; height: 100%; border-radius: 4px;"></div>
    </div>
    """

def format_file_size(bytes_size: int) -> str:
    """Human readable file sizes."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    else:
        return f"{bytes_size / (1024 * 1024):.2f} MB"
