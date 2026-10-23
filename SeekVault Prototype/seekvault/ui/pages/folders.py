import streamlit as st
import os
from pathlib import Path
from seekvault.database.repository import Repository
from seekvault.ingestion.pipeline import IngestionPipeline
from seekvault.monitoring.watcher import WatcherManager


def render_folders_page(repo: Repository, pipeline: IngestionPipeline, watcher: WatcherManager):
    st.header("📁 File Library & Authorized Folders")
    st.markdown(
        "Control exactly which directories SeekVault is permitted to access, index, and monitor. "
        "Revoking a folder removes it from search immediately — **it never deletes your files on disk.**"
    )

    # ── Add Folder Section ──────────────────────────────────────────────────────
    st.subheader("Add Folder to Vault")

    with st.form("add_folder_form", clear_on_submit=True):
        folder_input = st.text_input(
            "Folder Path",
            placeholder=r"e.g. D:\Documents\Projects  or  C:\Work\Notes",
            help="Enter the full absolute path to a directory on this machine."
        )
        col_rec, col_submit = st.columns([2, 1])
        with col_rec:
            is_recursive = st.checkbox(
                "Include sub-folders (recursive)",
                value=True,
                help="When enabled, all files inside nested directories are also indexed."
            )
        with col_submit:
            submitted = st.form_submit_button("➕ Authorize & Index", use_container_width=True, type="primary")

        if submitted:
            raw_path = folder_input.strip()
            if not raw_path:
                st.error("Please enter a folder path.")
            elif not os.path.isabs(raw_path):
                st.error(f"❌ Path must be absolute (e.g. start with a drive letter like C:\\\\). Got: `{raw_path}`")
            elif not os.path.exists(raw_path):
                st.error(f"❌ Path does not exist on disk: `{raw_path}`")
            elif not os.path.isdir(raw_path):
                st.error(f"❌ Path is not a directory: `{raw_path}`")
            else:
                try:
                    repo.add_authorized_folder(raw_path, is_recursive=is_recursive)
                    with st.spinner(f"Indexing files from `{raw_path}`…"):
                        count = pipeline.scan_folder(raw_path, is_recursive=is_recursive)
                    watcher.sync_watches()
                    st.success(f"✅ Authorized and indexed **{count} file(s)** from `{raw_path}`.")
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ Cannot authorize folder: {e}")
                except Exception as e:
                    st.error(f"❌ Unexpected error during indexing: {e}")

    st.markdown("---")

    # ── Revoke Confirmation State ────────────────────────────────────────────────
    # We track a pending revocation request in session_state so we can show
    # a confirmation dialog before destructively removing a folder.
    if "pending_revoke_folder_id" not in st.session_state:
        st.session_state.pending_revoke_folder_id = None
    if "pending_revoke_folder_path" not in st.session_state:
        st.session_state.pending_revoke_folder_path = ""

    if st.session_state.pending_revoke_folder_id is not None:
        folder_id = st.session_state.pending_revoke_folder_id
        folder_path = st.session_state.pending_revoke_folder_path

        with st.container():
            st.warning(
                f"⚠️ **Confirm Revocation**\n\n"
                f"Remove authorization for `{folder_path}`?\n\n"
                f"- All indexed chunks and search vectors for this folder will be removed from SeekVault.\n"
                f"- **Your original files on disk will NOT be deleted or modified.**\n"
                f"- You can re-authorize the folder at any time to re-index it."
            )
            col_yes, col_no, _ = st.columns([1, 1, 4])
            with col_yes:
                if st.button("✅ Yes, Revoke", type="primary", use_container_width=True):
                    repo.remove_authorized_folder(folder_id)
                    watcher.sync_watches()
                    st.session_state.pending_revoke_folder_id = None
                    st.session_state.pending_revoke_folder_path = ""
                    st.success("Folder authorization revoked. Your files on disk are untouched.")
                    st.rerun()
            with col_no:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.pending_revoke_folder_id = None
                    st.session_state.pending_revoke_folder_path = ""
                    st.rerun()

        st.markdown("---")

    # ── Authorized Folders List ──────────────────────────────────────────────────
    st.subheader("Authorized Locations")
    folders = repo.get_authorized_folders()
    folder_counts = repo.get_folder_file_counts()

    if not folders:
        st.info(
            "👋 **No authorized folders configured.**\n\n"
            "SeekVault only indexes directories you explicitly authorize. "
            "Enter an absolute folder path above to get started."
        )
    else:
        for f in folders:
            fid = f["id"]
            active = bool(f["is_active"])
            counts = folder_counts.get(fid, {"indexed": 0, "failed": 0, "pending": 0})

            with st.container():
                c_status, c_info, c_actions = st.columns([0.7, 4, 2.5])

                with c_status:
                    toggle = st.toggle(
                        "Active" if active else "Paused",
                        value=active,
                        key=f"toggle_auth_{fid}",
                        help="Pausing stops new indexing and suppresses this folder's files from search results."
                    )
                    if toggle != active:
                        repo.set_folder_active_state(fid, toggle)
                        watcher.sync_watches()
                        st.rerun()

                with c_info:
                    st.markdown(f"**`{f['folder_path']}`**")
                    sub_label = "✅ Recursive" if f["is_recursive"] else "📄 Top-level only"

                    # Build status summary string
                    status_parts = []
                    if counts["indexed"] > 0:
                        status_parts.append(f"{counts['indexed']} indexed")
                    if counts["pending"] > 0:
                        status_parts.append(f"{counts['pending']} pending")
                    if counts["failed"] > 0:
                        status_parts.append(f"⚠️ {counts['failed']} failed")
                    status_str = " · ".join(status_parts) if status_parts else "No files indexed yet"

                    st.caption(f"{sub_label}  ·  {status_str}  ·  Added: {f['added_at']}")

                    if not active:
                        st.caption("🔴 Paused — search results for this folder are suppressed")

                with c_actions:
                    col_scan, col_del = st.columns(2)
                    with col_scan:
                        if st.button("🔄 Re-scan", key=f"scan_btn_{fid}", use_container_width=True):
                            with st.spinner("Re-scanning…"):
                                count = pipeline.scan_folder(f["folder_path"], is_recursive=bool(f["is_recursive"]))
                            watcher.sync_watches()
                            st.success(f"Synced {count} file(s).")
                            st.rerun()
                    with col_del:
                        if st.button("🗑️ Revoke", key=f"del_btn_{fid}", use_container_width=True):
                            # Request confirmation — do NOT remove on a single click
                            st.session_state.pending_revoke_folder_id = fid
                            st.session_state.pending_revoke_folder_path = f["folder_path"]
                            st.rerun()

                st.markdown("<hr style='margin: 6px 0; border-color: #24324D;'>", unsafe_allow_html=True)
