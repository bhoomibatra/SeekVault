"""
navigator.py — In-app desktop folder and file navigator for SeekVault.
Provides reliable, user-friendly browsing of local folders (Documents, Downloads, etc.)
with breadcrumbs, format inspection, pre-indexing review, and zero-freeze execution.
"""

import os
import streamlit as st
from pathlib import Path
from typing import Dict, List, Any, Optional

from seekvault.config import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS
from seekvault.ui.components import format_file_size


def get_user_shortcuts() -> Dict[str, str]:
    """Discover real user document locations on the local computer."""
    home = Path.home()
    od = home / "OneDrive"
    shortcuts: Dict[str, str] = {}

    candidates = [
        ("Documents", od / "Documents"),
        ("Documents (Local)", home / "Documents"),
        ("Downloads", home / "Downloads"),
        ("Desktop", od / "Desktop"),
        ("Desktop (Local)", home / "Desktop"),
        ("Pictures", od / "Pictures"),
        ("Pictures (Local)", home / "Pictures"),
        ("Sample Files", Path.cwd() / "sample_data"),
    ]

    for label, path in candidates:
        try:
            if path.exists() and path.is_dir() and label not in shortcuts:
                shortcuts[label] = str(path.resolve())
        except Exception:
            continue

    if "Home" not in shortcuts:
        shortcuts["Home"] = str(home.resolve())

    return shortcuts


def get_friendly_folder_name(folder_path: str) -> str:
    """Return a clean, human-readable name for a folder path."""
    if not folder_path:
        return ""
    p = Path(folder_path)
    shortcuts = get_user_shortcuts()
    for label, s_path in shortcuts.items():
        if str(p.resolve()) == s_path:
            return label
    return p.name or str(folder_path)


def inspect_location_for_indexing(
    target_path: str,
    is_folder: bool = True,
    recursive: bool = True
) -> Dict[str, Any]:
    """
    Safely inspect a local path and categorize files by supported formats.
    Does not modify or delete any files.
    """
    all_exts = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS
    p = Path(target_path)

    if not p.exists():
        return {
            "valid": False,
            "error": "The specified location does not exist on your computer.",
            "supported": [],
            "unsupported": [],
            "by_type": {},
            "total_bytes": 0,
            "total_files": 0,
        }

    supported_files: List[Path] = []
    unsupported_files: List[Path] = []
    total_bytes = 0
    by_type: Dict[str, int] = {}

    if not is_folder or p.is_file():
        # Single file inspection
        ext = p.suffix.lower()
        size = p.stat().st_size
        if ext in all_exts:
            supported_files.append(p)
            total_bytes += size
            fmt = ext.replace(".", "").upper()
            by_type[fmt] = 1
        else:
            unsupported_files.append(p)
    else:
        # Directory inspection
        try:
            if recursive:
                candidates = [f for f in p.rglob("*") if f.is_file()]
            else:
                candidates = [f for f in p.glob("*") if f.is_file()]
        except Exception as exc:
            return {
                "valid": False,
                "error": f"Could not access folder: {exc}",
                "supported": [],
                "unsupported": [],
                "by_type": {},
                "total_bytes": 0,
                "total_files": 0,
            }

        for item in candidates:
            ext = item.suffix.lower()
            try:
                sz = item.stat().st_size
            except Exception:
                sz = 0

            if ext in all_exts:
                supported_files.append(item)
                total_bytes += sz
                fmt = ext.replace(".", "").upper()
                by_type[fmt] = by_type.get(fmt, 0) + 1
            else:
                unsupported_files.append(item)

    return {
        "valid": True,
        "error": None,
        "supported": supported_files,
        "unsupported": unsupported_files,
        "by_type": by_type,
        "total_bytes": total_bytes,
        "total_files": len(supported_files) + len(unsupported_files),
    }


def render_folder_browser(
    key_prefix: str = "fld_nav",
    default_path: Optional[str] = None
) -> Optional[str]:
    """
    Render an intuitive in-app folder navigator.
    Returns the chosen folder path when confirmed, or None.
    """
    session_key = f"{key_prefix}_current_path"
    shortcuts = get_user_shortcuts()

    # Default to first available shortcut or CWD
    if session_key not in st.session_state or not st.session_state[session_key]:
        if default_path and os.path.isdir(default_path):
            st.session_state[session_key] = default_path
        elif "Documents" in shortcuts:
            st.session_state[session_key] = shortcuts["Documents"]
        elif "Downloads" in shortcuts:
            st.session_state[session_key] = shortcuts["Downloads"]
        else:
            st.session_state[session_key] = str(Path.cwd())

    current_path = st.session_state[session_key]
    cur_p = Path(current_path)

    # 1. Quick Location Shortcuts
    st.markdown("<div style='font-size: 0.82rem; font-weight: 600; color: #4A5160; margin-bottom: 6px;'>Quick Locations:</div>", unsafe_allow_html=True)
    sc_cols = st.columns(min(len(shortcuts), 5))
    for i, (label, s_path) in enumerate(shortcuts.items()):
        if i >= 5:
            break
        with sc_cols[i]:
            is_active = (s_path == current_path)
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"{key_prefix}_sc_{i}", type=btn_type, use_container_width=True):
                st.session_state[session_key] = s_path
                st.rerun()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # 2. Breadcrumb Navigation Bar
    st.markdown(
        f"""
        <div style="background: #F7F6F2; border: 1px solid #E6E2D8; border-radius: 6px; padding: 8px 12px; margin-bottom: 10px; font-size: 0.85rem; color: #15181E; display: flex; align-items: center;">
            <span style="font-weight: 600; color: #1D4ED8; margin-right: 8px;">Folder:</span>
            <span style="font-weight: 500;">{get_friendly_folder_name(current_path)}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Up One Level action
    if cur_p.parent != cur_p and cur_p.parent.exists():
        if st.button(f"↑ Up to {cur_p.parent.name or 'Parent'}", key=f"{key_prefix}_btn_up"):
            st.session_state[session_key] = str(cur_p.parent)
            st.rerun()

    # 3. Subfolders in Current Location
    subfolders: List[Path] = []
    try:
        subfolders = sorted(
            [d for d in cur_p.iterdir() if d.is_dir() and not d.name.startswith(".")],
            key=lambda x: x.name.lower()
        )
    except Exception as exc:
        st.warning(f"Unable to read subfolders: {exc}")

    if subfolders:
        st.markdown("<div style='font-size: 0.80rem; color: #697386; margin: 8px 0 4px 0;'>Subfolders:</div>", unsafe_allow_html=True)
        # Display up to 15 subfolders in a 3-column grid
        display_folders = subfolders[:15]
        cols = st.columns(3)
        for idx, sub_f in enumerate(display_folders):
            col = cols[idx % 3]
            with col:
                if st.button(f"📁 {sub_f.name}", key=f"{key_prefix}_sub_{idx}", use_container_width=True):
                    st.session_state[session_key] = str(sub_f)
                    st.rerun()
        if len(subfolders) > 15:
            st.caption(f"... and {len(subfolders) - 15} more subfolders")
    else:
        st.caption("No subfolders in this location.")

    st.markdown("<hr style='border: none; border-top: 1px solid #E6E2D8; margin: 12px 0;' />", unsafe_allow_html=True)

    # 4. Selection Confirmation Actions
    c_choose, c_direct = st.columns([1.8, 1.2])
    with c_choose:
        if st.button(
            f"Select \"{get_friendly_folder_name(current_path)}\" to Index",
            key=f"{key_prefix}_confirm_folder",
            type="primary",
            use_container_width=True
        ):
            return current_path

    with c_direct:
        # Direct path input
        direct_in = st.text_input(
            "Or paste full path",
            key=f"{key_prefix}_direct_in",
            placeholder="e.g. C:\\Users\\hp\\Documents",
            label_visibility="collapsed"
        )
        if direct_in:
            if os.path.isdir(direct_in):
                if st.button("Go to Path", key=f"{key_prefix}_go_path", use_container_width=True):
                    st.session_state[session_key] = os.path.normpath(direct_in)
                    st.rerun()
            else:
                st.caption("⚠️ Path not found on computer")

    return None


def render_file_browser(
    key_prefix: str = "fls_nav",
    default_path: Optional[str] = None
) -> Optional[List[str]]:
    """
    Render an in-app file browser allowing multi-file selection.
    Returns list of chosen file paths when confirmed, or None.
    """
    session_key = f"{key_prefix}_current_path"
    shortcuts = get_user_shortcuts()

    if session_key not in st.session_state or not st.session_state[session_key]:
        if default_path and os.path.isdir(default_path):
            st.session_state[session_key] = default_path
        elif "Documents" in shortcuts:
            st.session_state[session_key] = shortcuts["Documents"]
        else:
            st.session_state[session_key] = str(Path.cwd())

    current_path = st.session_state[session_key]
    cur_p = Path(current_path)

    # 1. Quick Location Shortcuts
    st.markdown("<div style='font-size: 0.82rem; font-weight: 600; color: #4A5160; margin-bottom: 6px;'>Quick Locations:</div>", unsafe_allow_html=True)
    sc_cols = st.columns(min(len(shortcuts), 5))
    for i, (label, s_path) in enumerate(shortcuts.items()):
        if i >= 5:
            break
        with sc_cols[i]:
            is_active = (s_path == current_path)
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"{key_prefix}_sc_{i}", type=btn_type, use_container_width=True):
                st.session_state[session_key] = s_path
                st.rerun()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # 2. Location & Navigation Up
    st.markdown(
        f"""
        <div style="background: #F7F6F2; border: 1px solid #E6E2D8; border-radius: 6px; padding: 8px 12px; margin-bottom: 10px; font-size: 0.85rem; color: #15181E;">
            <span style="font-weight: 600; color: #1D4ED8; margin-right: 8px;">Folder:</span>
            <span>{get_friendly_folder_name(current_path)}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    if cur_p.parent != cur_p and cur_p.parent.exists():
        if st.button(f"↑ Up to {cur_p.parent.name or 'Parent'}", key=f"{key_prefix}_btn_up"):
            st.session_state[session_key] = str(cur_p.parent)
            st.rerun()

    # 3. List Supported Files
    all_supported_exts = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS
    files_in_dir: List[Path] = []
    subfolders: List[Path] = []

    try:
        for item in cur_p.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_dir():
                subfolders.append(item)
            elif item.is_file() and item.suffix.lower() in all_supported_exts:
                files_in_dir.append(item)
    except Exception as exc:
        st.warning(f"Could not read directory: {exc}")

    # Show Subfolders quickly so user can drill down
    if subfolders:
        with st.expander(f"📁 Subfolders in {cur_p.name} ({len(subfolders)})", expanded=False):
            f_cols = st.columns(3)
            for idx, sf in enumerate(subfolders[:15]):
                with f_cols[idx % 3]:
                    if st.button(f"📁 {sf.name}", key=f"{key_prefix}_sub_{idx}", use_container_width=True):
                        st.session_state[session_key] = str(sf)
                        st.rerun()

    # Files List with checkboxes
    if not files_in_dir:
        st.info("No supported documents or images found directly in this folder. Open a subfolder above to locate files.")
        return None

    st.markdown(
        f"<div style='font-size: 0.85rem; font-weight: 600; color: #15181E; margin: 10px 0 6px 0;'>Select files to add ({len(files_in_dir)} found):</div>",
        unsafe_allow_html=True
    )

    file_options = {
        str(f): f"{f.name} ({format_file_size(f.stat().st_size)})"
        for f in files_in_dir[:30]
    }

    chosen = st.multiselect(
        "Choose files to index",
        options=list(file_options.keys()),
        format_func=lambda x: file_options.get(x, x),
        key=f"{key_prefix}_chosen_files",
        label_visibility="collapsed"
    )

    if chosen:
        if st.button(f"Add {len(chosen)} Selected File(s) to SeekVault", key=f"{key_prefix}_confirm_files", type="primary"):
            return chosen

    return None
