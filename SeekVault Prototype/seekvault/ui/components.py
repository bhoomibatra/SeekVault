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
        "FULL": "#10B981",          # Emerald green
        "REDACTED": "#F59E0B",      # Amber / Orange
        "METADATA_ONLY": "#EF4444", # Red
    }
    color = colors.get(tier, "#6B7280")
    return f"""<span style="background-color: {color}20; color: {color}; border: 1px solid {color}50; padding: 2px 8px; border-radius: 6px; font-weight: 600; font-size: 0.80rem;">{tier}</span>"""

def render_relevance_badge(label: str) -> str:
    """Return colored HTML badge for search retrieval attribution."""
    colors = {
        "Both": ("#6366F1", "⚡ Hybrid (Both)"),      # Electric Indigo
        "Keyword": ("#06B6D4", "🔤 Keyword Match"),   # Cyan
        "Semantic": ("#8B5CF6", "🧠 Semantic Match"),  # Purple
    }
    color, text = colors.get(label, ("#6B7280", label or "Match"))
    return f"""<span style="background-color: {color}20; color: {color}; border: 1px solid {color}50; padding: 2px 8px; border-radius: 6px; font-weight: 600; font-size: 0.80rem;">{text}</span>"""

def render_score_bar(score: float) -> str:
    """Render a visual similarity percentage bar."""
    pct = max(0, min(100, int(score * 100)))
    color = "#6366F1" if pct > 65 else ("#F59E0B" if pct > 45 else "#9CA3AF")
    return f"""
    <div style="background-color: #24324D; border-radius: 4px; height: 6px; width: 100%; margin-top: 4px;">
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

def inject_design_system() -> None:
    """Inject custom Obsidian Slate design tokens & card styles into Streamlit."""
    custom_css = """
    <style>
        :root {
            --bg-base: #0B0F17;
            --bg-surface: #111827;
            --bg-card: #182234;
            --bg-card-hover: #1E2B42;
            --border-subtle: #24324D;
            --border-focus: #6366F1;
            --accent: #6366F1;
            --accent-hover: #4F46E5;
            --text-primary: #F3F4F6;
            --text-secondary: #9CA3AF;
            --text-muted: #6B7280;
        }

        /* Search hero card styling */
        .seekvault-search-card {
            background-color: #182234;
            border: 1px solid #24324D;
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 14px;
            transition: all 0.2s ease-in-out;
        }
        .seekvault-search-card:hover {
            border-color: #6366F1;
            background-color: #1E2B42;
            box-shadow: 0 4px 16px rgba(99, 102, 241, 0.12);
        }

        /* Highlight chip for snippets */
        .seekvault-snippet-box {
            background-color: #0F172A;
            border-left: 3px solid #6366F1;
            padding: 10px 14px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', Consolas, monospace;
            font-size: 0.88rem;
            color: #E2E8F0;
            line-height: 1.5;
            margin: 8px 0;
            white-space: pre-wrap;
            word-break: break-word;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
