import streamlit as st
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict

from seekvault.config import DOCUMENT_EXTENSIONS, IMAGE_EXTENSIONS
from seekvault.database.repository import Repository
from seekvault.ingestion.pipeline import IngestionPipeline
from seekvault.monitoring.watcher import WatcherManager
from seekvault.ui.components import (
    render_tier_badge,
    format_file_size,
    open_file_in_os,
    open_folder_in_os,
    inject_design_system,
)
from seekvault.ui.navigator import (
    get_friendly_folder_name,
    inspect_location_for_indexing,
    render_folder_browser,
    render_file_browser,
)

_PAGE_SIZE = 50


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _inspect_directory(folder_path: str, recursive: bool = True) -> Dict[str, Any]:
    res = inspect_location_for_indexing(folder_path, is_folder=True, recursive=recursive)
    return {
        "supported": res["supported"],
        "unsupported": res["unsupported"],
        "total": res["total_files"],
        "by_type": res.get("by_type", {}),
    }


def _format_badge(ext: str) -> str:
    """Colored format emblem for a file extension."""
    ext = (ext or "").lower().lstrip(".")
    configs = {
        "pdf":  ("FEE2E2", "B42318", "FECACA"),
        "docx": ("EFF6FF", "1D4ED8", "BFDBFE"),
        "doc":  ("EFF6FF", "1D4ED8", "BFDBFE"),
        "txt":  ("F0FDF4", "166534", "BBF7D0"),
        "md":   ("F0FDF4", "166534", "BBF7D0"),
        "jpg":  ("FAF5FF", "6B21A8", "E9D5FF"),
        "jpeg": ("FAF5FF", "6B21A8", "E9D5FF"),
        "png":  ("FAF5FF", "6B21A8", "E9D5FF"),
        "gif":  ("FAF5FF", "6B21A8", "E9D5FF"),
        "bmp":  ("FAF5FF", "6B21A8", "E9D5FF"),
        "webp": ("FAF5FF", "6B21A8", "E9D5FF"),
    }
    bg, fg, border = configs.get(ext, ("F0EEE8", "697386", "D1CBC0"))
    label = ext.upper() if ext else "?"
    return (
        f'<span style="background-color:#{bg};color:#{fg};border:1px solid #{border};'
        f'padding:2px 7px;border-radius:4px;font-size:0.70rem;font-weight:600;'
        f'font-family:\'JetBrains Mono\',Consolas,monospace;letter-spacing:0.03em;">'
        f'{label}</span>'
    )


def _status_dot(status: str) -> str:
    colors = {
        "INDEXED": ("#10B981", "Indexed"),
        "FAILED":  ("#EF4444", "Failed"),
        "PENDING": ("#F59E0B", "Pending"),
    }
    color, label = colors.get(status, ("#697386", status or "Unknown"))
    return (
        f'<span style="display:inline-flex;align-items:center;gap:5px;'
        f'font-size:0.78rem;color:{color};font-weight:600;">'
        f'<span style="width:7px;height:7px;border-radius:50%;'
        f'background:{color};display:inline-block;"></span>{label}</span>'
    )


def _stat_card(value: str, label: str) -> str:
    return (
        f'<div style="background:#FFFFFF;border:1px solid #E6E2D8;border-radius:8px;'
        f'padding:14px 18px;text-align:center;">'
        f'<div style="font-size:1.40rem;font-weight:700;color:#15181E;line-height:1.1;">{value}</div>'
        f'<div style="font-size:0.78rem;color:#697386;margin-top:4px;font-weight:500;">{label}</div>'
        f'</div>'
    )


def _hr() -> None:
    st.markdown(
        "<hr style='border:none;border-top:1px solid #E6E2D8;margin:8px 0 10px 0;'/>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------

def render_my_files_page(
    repo: Repository,
    pipeline: IngestionPipeline,
    watcher: WatcherManager,
):
    """Render the polished My Files workspace."""
    inject_design_system()

    st.markdown(
        """
        <div style="margin-bottom:18px;">
            <h1 style="font-size:1.75rem;font-weight:700;color:#15181E;margin:0 0 4px 0;letter-spacing:-0.015em;">
                My Files
            </h1>
            <p style="font-size:0.88rem;color:#4A5160;margin:0 0 8px 0;line-height:1.4;">
                See all local folders and files currently searchable by SeekVault.
            </p>
            <div style="font-size:0.80rem;color:#697386;background:#F9F8F6;border:1px solid #E6E2D8;border-radius:6px;padding:8px 12px;line-height:1.4;">
                💡 <strong>How it works:</strong> SeekVault creates a local search catalog of your files so you can search their text. 
                Your original files remain in their original folders on your computer and are never moved, edited, or modified.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tab_folders, tab_library = st.tabs(["Monitored Folders", "Searchable Files"])
    with tab_folders:
        _render_folders_tab(repo, pipeline, watcher)
    with tab_library:
        _render_library_tab(repo, pipeline, watcher)



# ---------------------------------------------------------------------------
# Tab 1 — Authorized Folders
# ---------------------------------------------------------------------------

def _render_folders_tab(
    repo: Repository, pipeline: IngestionPipeline, watcher: WatcherManager
) -> None:

    st.markdown(
        """
        <div style="background:#FFFFFF;border:1px solid #E6E2D8;border-radius:8px;
                    padding:14px 18px;margin-bottom:18px;">
            <div style="font-size:0.88rem;color:#15181E;font-weight:600;margin-bottom:2px;">
                Local-Only, Non-Destructive Indexing
            </div>
            <div style="font-size:0.84rem;color:#4A5160;line-height:1.5;">
                SeekVault scans files in read-only mode.
                <strong>Your original files on disk are never deleted, moved, or altered.</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    mode = st.radio(
        "Choose what to add:",
        options=["Add a Folder", "Add Specific Files"],
        horizontal=True,
        key="lib_import_mode_selector",
    )
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    if mode == "Add a Folder":
        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px solid #E6E2D8;border-radius:8px;
                        padding:18px;margin-bottom:16px;">
                <div style="font-size:1rem;font-weight:600;color:#15181E;margin-bottom:4px;">
                    Choose a Folder to Index
                </div>
                <div style="font-size:0.85rem;color:#4A5160;">
                    Browse your folders below. Supported documents and images will be indexed
                    for fast search.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        chosen_fld = render_folder_browser(key_prefix="lib_fld_nav")
        if chosen_fld:
            st.session_state["review_folder_path"] = chosen_fld
            st.session_state["review_files_list"] = None
            st.rerun()

        with st.expander("Open Windows dialog (optional)", expanded=False):
            st.caption("Use the standard Windows folder picker instead:")
            from seekvault.ui.platform import pick_folder_dialog
            if st.button("Open Windows Folder Dialog", key="btn_native_folder_lib"):
                picked = pick_folder_dialog("Select folder to authorize for SeekVault")
                if picked:
                    st.session_state["review_folder_path"] = picked
                    st.session_state["review_files_list"] = None
                    st.rerun()
    else:
        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px solid #E6E2D8;border-radius:8px;
                        padding:18px;margin-bottom:16px;">
                <div style="font-size:1rem;font-weight:600;color:#15181E;margin-bottom:4px;">
                    Choose Individual Files to Index
                </div>
                <div style="font-size:0.85rem;color:#4A5160;">
                    Browse to a folder and select one or more documents or images to add.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        chosen_fls = render_file_browser(key_prefix="lib_fls_nav")
        if chosen_fls:
            st.session_state["review_files_list"] = chosen_fls
            st.session_state["review_folder_path"] = None
            st.rerun()

        with st.expander("Open Windows dialog (optional)", expanded=False):
            st.caption("Use the standard Windows file picker instead:")
            from seekvault.ui.platform import pick_files_dialog
            if st.button("Open Windows File Dialog", key="btn_native_files_lib"):
                picked = pick_files_dialog("Select documents or images to index")
                if picked:
                    st.session_state["review_files_list"] = picked
                    st.session_state["review_folder_path"] = None
                    st.rerun()

    if st.session_state.get("review_folder_path"):
        _render_folder_review(repo, pipeline, watcher)

    if st.session_state.get("review_files_list"):
        _render_files_review(repo, pipeline, watcher)

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    with st.expander("Or enter a folder path manually", expanded=False):
        with st.form("manual_folder_form", clear_on_submit=True):
            manual_input = st.text_input(
                "Absolute folder path",
                placeholder=r"C:\Users\YourName\Documents\Research",
            )
            rec_check = st.checkbox(
                "Include subfolders",
                value=repo.get_setting("default_recursive", "1") == "1"
            )
            if st.form_submit_button("Authorize Folder"):
                raw = manual_input.strip()
                if not raw:
                    st.error("Please provide a folder path.")
                elif not os.path.isabs(raw):
                    st.error(f"Path must be absolute: {raw}")
                elif not os.path.exists(raw):
                    st.error(f"Folder not found on disk: {raw}")
                else:
                    repo.add_authorized_folder(raw, is_recursive=rec_check)
                    count = pipeline.scan_folder(raw, is_recursive=rec_check)
                    watcher.sync_watches()
                    st.success(f"Authorized and indexed {count} file(s) from '{Path(raw).name}'.")
                    st.rerun()

    if st.session_state.get("pending_revoke_folder_id") is not None:
        _render_revoke_confirm(repo, watcher)

    _render_authorized_folders_list(repo, pipeline, watcher)


def _render_folder_review(
    repo: Repository, pipeline: IngestionPipeline, watcher: WatcherManager
) -> None:
    rf_path = st.session_state["review_folder_path"]
    inspect_info = inspect_location_for_indexing(rf_path, is_folder=True, recursive=True)

    if not inspect_info["valid"]:
        st.error(f"Cannot index folder: {inspect_info['error']}")
        if st.button("Dismiss", key="btn_dismiss_fld_err"):
            st.session_state["review_folder_path"] = None
            st.rerun()
        return

    friendly_fld  = get_friendly_folder_name(rf_path)
    supported_cnt = len(inspect_info["supported"])
    unsupported_cnt = len(inspect_info["unsupported"])
    total_sz = format_file_size(inspect_info["total_bytes"])
    by_type  = inspect_info.get("by_type", {})
    breakdown_str = (
        ", ".join(f"{cnt} {fmt}" for fmt, cnt in sorted(by_type.items())) or "None"
    )
    unsup_note = (
        f" ({unsupported_cnt} unsupported files will be skipped)"
        if unsupported_cnt > 0 else ""
    )

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="background:#FFFFFF;border:1px solid #BFDBFE;border-left:4px solid #1D4ED8;
                    border-radius:8px;padding:18px;margin-bottom:16px;">
            <div style="font-size:1.05rem;font-weight:600;color:#15181E;margin-bottom:6px;">
                Review: {friendly_fld}
            </div>
            <div style="font-size:0.88rem;color:#15181E;line-height:1.6;margin-bottom:8px;">
                <strong>{supported_cnt} supported file(s)</strong> ({breakdown_str}),
                {total_sz} total.{unsup_note}
            </div>
            <div style="font-size:0.82rem;color:#166534;margin-bottom:10px;">
                Safe read-only scan: your original files on disk will never be moved,
                altered, or deleted.
            </div>
            <details>
                <summary style="font-size:0.78rem;color:#697386;cursor:pointer;">
                    Show full path
                </summary>
                <div style="font-family:'JetBrains Mono',Consolas,monospace;
                            font-size:0.78rem;color:#4A5160;margin-top:4px;
                            word-break:break-all;">{rf_path}</div>
            </details>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_start, c_cancel = st.columns([1.5, 1])
    with c_start:
        if st.button(
            f"Start Indexing \u2014 {friendly_fld}",
            key="btn_confirm_index_fld",
            type="primary",
        ):
            is_rec = repo.get_setting("default_recursive", "1") == "1"
            repo.add_authorized_folder(rf_path, is_recursive=is_rec)
            prog_bar  = st.progress(0)
            prog_text = st.empty()

            def _on_progress(idx, total, fname):
                if total > 0:
                    prog_bar.progress((idx + 1) / total)
                    prog_text.markdown(
                        f"<span style='font-size:0.84rem;color:#4A5160;'>"
                        f"Reading {idx + 1}/{total}: <strong>{fname}</strong></span>",
                        unsafe_allow_html=True,
                    )

            count = pipeline.scan_folder(
                rf_path, is_recursive=is_rec, progress_callback=_on_progress
            )
            watcher.sync_watches()
            prog_bar.empty()
            prog_text.empty()
            st.success(f"Indexed {count} file(s) from '{friendly_fld}'.")
            st.session_state["review_folder_path"] = None
            st.rerun()
    with c_cancel:
        if st.button("Cancel", key="btn_cancel_fld"):
            st.session_state["review_folder_path"] = None
            st.rerun()


def _render_files_review(
    repo: Repository, pipeline: IngestionPipeline, watcher: WatcherManager
) -> None:
    flist = st.session_state["review_files_list"]
    total_size = sum(
        Path(fp).stat().st_size for fp in flist if Path(fp).exists()
    )
    file_items = "".join(
        f"<li style='margin-bottom:2px;'><strong>{Path(f).name}</strong> "
        f"<span style='font-size:0.76rem;color:#697386;'>"
        f"({Path(f).suffix.upper().lstrip('.')})</span></li>"
        for f in flist
    )

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="background:#FFFFFF;border:1px solid #BFDBFE;border-left:4px solid #1D4ED8;
                    border-radius:8px;padding:18px;margin-bottom:16px;">
            <div style="font-size:1.05rem;font-weight:600;color:#15181E;margin-bottom:6px;">
                Review Selected Files
            </div>
            <div style="font-size:0.88rem;color:#15181E;margin-bottom:8px;">
                <strong>{len(flist)} file(s)</strong> selected
                ({format_file_size(total_size)} total).
            </div>
            <div style="font-size:0.82rem;color:#166534;margin-bottom:10px;">
                Safe read-only: original files will never be moved, altered, or deleted.
            </div>
            <details>
                <summary style="font-size:0.78rem;color:#697386;cursor:pointer;">
                    Show selected files
                </summary>
                <ul style="font-size:0.80rem;color:#4A5160;margin:6px 0 0 16px;line-height:1.7;">
                    {file_items}
                </ul>
            </details>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_start, c_cancel = st.columns([1.5, 1])
    with c_start:
        if st.button(
            f"Index {len(flist)} File(s)",
            key="btn_confirm_index_fls",
            type="primary",
        ):
            indexed  = 0
            prog_bar  = st.progress(0)
            prog_text = st.empty()
            for idx, fp in enumerate(flist):
                p = Path(fp)
                prog_bar.progress((idx + 1) / len(flist))
                prog_text.markdown(
                    f"<span style='font-size:0.84rem;color:#4A5160;'>"
                    f"Indexing {idx + 1}/{len(flist)}: <strong>{p.name}</strong></span>",
                    unsafe_allow_html=True,
                )
                if not repo.is_path_authorized(str(p)):
                    repo.add_authorized_folder(str(p.parent), is_recursive=False)
                res = pipeline.process_file(str(p))
                if res and res.get("status") == "INDEXED":
                    indexed += 1
            watcher.sync_watches()
            prog_bar.empty()
            prog_text.empty()
            st.success(f"Indexed {indexed} file(s).")
            st.session_state["review_files_list"] = None
            st.rerun()
    with c_cancel:
        if st.button("Cancel", key="btn_cancel_fls"):
            st.session_state["review_files_list"] = None
            st.rerun()


def _render_revoke_confirm(repo: Repository, watcher: WatcherManager) -> None:
    folder_id   = st.session_state["pending_revoke_folder_id"]
    folder_path = st.session_state.get("pending_revoke_folder_path", "")
    st.markdown(
        f"""
        <div style="background:#FEF2F2;border:1px solid #FECACA;border-left:4px solid #B42318;
                    border-radius:8px;padding:16px;margin:16px 0;">
            <div style="font-size:0.95rem;font-weight:600;color:#B42318;margin-bottom:4px;">
                Remove folder from SeekVault?
            </div>
            <div style="font-family:'JetBrains Mono',Consolas,monospace;font-size:0.82rem;
                        color:#15181E;margin-bottom:8px;word-break:break-all;">
                {folder_path}
            </div>
            <div style="font-size:0.84rem;color:#4A5160;line-height:1.5;">
                Removes the folder and its files from the search index.
                <strong>Your original files on disk will not be deleted, moved, or altered.</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c_yes, c_no = st.columns([1.5, 1])
    with c_yes:
        if st.button("Remove from Index", key="btn_confirm_revoke", type="primary"):
            repo.remove_authorized_folder(folder_id)
            watcher.sync_watches()
            st.session_state["pending_revoke_folder_id"]   = None
            st.session_state["pending_revoke_folder_path"] = ""
            st.success("Folder removed. Physical files on disk remain untouched.")
            st.rerun()
    with c_no:
        if st.button("Cancel", key="btn_cancel_revoke"):
            st.session_state["pending_revoke_folder_id"] = None
            st.session_state["pending_revoke_folder_path"] = ""
            st.rerun()


def _render_authorized_folders_list(
    repo: Repository, pipeline: IngestionPipeline, watcher: WatcherManager
) -> None:
    st.markdown(
        "<div style='font-size:1.05rem;font-weight:700;color:#15181E;"
        "margin:24px 0 10px 0;'>Authorized Folders</div>",
        unsafe_allow_html=True,
    )
    auth_folders  = repo.get_authorized_folders()
    folder_counts = repo.get_folder_file_counts()

    if not auth_folders:
        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px dashed #D1CBC0;border-radius:8px;
                        padding:28px;text-align:center;color:#4A5160;font-size:0.88rem;">
                No authorized folders yet. Use the options above to add a folder or files.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for f in auth_folders:
        fid    = f["id"]
        f_path = f["folder_path"]
        f_name = get_friendly_folder_name(f_path)
        is_rec = bool(f.get("is_recursive", 1))
        counts = folder_counts.get(fid, {"indexed": 0, "failed": 0, "pending": 0})

        failed_note  = (
            f" &nbsp;&middot;&nbsp; <span style='color:#B42318;font-weight:600;'>"
            f"{counts['failed']} failed</span>"
            if counts["failed"] > 0 else ""
        )
        pending_note = (
            f" &nbsp;&middot;&nbsp; <span style='color:#92400E;'>"
            f"{counts['pending']} pending</span>"
            if counts["pending"] > 0 else ""
        )
        scope_label = "Subfolders included" if is_rec else "Top folder only"

        with st.container():
            c_info, c_actions = st.columns([3.8, 1.2])
            with c_info:
                st.markdown(
                    f"""
                    <div style="font-size:0.96rem;font-weight:600;color:#15181E;">
                        {f_name}
                    </div>
                    <div style="font-size:0.80rem;color:#4A5160;margin:2px 0 4px 0;">
                        <strong>{counts['indexed']} indexed</strong>
                        &nbsp;&middot;&nbsp; {scope_label}{failed_note}{pending_note}
                    </div>
                    <details style="margin:0;">
                        <summary style="font-size:0.76rem;color:#697386;cursor:pointer;">
                            Folder path
                        </summary>
                        <div style="font-family:'JetBrains Mono',Consolas,monospace;
                                    font-size:0.74rem;color:#4A5160;margin-top:2px;
                                    word-break:break-all;">{f_path}</div>
                    </details>
                    """,
                    unsafe_allow_html=True,
                )
            with c_actions:
                c_r, c_d = st.columns(2)
                with c_r:
                    if st.button("Re-scan", key=f"fld_rescan_{fid}", use_container_width=True):
                        if os.path.exists(f_path):
                            with st.spinner("Scanning..."):
                                c = pipeline.scan_folder(f_path, is_recursive=is_rec)
                            watcher.sync_watches()
                            st.success(f"Synced {c} file(s).")
                            st.rerun()
                        else:
                            st.error("Folder not found on disk.")
                with c_d:
                    if st.button("Remove", key=f"fld_revoke_{fid}", use_container_width=True):
                        st.session_state["pending_revoke_folder_id"]   = fid
                        st.session_state["pending_revoke_folder_path"] = f_path
                        st.rerun()
            _hr()


# ---------------------------------------------------------------------------
# Tab 2 — Indexed Library
# ---------------------------------------------------------------------------

def _render_library_tab(
    repo: Repository, pipeline: IngestionPipeline, watcher: WatcherManager
) -> None:
    all_files    = repo.get_all_indexed_files(limit=2000)
    auth_folders = repo.get_authorized_folders()

    total_files   = len(all_files)
    total_size    = sum(f.get("file_size", 0) or 0 for f in all_files)
    indexed_count = sum(1 for f in all_files if f.get("status") == "INDEXED")
    total_folders = len(auth_folders)

    # --- Summary stats ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(_stat_card(str(total_files), "Total Files"), unsafe_allow_html=True)
    with c2:
        st.markdown(_stat_card(str(indexed_count), "Ready to Search"), unsafe_allow_html=True)
    with c3:
        st.markdown(
            _stat_card(format_file_size(total_size), "Total Size"), unsafe_allow_html=True
        )
    with c4:
        st.markdown(
            _stat_card(str(total_folders), "Authorized Folders"), unsafe_allow_html=True
        )

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

    if total_files == 0:
        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px dashed #D1CBC0;border-radius:8px;
                        padding:36px;text-align:center;color:#4A5160;font-size:0.88rem;">
                No files indexed yet. Go to <strong>Authorized Folders</strong> to add files.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # --- Filter bar ---
    fc1, fc2, fc3, fc4 = st.columns([2.2, 1.3, 1.3, 1.2])
    with fc1:
        kw_filter = st.text_input(
            "Filter",
            placeholder="Search by filename...",
            key="lib_kw_filter",
            label_visibility="collapsed",
        )
    with fc2:
        type_sel = st.selectbox(
            "Type",
            ["All Types", "Documents", "Images"],
            key="lib_type_sel",
            label_visibility="collapsed",
        )
    with fc3:
        tier_sel = st.selectbox(
            "Privacy",
            ["All Tiers", "FULL", "REDACTED", "METADATA_ONLY"],
            key="lib_tier_sel",
            label_visibility="collapsed",
        )
    with fc4:
        sort_sel = st.selectbox(
            "Sort",
            ["Newest First", "Name A-Z", "Largest First"],
            key="lib_sort_sel",
            label_visibility="collapsed",
        )

    # Apply filters
    filtered = list(all_files)
    if type_sel == "Documents":
        filtered = [f for f in filtered if f.get("file_type") == "DOCUMENT"]
    elif type_sel == "Images":
        filtered = [f for f in filtered if f.get("file_type") == "IMAGE"]
    if tier_sel != "All Tiers":
        filtered = [f for f in filtered if f.get("privacy_tier") == tier_sel]
    if kw_filter and kw_filter.strip():
        term = kw_filter.strip().lower()
        filtered = [
            f for f in filtered
            if term in (f.get("file_name") or "").lower()
            or term in (f.get("file_path") or "").lower()
        ]

    # Sort
    if "Name" in sort_sel:
        filtered.sort(key=lambda x: (x.get("file_name") or "").lower())
    elif "Largest" in sort_sel:
        filtered.sort(key=lambda x: x.get("file_size") or 0, reverse=True)
    else:
        filtered.sort(key=lambda x: x.get("indexed_at") or "", reverse=True)

    # Failed files section
    failed_in_view = [f for f in filtered if f.get("status") == "FAILED"]
    base_view = not kw_filter and tier_sel == "All Tiers" and type_sel == "All Types"
    if failed_in_view and base_view:
        with st.expander(
            f"{len(failed_in_view)} file(s) could not be indexed \u2014 click to review",
            expanded=False,
        ):
            for file_rec in failed_in_view:
                _render_file_row(file_rec, repo, pipeline, watcher, show_error=True)
            c_retry, _ = st.columns([1, 3])
            with c_retry:
                if st.button("Retry All Failed", key="btn_retry_all_failed"):
                    repo.reset_pending_files()
                    for ffile in failed_in_view:
                        pipeline.process_file(ffile["file_path"])
                    st.success("Retry complete.")
                    st.rerun()

    # Inline file-removal confirmation
    if st.session_state.get("pending_remove_file_id"):
        _render_file_remove_confirm(repo, pipeline)

    # Main display list (exclude failed)
    display_files = [f for f in filtered if f.get("status") != "FAILED"]
    result_count  = len(display_files)
    filter_active = (
        bool(kw_filter and kw_filter.strip())
        or tier_sel != "All Tiers"
        or type_sel != "All Types"
    )

    _filtered_sfx = "  ·  FILTERED" if filter_active else ""
    _count_html = (
        "<div style='font-family:\"JetBrains Mono\",Consolas,monospace;"
        "font-size:0.76rem;color:#697386;margin-bottom:12px;'>"
        f"SHOWING {result_count} FILE(S){_filtered_sfx}"
        "</div>"
    )
    st.markdown(_count_html, unsafe_allow_html=True)

    if not display_files:
        st.info("No files match the selected filters.")
        return

    # Pagination
    page_key = "lib_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    filter_hash = f"{kw_filter}|{type_sel}|{tier_sel}|{sort_sel}"
    if st.session_state.get("_lib_last_filter") != filter_hash:
        st.session_state[page_key] = 0
        st.session_state["_lib_last_filter"] = filter_hash

    total_pages  = max(1, (result_count + _PAGE_SIZE - 1) // _PAGE_SIZE)
    current_page = max(0, min(st.session_state[page_key], total_pages - 1))
    page_files   = display_files[current_page * _PAGE_SIZE : (current_page + 1) * _PAGE_SIZE]

    # Grouped by folder when no filter is active
    if not filter_active and auth_folders:
        fid_to_path = {f["id"]: f["folder_path"] for f in auth_folders}
        groups: Dict[Optional[int], List] = defaultdict(list)
        for file_rec in page_files:
            groups[file_rec.get("folder_id")].append(file_rec)

        for fid, group in groups.items():
            folder_path = fid_to_path.get(fid, "")
            folder_name = (
                get_friendly_folder_name(folder_path) if folder_path else "Ungrouped"
            )
            grp_indexed = sum(1 for f in group if f.get("status") == "INDEXED")

            st.markdown(
                f"""
                <div style="font-size:0.92rem;font-weight:700;color:#15181E;
                            margin:18px 0 4px 0;">
                    {folder_name}
                    <span style="font-size:0.76rem;font-weight:500;color:#697386;
                                background:#F0EEE8;border:1px solid #E6E2D8;
                                border-radius:4px;padding:2px 8px;margin-left:8px;">
                        {grp_indexed}/{len(group)} indexed
                    </span>
                </div>
                <details style="margin-bottom:6px;">
                    <summary style="font-size:0.74rem;color:#697386;cursor:pointer;">
                        Folder path
                    </summary>
                    <div style="font-family:'JetBrains Mono',Consolas,monospace;
                                font-size:0.74rem;color:#4A5160;margin-top:2px;
                                word-break:break-all;">{folder_path}</div>
                </details>
                """,
                unsafe_allow_html=True,
            )

            for file_rec in group:
                _render_file_row(file_rec, repo, pipeline, watcher)
            _hr()
    else:
        for file_rec in page_files:
            _render_file_row(file_rec, repo, pipeline, watcher)

    # Pagination controls
    if total_pages > 1:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        pg1, pg2, pg3 = st.columns([1, 2, 1])
        with pg1:
            if current_page > 0:
                if st.button(
                    "\u2190 Previous", key="lib_prev_page", use_container_width=True
                ):
                    st.session_state[page_key] = current_page - 1
                    st.rerun()
        with pg2:
            st.markdown(
                f"<div style='text-align:center;font-size:0.84rem;color:#697386;"
                f"padding-top:8px;'>Page {current_page + 1} of {total_pages}</div>",
                unsafe_allow_html=True,
            )
        with pg3:
            if current_page < total_pages - 1:
                if st.button(
                    "Next \u2192", key="lib_next_page", use_container_width=True
                ):
                    st.session_state[page_key] = current_page + 1
                    st.rerun()


# ---------------------------------------------------------------------------
# File row
# ---------------------------------------------------------------------------

def _render_file_row(
    file_rec: Dict[str, Any],
    repo: Repository,
    pipeline: IngestionPipeline,
    watcher: WatcherManager,
    show_error: bool = False,
) -> None:
    f_id   = file_rec["id"]
    f_name = file_rec.get("file_name", "Unknown")
    f_path = file_rec.get("file_path", "")
    f_ext  = file_rec.get("file_extension", "")
    f_size = format_file_size(file_rec.get("file_size", 0) or 0)
    f_mod  = (file_rec.get("modified_at") or "")[:10]
    f_stat = file_rec.get("status", "INDEXED")
    f_tier = file_rec.get("privacy_tier") or ""
    f_err  = file_rec.get("error_detail") or ""

    fmt_badge  = _format_badge(f_ext)
    tier_badge = render_tier_badge(f_tier) if f_tier else ""
    status_h   = _status_dot(f_stat)
    mod_part   = f" &middot; {f_mod}" if f_mod else ""

    with st.container():
        c_info, c_b1, c_b2, c_b3 = st.columns([3.1, 1.1, 1.3, 0.9])
        with c_info:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:8px;
                            flex-wrap:wrap;margin-bottom:2px;">
                    {fmt_badge}
                    <span style="font-size:0.92rem;font-weight:600;color:#15181E;">
                        {f_name}
                    </span>
                </div>
                <div style="font-size:0.78rem;color:#4A5160;display:flex;
                            align-items:center;gap:10px;flex-wrap:wrap;margin:2px 0;">
                    {status_h} {tier_badge}
                    <span style="color:#697386;">{f_size}{mod_part}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if show_error and f_err:
                st.markdown(
                    f"<div style='font-size:0.76rem;color:#B42318;margin-top:2px;"
                    f"font-family:\"JetBrains Mono\",Consolas,monospace;'>"
                    f"{f_err[:250]}</div>",
                    unsafe_allow_html=True,
                )
        with c_b1:
            if st.button("Open File", key=f"lib_open_{f_id}", use_container_width=True):
                ok, msg = open_file_in_os(f_path)
                if not ok:
                    st.warning(msg)
        with c_b2:
            if st.button(
                "Show in Folder", key=f"lib_reveal_{f_id}", use_container_width=True
            ):
                ok, msg = open_folder_in_os(f_path)
                if not ok:
                    st.warning(msg)
        with c_b3:
            if st.button("Remove", key=f"lib_remove_{f_id}", use_container_width=True, help="Remove from search index (file on disk is not deleted)"):
                st.session_state["pending_remove_file_id"]   = f_id
                st.session_state["pending_remove_file_path"] = f_path
                st.session_state["pending_remove_file_name"] = f_name
                st.rerun()

        st.markdown(
            "<hr style='border:none;border-top:1px solid #E6E2D8;margin:8px 0 10px 0;'/>",
            unsafe_allow_html=True,
        )


def _render_file_remove_confirm(repo: Repository, pipeline: IngestionPipeline) -> None:
    f_id   = st.session_state["pending_remove_file_id"]
    f_path = st.session_state.get("pending_remove_file_path", "")
    f_name = st.session_state.get("pending_remove_file_name", "this file")
    st.markdown(
        f"""
        <div style="background:#FEF2F2;border:1px solid #FECACA;border-left:4px solid #B42318;
                    border-radius:8px;padding:16px;margin:12px 0;">
            <div style="font-size:0.95rem;font-weight:600;color:#B42318;margin-bottom:4px;">
                Remove from index?
            </div>
            <div style="font-size:0.88rem;font-weight:600;color:#15181E;margin-bottom:4px;">
                {f_name}
            </div>
            <div style="font-size:0.84rem;color:#4A5160;">
                The file will be removed from search results.
                <strong>The original file on disk will not be deleted or changed.</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c_yes, c_no = st.columns([1.2, 1])
    with c_yes:
        if st.button(
            "Remove from Index", key="btn_confirm_file_remove", type="primary"
        ):
            pipeline.remove_file(f_path)
            st.session_state["pending_remove_file_id"]   = None
            st.session_state["pending_remove_file_path"] = ""
            st.session_state["pending_remove_file_name"] = ""
            st.success(f"'{f_name}' removed from index.")
            st.rerun()
    with c_no:
        if st.button("Cancel", key="btn_cancel_file_remove"):
            st.session_state["pending_remove_file_id"] = None
            st.rerun()


# ---------------------------------------------------------------------------
# Backwards compatibility alias
# ---------------------------------------------------------------------------
render_file_library_page = render_my_files_page
