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
    """Inject custom 'Private Search Instrument' design tokens & styles into Streamlit."""
    custom_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

        :root {
            /* Warm Parchment & Deep Ink Palette ("The Private Search Instrument") */
            --canvas-bg: #F7F6F2;
            --canvas-subtle: #F0EEE8;
            --surface-card: #FFFFFF;
            --surface-hover: #FCFBF9;
            --border-hairline: #E6E2D8;
            --border-strong: #D1CBC0;
            --border-focus: #1D4ED8;
            --ink-primary: #15181E;
            --ink-secondary: #4A5160;
            --ink-muted: #828A98;
            --cobalt-primary: #1D4ED8;
            --cobalt-tint: #EFF4FE;
            --cobalt-border: #BFDBFE;

            /* Legacy token aliases for backward compatibility */
            --bg-base: #F7F6F2;
            --bg-surface: #F0EEE8;
            --bg-card: #FFFFFF;
            --bg-card-hover: #FCFBF9;
            --border-subtle: #E6E2D8;
            --text-primary: #15181E;
            --text-secondary: #4A5160;
            --text-muted: #828A98;
            --accent: #1D4ED8;
        }

        /* Streamlit Global Overrides */
        .stApp {
            background-color: var(--canvas-bg) !important;
            color: var(--ink-primary) !important;
            font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #F2EFEB !important;
            border-right: 1px solid var(--border-hairline) !important;
        }

        /* Hero Document Card ("The Private Search Instrument") */
        .instrument-card {
            background: var(--surface-card);
            border: 1px solid var(--border-hairline);
            border-radius: 10px;
            padding: 18px 22px;
            margin-bottom: 14px;
            box-shadow: 0 1px 3px rgba(22, 25, 30, 0.03);
            transition: all 0.15s ease-in-out;
        }
        .instrument-card:hover {
            border-color: var(--border-strong);
            box-shadow: 0 6px 20px rgba(22, 25, 30, 0.05);
            transform: translateY(-1px);
        }

        /* Document Format Emblems */
        .format-badge {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.70rem;
            font-weight: 700;
            letter-spacing: 0.3px;
            padding: 2px 7px;
            border-radius: 4px;
            display: inline-block;
            vertical-align: middle;
        }
        .format-pdf { background: #FEE2E2; color: #991B1B; }
        .format-docx { background: #DBEAFE; color: #1E40AF; }
        .format-txt { background: #F3F4F6; color: #374151; }
        .format-img { background: #EDE9FE; color: #5B21B6; }

        /* Real Passage Snippet Box */
        .instrument-snippet {
            font-size: 0.88rem;
            line-height: 1.55;
            color: var(--ink-secondary);
            background: var(--canvas-subtle);
            border-left: 3px solid var(--border-strong);
            padding: 9px 13px;
            border-radius: 0 6px 6px 0;
            margin: 10px 0;
            font-family: 'Plus Jakarta Sans', sans-serif;
            white-space: pre-wrap;
            word-break: break-word;
        }
        .instrument-snippet mark {
            background: #FEF08A;
            color: #854D0E;
            padding: 1px 3px;
            border-radius: 2px;
            font-weight: 600;
        }

        /* Metadata Line */
        .instrument-meta {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--ink-muted);
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 6px;
        }

        /* Legacy compatibility */
        .seekvault-search-card {
            background-color: #FFFFFF;
            border: 1px solid #E6E2D8;
            border-radius: 10px;
            padding: 16px 20px;
            margin-bottom: 14px;
            box-shadow: 0 1px 3px rgba(22, 25, 30, 0.03);
            transition: all 0.2s ease-in-out;
        }
        .seekvault-snippet-box {
            background-color: #F0EEE8;
            border-left: 3px solid #1D4ED8;
            padding: 10px 14px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', Consolas, monospace;
            font-size: 0.88rem;
            color: #15181E;
            line-height: 1.5;
            margin: 8px 0;
            white-space: pre-wrap;
            word-break: break-word;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
