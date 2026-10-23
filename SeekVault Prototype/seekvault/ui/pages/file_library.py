import streamlit as st
import os
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional

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
from seekvault.ui.platform import pick_folder_dialog, pick_files_dialog


def _inspect_directory(folder_path: str, recursive: bool = True) -> Dict[str, Any]:
    """Inspect directory contents to categorize supported and unsupported formats prior to indexing."""
    supported = []
    unsupported = []
    all_supported_exts = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS

    p = Path(folder_path)
    if not p.exists() or not p.is_dir():
        return {"supported": [], "unsupported": [], "total": 0}

    pattern = "**/*" if recursive else "*"
    try:
        candidates = list(p.glob(pattern))
    except Exception:
        candidates = []

    for c in candidates:
        if c.is_file():
            ext = c.suffix.lower()
            if ext in all_supported_exts:
                supported.append(c)
            else:
                unsupported.append(c)

    return {
        "supported": supported,
        "unsupported": unsupported,
        "total": len(supported) + len(unsupported)
    }


def render_my_files_page(
    repo: Repository,
    pipeline: IngestionPipeline,
    watcher: WatcherManager
):
    """Render the professional My Files workspace."""
    inject_design_system()

    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h1 style="font-size: 1.85rem; font-weight: 700; color: #15181E; margin: 0 0 4px 0; letter-spacing: -0.015em;">
                My Files
            </h1>
            <p style="font-size: 0.90rem; color: #4A5160; margin: 0; line-height: 1.4;">
                Manage authorized local folders, review files before indexing, and inspect your library status.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_folders, tab_files = st.tabs(["Authorized Folders", "Indexed Library"])

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 1: AUTHORIZED FOLDERS & IMPORT
    # ═════════════════════════════════════════════════════════════════════════
    with tab_folders:
        # Non-destruction assurance banner
        st.markdown(
            """
            <div style="background-color: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 14px 18px; margin-bottom: 18px;">
                <div style="font-size: 0.88rem; color: #15181E; font-weight: 600; margin-bottom: 2px;">
                    Local-Only, Non-Destructive Storage
                </div>
                <div style="font-size: 0.84rem; color: #4A5160; line-height: 1.5;">
                    SeekVault scans and indexes files in read-only mode. 
                    <strong>Your original physical files on disk are strictly never deleted, moved, or altered.</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # ── Folder Import Controls ──
        c_add_fld, c_add_fls = st.columns(2)

        with c_add_fld:
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 16px; height: 100%;">
                    <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 4px;">Authorize Folder</div>
                    <div style="font-size: 0.82rem; color: #4A5160; margin-bottom: 12px;">Select a local folder to monitor and index its supported documents and images.</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("Browse Folder on Windows...", key="btn_browse_folder_main", type="primary"):
                picked = pick_folder_dialog("Select folder to authorize for SeekVault")
                if picked:
                    st.session_state["review_folder_path"] = picked
                    st.rerun()

            fld_in = st.text_input("Or enter folder path:", key="input_lib_folder_path", placeholder=r"e.g. C:\Users\hp\Documents")
            if st.button("Select Folder Path", key="btn_select_lib_folder"):
                if fld_in and os.path.isdir(fld_in):
                    st.session_state["review_folder_path"] = os.path.normpath(fld_in)
                    st.rerun()
                else:
                    st.error("Directory not found on disk.")

        with c_add_fls:
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 16px; height: 100%;">
                    <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 4px;">Add Individual Files</div>
                    <div style="font-size: 0.82rem; color: #4A5160; margin-bottom: 12px;">Select one or more documents or images from anywhere on your PC to index.</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("Browse Files on Windows...", key="btn_browse_files_main"):
                picked_files = pick_files_dialog("Select documents or images to index")
                if picked_files:
                    st.session_state["review_files_list"] = picked_files
                    st.rerun()

            file_in = st.text_input("Or enter file path:", key="input_lib_file_path", placeholder=r"e.g. C:\Users\hp\Documents\notes.pdf")
            if st.button("Select File Path", key="btn_select_lib_file"):
                if file_in and os.path.isfile(file_in):
                    st.session_state["review_files_list"] = [os.path.normpath(file_in)]
                    st.rerun()
                else:
                    st.error("File not found on disk.")


        # ── Pre-Indexing Review (Folder) ──
        if "review_folder_path" in st.session_state and st.session_state["review_folder_path"]:
            rf_path = st.session_state["review_folder_path"]
            inspect_info = _inspect_directory(rf_path, recursive=True)

            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #BFDBFE; border-left: 4px solid #1D4ED8; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
                    <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 4px;">Review Folder Before Indexing</div>
                    <div style="font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.82rem; color: #15181E; margin-bottom: 8px;">{rf_path}</div>
                    <div style="font-size: 0.85rem; color: #4A5160; line-height: 1.5;">
                        Found <strong>{inspect_info['total']}</strong> items: 
                        <strong style="color: #166534;">{len(inspect_info['supported'])} supported</strong> documents and images ready to index, 
                        <span style="color: #697386;">{len(inspect_info['unsupported'])} unsupported formats</span> will be skipped.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            c_start_fld, c_cancel_fld = st.columns([1.5, 1])
            with c_start_fld:
                if st.button("Start Indexing Folder", key="btn_confirm_index_fld", type="primary"):
                    with st.spinner(f"Indexing '{Path(rf_path).name}'..."):
                        fid = repo.add_authorized_folder(rf_path, is_recursive=True)
                        count = pipeline.scan_folder(rf_path, is_recursive=True)
                        watcher.sync_watches()
                    st.success(f"Indexed {count} supported file(s) from '{Path(rf_path).name}'.")
                    st.session_state["review_folder_path"] = None
                    st.rerun()
            with c_cancel_fld:
                if st.button("Cancel Import", key="btn_cancel_fld"):
                    st.session_state["review_folder_path"] = None
                    st.rerun()

        # ── Pre-Indexing Review (Individual Files) ──
        if "review_files_list" in st.session_state and st.session_state["review_files_list"]:
            flist = st.session_state["review_files_list"]
            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #BFDBFE; border-left: 4px solid #1D4ED8; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
                    <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 4px;">Review Files Before Indexing</div>
                    <div style="font-size: 0.85rem; color: #4A5160; line-height: 1.5;">
                        Selected <strong>{len(flist)}</strong> file(s) for indexing.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            c_start_fls, c_cancel_fls = st.columns([1.5, 1])
            with c_start_fls:
                if st.button("Start Indexing Files", key="btn_confirm_index_fls", type="primary"):
                    indexed = 0
                    with st.spinner("Indexing selected files..."):
                        for fp in flist:
                            p = Path(fp)
                            parent_dir = str(p.parent)
                            if not repo.is_path_authorized(str(p)):
                                repo.add_authorized_folder(parent_dir, is_recursive=False)
                            res = pipeline.process_file(str(p))
                            if res and res.get("status") == "INDEXED":
                                indexed += 1
                        watcher.sync_watches()
                    st.success(f"Successfully indexed {indexed} file(s).")
                    st.session_state["review_files_list"] = None
                    st.rerun()
            with c_cancel_fls:
                if st.button("Cancel Files Import", key="btn_cancel_fls"):
                    st.session_state["review_files_list"] = None
                    st.rerun()

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # ── Manual Path Entry Fallback Expander ──
        with st.expander("Or enter folder path manually", expanded=False):
            with st.form("manual_folder_form", clear_on_submit=True):
                manual_input = st.text_input("Absolute folder path", placeholder=r"C:\Users\Documents\Research")
                rec_check = st.checkbox("Include subfolders (recursive)", value=True)
                submitted_manual = st.form_submit_button("Authorize Folder")
                if submitted_manual:
                    raw = manual_input.strip()
                    if not raw:
                        st.error("Please provide a folder path.")
                    elif not os.path.isabs(raw):
                        st.error(f"Path must be absolute: `{raw}`")
                    elif not os.path.exists(raw):
                        st.error(f"Directory not found on disk: `{raw}`")
                    else:
                        fid = repo.add_authorized_folder(raw, is_recursive=rec_check)
                        count = pipeline.scan_folder(raw, is_recursive=rec_check)
                        watcher.sync_watches()
                        st.success(f"Authorized '{Path(raw).name}' and indexed {count} file(s).")
                        st.rerun()

        # ── Confirmation State for Removing a Folder ──
        if "pending_revoke_folder_id" in st.session_state and st.session_state["pending_revoke_folder_id"] is not None:
            folder_id = st.session_state["pending_revoke_folder_id"]
            folder_path = st.session_state.get("pending_revoke_folder_path", "")

            st.markdown(
                f"""
                <div style="background: #FEF2F2; border: 1px solid #FECACA; border-left: 4px solid #B42318; border-radius: 8px; padding: 16px; margin: 16px 0;">
                    <div style="font-size: 0.95rem; font-weight: 600; color: #B42318; margin-bottom: 4px;">Confirm Removing Folder from SeekVault</div>
                    <div style="font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.82rem; color: #15181E; margin-bottom: 8px;">{folder_path}</div>
                    <div style="font-size: 0.84rem; color: #4A5160; line-height: 1.5;">
                        This removes the folder and its files from SeekVault's search index. 
                        <strong>Your original files on disk will strictly NOT be deleted, moved, or altered.</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            c_yes_del, c_no_del = st.columns([1.5, 1])
            with c_yes_del:
                if st.button("Remove from Index", key="btn_confirm_revoke", type="primary"):
                    repo.remove_authorized_folder(folder_id)
                    watcher.sync_watches()
                    st.session_state["pending_revoke_folder_id"] = None
                    st.session_state["pending_revoke_folder_path"] = ""
                    st.success("Folder removed from index. Physical files on disk remain untouched.")
                    st.rerun()
            with c_no_del:
                if st.button("Cancel", key="btn_cancel_revoke"):
                    st.session_state["pending_revoke_folder_id"] = None
                    st.session_state["pending_revoke_folder_path"] = ""
                    st.rerun()

        # ── Currently Authorized Folders List ──
        st.markdown(
            """
            <div style="font-size: 1.1rem; font-weight: 600; color: #15181E; margin: 20px 0 10px 0;">
                Authorized Folders
            </div>
            """,
            unsafe_allow_html=True
        )

        auth_folders = repo.get_authorized_folders()
        folder_counts = repo.get_folder_file_counts()

        if not auth_folders:
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px dashed #D1CBC0; border-radius: 8px; padding: 24px; text-align: center; color: #4A5160;">
                    No authorized folders configured. Use the buttons above to authorize a folder or add files.
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            for f in auth_folders:
                fid = f["id"]
                f_path = f["folder_path"]
                f_name = Path(f_path).name or f_path
                is_rec = bool(f.get("is_recursive", 1))
                counts = folder_counts.get(fid, {"indexed": 0, "failed": 0, "pending": 0})

                with st.container():
                    c_info, c_actions = st.columns([3.8, 1.2])

                    with c_info:
                        st.markdown(
                            f"""
                            <div style="font-size: 0.95rem; font-weight: 600; color: #15181E;">
                                {f_name}
                            </div>
                            <div style="font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.74rem; color: #697386;">
                                {f_path}
                            </div>
                            <div style="font-size: 0.78rem; color: #4A5160; margin-top: 3px;">
                                {counts['indexed']} indexed &nbsp;•&nbsp; {'Recursive' if is_rec else 'Direct only'}
                                {f" &nbsp;•&nbsp; <span style='color:#B42318;'>{counts['failed']} failed</span>" if counts['failed'] > 0 else ""}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    with c_actions:
                        c_rescan, c_revoke = st.columns(2)
                        with c_rescan:
                            if st.button("Re-scan", key=f"fld_rescan_{fid}", use_container_width=True):
                                if os.path.exists(f_path):
                                    with st.spinner("Scanning..."):
                                        c = pipeline.scan_folder(f_path, is_recursive=is_rec)
                                    watcher.sync_watches()
                                    st.success(f"Synced {c} file(s).")
                                    st.rerun()
                                else:
                                    st.error("Folder no longer exists on disk.")

                        with c_revoke:
                            if st.button("Remove", key=f"fld_revoke_{fid}", use_container_width=True):
                                st.session_state["pending_revoke_folder_id"] = fid
                                st.session_state["pending_revoke_folder_path"] = f_path
                                st.rerun()

                    st.markdown("<hr style='border: none; border-top: 1px solid #E6E2D8; margin: 10px 0 12px 0;' />", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 2: INDEXED LIBRARY INSPECTOR
    # ═════════════════════════════════════════════════════════════════════════
    with tab_files:
        st.markdown(
            """
            <div style="font-size: 1.1rem; font-weight: 600; color: #15181E; margin: 10px 0 10px 0;">
                Indexed Files Registry
            </div>
            """,
            unsafe_allow_html=True
        )

        # Filter bar
        fc1, fc2, fc3, fc4 = st.columns([1.8, 1.2, 1.2, 1.2])

        with fc1:
            kw_filter = st.text_input("Filter by filename", placeholder="Type to filter...", label_visibility="collapsed")
        with fc2:
            type_sel = st.selectbox("Format", ["All Formats", "Documents", "Images"], label_visibility="collapsed")
        with fc3:
            status_sel = st.selectbox("Status", ["All Statuses", "INDEXED", "FAILED", "PENDING"], label_visibility="collapsed")
        with fc4:
            sort_sel = st.selectbox("Sort", ["Modified (Newest)", "Name (A-Z)", "Size (Largest)"], label_visibility="collapsed")

        # Map filters
        f_type = None
        if type_sel == "Documents":
            f_type = "DOCUMENT"
        elif type_sel == "Images":
            f_type = "IMAGE"

        f_status = None if status_sel == "All Statuses" else status_sel

        # Retrieve files
        all_files = repo.get_all_indexed_files(limit=1000, file_type=f_type)

        if f_status:
            all_files = [f for f in all_files if f.get("status") == f_status]

        if kw_filter and kw_filter.strip():
            term = kw_filter.strip().lower()
            all_files = [f for f in all_files if term in f.get("file_name", "").lower() or term in f.get("file_path", "").lower()]

        # Sort
        if "Name" in sort_sel:
            all_files.sort(key=lambda x: x.get("file_name", "").lower())
        elif "Size" in sort_sel:
            all_files.sort(key=lambda x: x.get("file_size", 0), reverse=True)
        else:
            all_files.sort(key=lambda x: x.get("modified_at") or "", reverse=True)

        st.markdown(
            f"""
            <div style="font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.76rem; color: #697386; margin-bottom: 12px;">
                DISPLAYING {len(all_files)} FILE(S)
            </div>
            """,
            unsafe_allow_html=True
        )

        if not all_files:
            st.info("No files match the selected filter criteria.")
        else:
            for idx, file_rec in enumerate(all_files, 1):
                f_id = file_rec["id"]
                f_name = file_rec["file_name"]
                f_path = file_rec["file_path"]
                f_size = format_file_size(file_rec.get("file_size", 0))
                f_mod = file_rec.get("modified_at", "Unknown")
                f_stat = file_rec.get("status", "INDEXED")

                with st.container():
                    col_item_info, col_item_btn1, col_item_btn2, col_item_btn3 = st.columns([3.5, 0.7, 1.0, 0.9])

                    with col_item_info:
                        st.markdown(
                            f"""
                            <div style="font-size: 0.92rem; font-weight: 600; color: #15181E;">
                                {f_name}
                            </div>
                            <div style="font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.72rem; color: #697386; word-break: break-all;">
                                {f_path}
                            </div>
                            <div style="font-size: 0.75rem; color: #4A5160; margin-top: 2px;">
                                {f_size} &nbsp;•&nbsp; Modified {f_mod} &nbsp;•&nbsp; Status: <strong>{f_stat}</strong>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    with col_item_btn1:
                        if st.button("Open", key=f"lib_open_{f_id}_{idx}", use_container_width=True):
                            ok, msg = open_file_in_os(f_path)
                            if not ok:
                                st.warning(msg)

                    with col_item_btn2:
                        if st.button("Reveal in Explorer", key=f"lib_reveal_{f_id}_{idx}", use_container_width=True):
                            ok, msg = open_folder_in_os(f_path)
                            if not ok:
                                st.warning(msg)

                    with col_item_btn3:
                        if st.button("Remove", key=f"lib_remove_{f_id}_{idx}", use_container_width=True):
                            pipeline.remove_file(f_path)
                            st.success(f"Removed '{f_name}' from index.")
                            st.rerun()

                    st.markdown("<hr style='border: none; border-top: 1px solid #E6E2D8; margin: 8px 0 10px 0;' />", unsafe_allow_html=True)


# Backwards compatibility alias
render_file_library_page = render_my_files_page
