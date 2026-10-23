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
from seekvault.ui.navigator import (
    get_friendly_folder_name,
    inspect_location_for_indexing,
    render_folder_browser,
    render_file_browser,
)


def _inspect_directory(folder_path: str, recursive: bool = True) -> Dict[str, Any]:
    """Inspect directory contents to categorize supported and unsupported formats prior to indexing."""
    res = inspect_location_for_indexing(folder_path, is_folder=True, recursive=recursive)
    return {
        "supported": res["supported"],
        "unsupported": res["unsupported"],
        "total": res["total_files"],
        "by_type": res.get("by_type", {})
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

        # ── Import Mode Switcher ──
        mode = st.radio(
            "Choose what you want to add to SeekVault:",
            options=["Add a Folder", "Add Specific Files"],
            horizontal=True,
            key="lib_import_mode_selector"
        )

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        if mode == "Add a Folder":
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
                    <div style="font-size: 1rem; font-weight: 600; color: #15181E; margin-bottom: 4px;">Choose a Folder to Index</div>
                    <div style="font-size: 0.85rem; color: #4A5160; margin-bottom: 14px;">
                        Browse your computer's folders below. SeekVault will read and index supported documents and images for fast search.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            chosen_fld = render_folder_browser(key_prefix="lib_fld_nav")
            if chosen_fld:
                st.session_state["review_folder_path"] = chosen_fld
                st.session_state["review_files_list"] = None
                st.rerun()

            # Optional Windows dialog
            with st.expander("Open Windows dialog (optional)", expanded=False):
                st.caption("If you prefer the standard Windows folder popup window:")
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
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
                    <div style="font-size: 1rem; font-weight: 600; color: #15181E; margin-bottom: 4px;">Choose Individual Files to Index</div>
                    <div style="font-size: 0.85rem; color: #4A5160; margin-bottom: 14px;">
                        Browse to a folder below and select one or more documents or images to add to your library.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            chosen_fls = render_file_browser(key_prefix="lib_fls_nav")
            if chosen_fls:
                st.session_state["review_files_list"] = chosen_fls
                st.session_state["review_folder_path"] = None
                st.rerun()

            # Optional Windows dialog
            with st.expander("Open Windows dialog (optional)", expanded=False):
                st.caption("If you prefer the standard Windows file popup window:")
                from seekvault.ui.platform import pick_files_dialog
                if st.button("Open Windows File Dialog", key="btn_native_files_lib"):
                    picked = pick_files_dialog("Select documents or images to index")
                    if picked:
                        st.session_state["review_files_list"] = picked
                        st.session_state["review_folder_path"] = None
                        st.rerun()

        # ── Pre-Indexing Review (Folder) ──
        if "review_folder_path" in st.session_state and st.session_state["review_folder_path"]:
            rf_path = st.session_state["review_folder_path"]
            inspect_info = inspect_location_for_indexing(rf_path, is_folder=True, recursive=True)

            if not inspect_info["valid"]:
                st.error(f"Cannot index folder: {inspect_info['error']}")
                if st.button("Dismiss", key="btn_dismiss_fld_err"):
                    st.session_state["review_folder_path"] = None
                    st.rerun()
            else:
                friendly_fld = get_friendly_folder_name(rf_path)
                supported_cnt = len(inspect_info["supported"])
                unsupported_cnt = len(inspect_info["unsupported"])
                total_sz = format_file_size(inspect_info["total_bytes"])

                # Format breakdown summary
                by_type = inspect_info.get("by_type", {})
                breakdown_parts = [f"{cnt} {fmt}" for fmt, cnt in sorted(by_type.items())]
                breakdown_str = ", ".join(breakdown_parts) if breakdown_parts else "None"

                st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
                st.markdown(
                    f"""
                    <div style="background: #FFFFFF; border: 1px solid #BFDBFE; border-left: 4px solid #1D4ED8; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
                        <div style="font-size: 1.05rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
                            Review: {friendly_fld}
                        </div>
                        <div style="font-size: 0.88rem; color: #15181E; line-height: 1.6; margin-bottom: 8px;">
                            Found <strong>{supported_cnt} supported files</strong> ({breakdown_str}) totaling <strong>{total_sz}</strong>.
                            {f'<span style="color: #697386;">({unsupported_cnt} unsupported files will be safely skipped)</span>' if unsupported_cnt > 0 else ''}
                        </div>
                        <div style="font-size: 0.82rem; color: #166534; line-height: 1.4; margin-bottom: 10px;">
                            ✓ <strong>Safe read-only scan:</strong> Your original files on disk will strictly never be moved, altered, or deleted.
                        </div>
                        <details style="margin-top: 6px;">
                            <summary style="font-size: 0.78rem; color: #697386; cursor: pointer;">Show full folder path</summary>
                            <div style="font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.78rem; color: #4A5160; margin-top: 4px; word-break: break-all;">
                                {rf_path}
                            </div>
                        </details>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                c_start_fld, c_cancel_fld = st.columns([1.5, 1])
                with c_start_fld:
                    if st.button(f"Start Indexing {friendly_fld}", key="btn_confirm_index_fld", type="primary"):
                        fid = repo.add_authorized_folder(rf_path, is_recursive=True)
                        prog_bar = st.progress(0)
                        prog_text = st.empty()

                        def _on_progress(idx, total, fname):
                            if total > 0:
                                prog_bar.progress((idx + 1) / total)
                                prog_text.markdown(f"<span style='font-size:0.84rem; color:#4A5160;'>Reading file {idx+1} of {total}: <strong>{fname}</strong></span>", unsafe_allow_html=True)

                        count = pipeline.scan_folder(rf_path, is_recursive=True, progress_callback=_on_progress)
                        watcher.sync_watches()
                        prog_bar.empty()
                        prog_text.empty()
                        st.success(f"Successfully indexed {count} file(s) from '{friendly_fld}'.")
                        st.session_state["review_folder_path"] = None
                        st.rerun()

                with c_cancel_fld:
                    if st.button("Cancel", key="btn_cancel_fld"):
                        st.session_state["review_folder_path"] = None
                        st.rerun()

        # ── Pre-Indexing Review (Individual Files) ──
        if "review_files_list" in st.session_state and st.session_state["review_files_list"]:
            flist = st.session_state["review_files_list"]
            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #BFDBFE; border-left: 4px solid #1D4ED8; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
                    <div style="font-size: 1.05rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
                        Review Selected Files
                    </div>
                    <div style="font-size: 0.88rem; color: #15181E; line-height: 1.6; margin-bottom: 8px;">
                        Ready to index <strong>{len(flist)}</strong> individual file(s).
                    </div>
                    <div style="font-size: 0.82rem; color: #166534; line-height: 1.4; margin-bottom: 10px;">
                        ✓ <strong>Safe read-only scan:</strong> Your original files on disk will strictly never be moved, altered, or deleted.
                    </div>
                    <details style="margin-top: 6px;">
                        <summary style="font-size: 0.78rem; color: #697386; cursor: pointer;">Show selected file names</summary>
                        <ul style="font-size: 0.80rem; color: #4A5160; margin: 6px 0 0 16px; padding: 0;">
                            {''.join([f'<li>{Path(f).name}</li>' for f in flist])}
                        </ul>
                    </details>
                </div>
                """,
                unsafe_allow_html=True
            )

            c_start_fls, c_cancel_fls = st.columns([1.5, 1])
            with c_start_fls:
                if st.button(f"Start Indexing {len(flist)} File(s)", key="btn_confirm_index_fls", type="primary"):
                    indexed = 0
                    prog_bar = st.progress(0)
                    prog_text = st.empty()

                    for idx, fp in enumerate(flist):
                        p = Path(fp)
                        prog_bar.progress((idx + 1) / len(flist))
                        prog_text.markdown(f"<span style='font-size:0.84rem; color:#4A5160;'>Indexing file {idx+1} of {len(flist)}: <strong>{p.name}</strong></span>", unsafe_allow_html=True)
                        parent_dir = str(p.parent)
                        if not repo.is_path_authorized(str(p)):
                            repo.add_authorized_folder(parent_dir, is_recursive=False)
                        res = pipeline.process_file(str(p))
                        if res and res.get("status") == "INDEXED":
                            indexed += 1

                    watcher.sync_watches()
                    prog_bar.empty()
                    prog_text.empty()
                    st.success(f"Successfully indexed {indexed} file(s).")
                    st.session_state["review_files_list"] = None
                    st.rerun()

            with c_cancel_fls:
                if st.button("Cancel", key="btn_cancel_fls"):
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
                f_name = get_friendly_folder_name(f_path)
                is_rec = bool(f.get("is_recursive", 1))
                counts = folder_counts.get(fid, {"indexed": 0, "failed": 0, "pending": 0})

                with st.container():
                    c_info, c_actions = st.columns([3.8, 1.2])

                    with c_info:
                        st.markdown(
                            f"""
                            <div style="font-size: 0.96rem; font-weight: 600; color: #15181E;">
                                📁 {f_name}
                            </div>
                            <div style="font-size: 0.80rem; color: #4A5160; margin: 2px 0 4px 0;">
                                <strong>{counts['indexed']} file(s) ready to search</strong> &nbsp;•&nbsp; {'Subfolders included' if is_rec else 'Direct folder only'}
                                {f" &nbsp;•&nbsp; <span style='color:#B42318;'>{counts['failed']} couldn't be read</span>" if counts['failed'] > 0 else ""}
                            </div>
                            <details style="margin: 0;">
                                <summary style="font-size: 0.76rem; color: #697386; cursor: pointer;">Folder location details</summary>
                                <div style="font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.74rem; color: #4A5160; margin-top: 2px; word-break: break-all;">
                                    {f_path}
                                </div>
                            </details>
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
