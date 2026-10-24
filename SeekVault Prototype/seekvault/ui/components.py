import streamlit as st
import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, Any, Tuple

def open_file_in_os(file_path: str) -> Tuple[bool, str]:
    """Launch the file using its default registered application."""
    if not file_path:
        return False, "Invalid file path."

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
    except Exception as e:
        return False, f"Failed to open file: {e}"

def open_folder_in_os(file_path: str) -> Tuple[bool, str]:
    """Open containing directory in file explorer with the file selected/highlighted."""
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
    """Return colored HTML badge for privacy tiers with WCAG compliant text contrast."""
    badge_config = {
        "FULL": {"border": "#10B981", "bg": "#ECFDF5", "text": "#166534"},
        "REDACTED": {"border": "#F59E0B", "bg": "#FFFBEB", "text": "#92400E"},
        "METADATA_ONLY": {"border": "#EF4444", "bg": "#FEF2F2", "text": "#B42318"},
    }
    cfg = badge_config.get(tier, {"border": "#697386", "bg": "#F0EEE8", "text": "#15181E"})
    return f"""<span style="background-color: {cfg['bg']}; color: {cfg['text']}; border: 1px solid {cfg['border']}; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.78rem; font-family: 'JetBrains Mono', Consolas, monospace;">{tier}</span>"""

def render_relevance_badge(label: str) -> str:
    """Return colored HTML badge for search retrieval attribution with readable dark text."""
    colors = {
        "Both": ("#6366F1", "#EEF2FF", "#3730A3", "Hybrid (Both)"),      # Indigo border, light bg, dark indigo text
        "Keyword": ("#06B6D4", "#ECFEFF", "#155E75", "Keyword Match"),   # Cyan border, light bg, dark cyan text
        "Semantic": ("#8B5CF6", "#F5F3FF", "#5B21B6", "Semantic Match"), # Purple border, light bg, dark purple text
    }
    border, bg, text_color, text = colors.get(label, ("#697386", "#F0EEE8", "#15181E", label or "Match"))
    return f"""<span style="background-color: {bg}; color: {text_color}; border: 1px solid {border}; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 0.78rem;">{text}</span>"""

def render_score_bar(score: float) -> str:
    """Render a visual similarity percentage bar."""
    pct = max(0, min(100, int(score * 100)))
    color = "#1D4ED8" if pct > 65 else ("#92400E" if pct > 45 else "#697386")
    return f"""
    <div style="background-color: #E6E2D8; border-radius: 4px; height: 6px; width: 100%; margin-top: 4px;">
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
    """Inject SeekVault Light Theme Design System ensuring WCAG AA compliant contrast."""
    custom_css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=swap');

        /* ─── CSS Variables ─── */
        :root {
            --bg-main: #F7F6F2;
            --bg-secondary: #F0EEE8;
            --bg-card: #FFFFFF;
            --text-primary: #15181E;
            --text-secondary: #4A5160;
            --text-muted: #697386;
            --border-subtle: #E6E2D8;
            --border-strong: #D1CBC0;
            --accent-primary: #1D4ED8;
            --accent-hover: #1E40AF;
            --color-success: #166534;
            --color-warning: #92400E;
            --color-error: #B42318;
        }

        /* ─── Global Base Reset & Typography ─── */
        html, body, .stApp {
            background-color: #F7F6F2 !important;
            color: #15181E !important;
            font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
            font-weight: 400 !important;
            -webkit-font-smoothing: antialiased;
        }

        /* Enforce dark text and clean vertical line-height across all generic Streamlit layout containers */
        .stApp p, .stApp label, .stApp li, .stApp td, .stApp th {
            color: #15181E;
            font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif !important;
            line-height: 1.45 !important;
        }

        /* ─── Guaranteed Fix for Expander & Icon Overlap ─── */
        [data-testid="stExpander"] {
            border: 1px solid #E6E2D8 !important;
            border-radius: 8px !important;
            background-color: #FFFFFF !important;
            margin-bottom: 12px !important;
        }

        [data-testid="stExpander"] summary {
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            gap: 12px !important;
            cursor: pointer !important;
            padding: 10px 14px !important;
            list-style: none !important;
        }

        [data-testid="stExpander"] summary::-webkit-details-marker {
            display: none !important;
        }

        /* ─── Universal Protection for ALL Streamlit Icons Across Entire App ─── */
        [data-testid="stIconMaterial"],
        [data-testid^="stIcon"],
        [data-testid*="Chevron"],
        .material-symbols-rounded,
        .material-icons,
        span[translate="no"] {
            font-family: "Material Symbols Rounded", "Material Icons", sans-serif !important;
            font-feature-settings: "liga" 1 !important;
            -webkit-font-feature-settings: "liga" 1 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            overflow: hidden !important;
            max-width: 1.5rem !important;
            max-height: 1.5rem !important;
            text-overflow: clip !important;
            white-space: nowrap !important;
            line-height: 1 !important;
            vertical-align: middle !important;
            flex-shrink: 0 !important;
        }

        /* Completely suppress raw ligature text strings on all expander chevrons */
        [data-testid="stExpander"] summary [data-testid="stIconMaterial"],
        [data-testid="stExpander"] summary [data-testid="stExpanderIcon"],
        [data-testid="stExpander"] summary [data-testid="stExpanderStepChevron"],
        [data-testid="stExpander"] summary [data-testid="stExpanderToggleIcon"],
        [data-testid="stExpander"] summary svg,
        [data-testid="stExpander"] summary div:first-child [data-testid="stIconMaterial"],
        details summary [data-testid="stIconMaterial"],
        details summary [data-testid="stExpanderIcon"],
        details summary [data-testid="stExpanderStepChevron"],
        .stExpander summary [data-testid="stIconMaterial"] {
            font-size: 0 !important;
            color: transparent !important;
            -webkit-text-fill-color: transparent !important;
            line-height: 0 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 18px !important;
            min-width: 18px !important;
            max-width: 18px !important;
            height: 18px !important;
            overflow: hidden !important;
            flex-shrink: 0 !important;
            position: relative !important;
            letter-spacing: -9999px !important;
            user-select: none !important;
        }

        /* Crisp vector chevron that NEVER leaks font text */
        [data-testid="stExpander"] summary [data-testid="stIconMaterial"]::after,
        [data-testid="stExpander"] summary [data-testid="stExpanderIcon"]::after,
        [data-testid="stExpander"] summary [data-testid="stExpanderStepChevron"]::after,
        [data-testid="stExpander"] summary [data-testid="stExpanderToggleIcon"]::after,
        [data-testid="stExpander"] summary div:first-child [data-testid="stIconMaterial"]::after,
        details summary [data-testid="stIconMaterial"]::after,
        details summary [data-testid="stExpanderIcon"]::after,
        details summary [data-testid="stExpanderStepChevron"]::after,
        .stExpander summary [data-testid="stIconMaterial"]::after {
            content: '' !important;
            display: block !important;
            width: 7px !important;
            height: 7px !important;
            border-right: 2px solid #4A5160 !important;
            border-bottom: 2px solid #4A5160 !important;
            transform: rotate(-45deg) !important;
            transition: transform 0.18s ease !important;
            margin-left: -2px !important;
            letter-spacing: normal !important;
        }

        /* Rotate chevron downward when expander is open */
        [data-testid="stExpander"][open] summary [data-testid="stIconMaterial"]::after,
        [data-testid="stExpander"][open] summary [data-testid="stExpanderIcon"]::after,
        [data-testid="stExpander"][open] summary [data-testid="stExpanderStepChevron"]::after,
        [data-testid="stExpander"][open] summary [data-testid="stExpanderToggleIcon"]::after,
        [data-testid="stExpander"][open] summary div:first-child [data-testid="stIconMaterial"]::after,
        details[open] summary [data-testid="stIconMaterial"]::after,
        details[open] summary [data-testid="stExpanderIcon"]::after,
        details[open] summary [data-testid="stExpanderStepChevron"]::after,
        .stExpander[open] summary [data-testid="stIconMaterial"]::after {
            transform: rotate(45deg) !important;
            margin-top: -3px !important;
            margin-left: 0 !important;
        }

        /* Expander label text must never touch or collide with the icon */
        [data-testid="stExpander"] summary > div,
        [data-testid="stExpander"] summary > p,
        details summary > div,
        details summary > p {
            margin: 0 !important;
            padding: 0 !important;
            flex: 1 !important;
            font-size: 0.92rem !important;
            font-weight: 600 !important;
            color: #15181E !important;
            line-height: 1.45 !important;
            white-space: normal !important;
            overflow-wrap: break-word !important;
        }

        /* Buttons: Ensure adequate width, padding, clean line-height, and proper text wrapping */
        [data-testid="stButton"] button,
        .stButton > button {
            min-height: 38px !important;
            padding: 8px 16px !important;
            font-size: 0.88rem !important;
            font-weight: 500 !important;
            line-height: 1.45 !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            white-space: normal !important;
            word-break: normal !important;
            overflow-wrap: break-word !important;
            border-radius: 6px !important;
        }


        /* ─── Headings: 600-700 weight, solid #15181E ─── */
        h1, h2, h3, h4, h5, h6,
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
            font-family: 'Plus Jakarta Sans', 'Inter', -apple-system, sans-serif !important;
            color: #15181E !important;
            -webkit-text-fill-color: #15181E !important;
            letter-spacing: -0.015em !important;
        }

        h1, .stMarkdown h1 {
            font-size: 1.85rem !important;
            font-weight: 700 !important;
            line-height: 1.25 !important;
            margin-bottom: 0.35rem !important;
        }

        h2, .stMarkdown h2 {
            font-size: 1.30rem !important;
            font-weight: 600 !important;
            line-height: 1.3 !important;
            margin-top: 1.2rem !important;
            margin-bottom: 0.4rem !important;
        }

        h3, .stMarkdown h3 {
            font-size: 1.08rem !important;
            font-weight: 600 !important;
            line-height: 1.35 !important;
            margin-top: 1rem !important;
            margin-bottom: 0.35rem !important;
        }

        /* ─── Monospace Code and Technical Metadata ─── */
        code, pre, .font-mono, [data-testid="stCodeBlock"], [data-testid="stCode"] {
            font-family: 'JetBrains Mono', Consolas, 'Courier New', monospace !important;
        }

        code {
            background-color: #F0EEE8 !important;
            color: #15181E !important;
            border: 1px solid #E6E2D8 !important;
            border-radius: 4px !important;
            padding: 2px 6px !important;
            font-size: 0.85em !important;
        }

        /* ─── Streamlit Sidebar Styling ─── */
        [data-testid="stSidebar"] {
            background-color: #F0EEE8 !important;
            border-right: 1px solid #E6E2D8 !important;
        }

        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] span, 
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] div {
            color: #15181E;
        }

        /* Sidebar Navigation Radio Options */
        [data-testid="stSidebar"] [data-baseweb="radio"] {
            padding: 4px 0 !important;
        }

        [data-testid="stSidebar"] [data-baseweb="radio"] label {
            font-size: 0.90rem !important;
            font-weight: 500 !important;
            color: #15181E !important;
            cursor: pointer !important;
        }

        [data-testid="stSidebar"] [data-baseweb="radio"] input:checked + div {
            background-color: #1D4ED8 !important;
            border-color: #1D4ED8 !important;
        }

        /* ─── Streamlit Inputs & Textareas ─── */
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            background-color: #FFFFFF !important;
            color: #15181E !important;
            border: 1px solid #E6E2D8 !important;
            border-radius: 6px !important;
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
            font-size: 0.92rem !important;
            padding: 10px 14px !important;
        }

        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder {
            color: #697386 !important;
            opacity: 1 !important;
        }

        [data-testid="stTextInput"] input:focus,
        [data-testid="stTextArea"] textarea:focus {
            border-color: #1D4ED8 !important;
            box-shadow: 0 0 0 1px #1D4ED8 !important;
            outline: none !important;
        }

        [data-testid="stWidgetLabel"] label,
        [data-testid="stWidgetLabel"] p {
            color: #15181E !important;
            font-weight: 500 !important;
            font-size: 0.88rem !important;
            margin-bottom: 4px !important;
        }

        /* ─── Selectboxes & Dropdowns ─── */
        [data-testid="stSelectbox"] > div > div {
            background-color: #FFFFFF !important;
            border: 1px solid #E6E2D8 !important;
            border-radius: 6px !important;
            color: #15181E !important;
        }

        [data-testid="stSelectbox"] span {
            color: #15181E !important;
            font-size: 0.90rem !important;
        }

        /* ─── Primary Buttons: #1D4ED8 with white text ─── */
        button[kind="primary"],
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"] {
            background-color: #1D4ED8 !important;
            color: #FFFFFF !important;
            border: 1px solid #1D4ED8 !important;
            border-radius: 6px !important;
            font-weight: 600 !important;
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
            font-size: 0.90rem !important;
            box-shadow: none !important;
            transition: background-color 0.15s ease !important;
        }

        button[kind="primary"]:hover,
        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="baseButton-primary"]:hover {
            background-color: #1E40AF !important;
            border-color: #1E40AF !important;
            color: #FFFFFF !important;
        }

        /* ─── Secondary Buttons: Light background with dark text ─── */
        button[kind="secondary"],
        .stButton > button,
        .stButton > button[data-testid="baseButton-secondary"] {
            background-color: #FFFFFF !important;
            color: #15181E !important;
            border: 1px solid #E6E2D8 !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
            font-size: 0.90rem !important;
            box-shadow: none !important;
            transition: all 0.15s ease !important;
        }

        button[kind="secondary"]:hover,
        .stButton > button:hover {
            background-color: #F0EEE8 !important;
            border-color: #D1CBC0 !important;
            color: #15181E !important;
        }

        /* ─── Tabs: Restrained cobalt indicator & readable dark text ─── */
        button[data-baseweb="tab"] {
            color: #4A5160 !important;
            font-weight: 500 !important;
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
            font-size: 0.90rem !important;
            border-bottom: 2px solid transparent !important;
            padding: 8px 16px !important;
        }

        button[data-baseweb="tab"]:hover {
            color: #15181E !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            color: #1D4ED8 !important;
            font-weight: 600 !important;
            border-bottom: 2px solid #1D4ED8 !important;
        }

        /* Streamlit expander content styling */
        [data-testid="stExpanderDetails"] {
            padding: 12px 16px !important;
        }

        /* ─── Streamlit Metrics ─── */
        [data-testid="stMetricLabel"] p {
            color: #4A5160 !important;
            font-size: 0.82rem !important;
            font-weight: 500 !important;
        }

        [data-testid="stMetricValue"] {
            color: #15181E !important;
            -webkit-text-fill-color: #15181E !important;
            font-size: 1.70rem !important;
            font-weight: 700 !important;
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
        }

        /* ─── Muted & Secondary Text ─── */
        [data-testid="stCaptionContainer"] p,
        .text-muted {
            color: #697386 !important;
            font-size: 0.82rem !important;
        }

        /* ─── SeekVault Hero Document Card ─── */
        .instrument-card,
        .seekvault-search-card {
            background-color: #FFFFFF !important;
            border: 1px solid #E6E2D8 !important;
            border-radius: 8px !important;
            padding: 16px 20px !important;
            margin-bottom: 12px !important;
            box-shadow: 0 1px 2px rgba(21, 24, 30, 0.03) !important;
        }

        .instrument-card:hover {
            border-color: #D1CBC0 !important;
            box-shadow: 0 4px 12px rgba(21, 24, 30, 0.05) !important;
        }

        .instrument-snippet {
            font-size: 0.88rem !important;
            line-height: 1.55 !important;
            color: #4A5160 !important;
            background-color: #F0EEE8 !important;
            border-left: 3px solid #D1CBC0 !important;
            padding: 8px 12px !important;
            border-radius: 0 4px 4px 0 !important;
            margin: 8px 0 !important;
            font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
        }

        .instrument-snippet mark {
            background-color: #FEF08A !important;
            color: #15181E !important;
            font-weight: 600 !important;
            padding: 1px 4px !important;
            border-radius: 2px !important;
        }

        /* ─── Document Format Emblems ─── */
        .format-badge {
            font-family: 'JetBrains Mono', Consolas, monospace !important;
            font-size: 0.70rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.04em !important;
            padding: 2px 6px !important;
            border-radius: 4px !important;
            display: inline-block !important;
        }

        .format-pdf { background-color: #FEE2E2 !important; color: #B42318 !important; border: 1px solid #FECACA !important; }
        .format-docx { background-color: #EFF6FF !important; color: #1D4ED8 !important; border: 1px solid #BFDBFE !important; }
        .format-txt { background-color: #F0FDF4 !important; color: #166534 !important; border: 1px solid #BBF7D0 !important; }
        .format-img { background-color: #FAF5FF !important; color: #6B21A8 !important; border: 1px solid #E9D5FF !important; }

        /* ─── Streamlit DataFrames / Tables ─── */
        [data-testid="stDataFrame"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E6E2D8 !important;
            border-radius: 6px !important;
        }

        [data-testid="stDataFrame"] div {
            color: #15181E !important;
        }

        /* ─── Streamlit Alerts ─── */
        [data-testid="stAlert"] {
            border-radius: 6px !important;
            padding: 12px 16px !important;
        }

        [data-testid="stAlert"] p {
            font-size: 0.88rem !important;
            line-height: 1.45 !important;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
