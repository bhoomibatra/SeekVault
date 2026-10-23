import streamlit as st
import os
import pandas as pd
from pathlib import Path
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


def render_file_library_page(
    repo: Repository,
    pipeline: IngestionPipeline,
    watcher: WatcherManager
):
    inject_design_system()

    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: baseline; justify-content: space-between;">
                <h1 style="font-size: 1.85rem; font-weight: 700; letter-spacing: -0.015em; margin-bottom: 4px; color: #15181E;">
                    File Library & Storage
                </h1>
                <span style="font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.75rem; color: #697386;">
                    Scope: Authorized Directories & Registry
                </span>
            </div>
            <p style="font-size: 0.90rem; color: #4A5160; margin-top: 0; margin-bottom: 12px; line-height: 1.5;">
                Manage authorized local directories and inspect indexed file representations with verifiable privacy boundaries.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_folders, tab_files = st.tabs(["Authorized Locations", "Indexed Files Registry"])

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 1: AUTHORIZED FOLDERS MANAGEMENT
    # ═════════════════════════════════════════════════════════════════════════
    with tab_folders:
        st.markdown(
            """
            <div style="background-color: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 14px 18px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(22, 25, 30, 0.02);">
                <div style="font-size: 0.88rem; color: #15181E; font-weight: 600; margin-bottom: 2px;">
                    Strict Non-Mutation Guarantee
                </div>
                <div style="font-size: 0.84rem; color: #4A5160; line-height: 1.5;">
                    Revoking folder authorization removes files from the search index immediately. 
                    <strong>Your original physical files on disk are strictly never deleted, moved, or altered.</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # ── Revocation Confirmation State ────────────────────────────────────
        if "pending_revoke_folder_id" not in st.session_state:
            st.session_state.pending_revoke_folder_id = None
        if "pending_revoke_folder_path" not in st.session_state:
            st.session_state.pending_revoke_folder_path = ""

        if st.session_state.pending_revoke_folder_id is not None:
            folder_id = st.session_state.pending_revoke_folder_id
            folder_path = st.session_state.pending_revoke_folder_path

            st.warning(
                f"⚠️ **Confirm Authorization Revocation**\n\n"
                f"Are you sure you want to remove authorization for:\n\n"
                f"`{folder_path}`\n\n"
                f"- All search vectors, content previews, and metadata will be purged from SeekVault.\n"
                f"- **Your original source files on disk will NOT be touched or deleted.**\n"
                f"- You can re-authorize this directory at any time."
            )
            col_confirm, col_cancel, _ = st.columns([1.2, 1, 3])
            with col_confirm:
                if st.button("✅ Yes, Revoke Authorization", type="primary", key="confirm_revoke_btn"):
                    repo.remove_authorized_folder(folder_id)
                    watcher.sync_watches()
                    st.session_state.pending_revoke_folder_id = None
                    st.session_state.pending_revoke_folder_path = ""
                    st.success("Authorization safely revoked. Your files on disk remain untouched.")
                    st.rerun()
            with col_cancel:
                if st.button("❌ Cancel", key="cancel_revoke_btn"):
                    st.session_state.pending_revoke_folder_id = None
                    st.session_state.pending_revoke_folder_path = ""
                    st.rerun()

            st.markdown("---")

        # ── Add New Folder ───────────────────────────────────────────────────
        with st.expander("Authorize New Directory", expanded=False):
            with st.form("add_auth_folder_form", clear_on_submit=True):
                folder_input = st.text_input(
                    "Directory Path",
                    placeholder=r"e.g., C:\Users\Documents\Research or D:\Projects\Notes",
                    help="Enter absolute path to a folder on this computer."
                )
                col_rec, col_sub = st.columns([2, 1])
                with col_rec:
                    is_rec = st.checkbox("Include sub-folders (recursive indexing)", value=True)
                with col_sub:
                    submitted = st.form_submit_button("Authorize & Scan", type="primary", use_container_width=True)

                if submitted:
                    raw = folder_input.strip()
                    if not raw:
                        st.error("Please provide a folder path.")
                    elif not os.path.isabs(raw):
                        st.error(f"Path must be absolute. Received: `{raw}`")
                    elif not os.path.exists(raw):
                        st.error(f"Directory does not exist on disk: `{raw}`")
                    elif not os.path.isdir(raw):
                        st.error(f"Path is not a directory: `{raw}`")
                    else:
                        try:
                            repo.add_authorized_folder(raw, is_recursive=is_rec)
                            with st.spinner(f"Scanning and indexing `{raw}`..."):
                                count = pipeline.scan_folder(raw, is_recursive=is_rec)
                            watcher.sync_watches()
                            st.success(f"✅ Authorized and indexed **{count} file(s)** from `{raw}`.")
                            st.rerun()
                        except ValueError as err:
                            st.error(f"Cannot authorize folder: {err}")
                        except Exception as err:
                            st.error(f"Unexpected error during folder indexing: {err}")

        # ── Active Locations List ────────────────────────────────────────────
        st.subheader("Authorized Locations")
        folders = repo.get_authorized_folders()
        folder_counts = repo.get_folder_file_counts()

        if not folders:
            st.info(
                "👋 **No folders currently authorized.** Enter a folder path above to begin indexing your files."
            )
        else:
            for f in folders:
                fid = f["id"]
                active = bool(f["is_active"])
                counts = folder_counts.get(fid, {"indexed": 0, "failed": 0, "pending": 0})

                with st.container():
                    c_status, c_info, c_actions = st.columns([0.8, 3.8, 2.2])

                    with c_status:
                        toggle = st.toggle(
                            "Active" if active else "Paused",
                            value=active,
                            key=f"lib_toggle_{fid}",
                            help="Pausing excludes this folder's files from search results."
                        )
                        if toggle != active:
                            repo.set_folder_active_state(fid, toggle)
                            watcher.sync_watches()
                            st.rerun()

                    with c_info:
                        st.markdown(f"**`{f['folder_path']}`**")
                        rec_label = "Recursive" if f["is_recursive"] else "Top-level only"
                        status_summary = f"{counts['indexed']} indexed"
                        if counts["failed"] > 0:
                            status_summary += f" | <span style='color:#DC2626;'>{counts['failed']} failed</span>"
                        if counts["pending"] > 0:
                            status_summary += f" | <span style='color:#D97706;'>{counts['pending']} pending</span>"

                        st.markdown(
                            f"<span style='font-size:0.80rem; font-family: \"JetBrains Mono\", Consolas, monospace; color:#697386;'>{rec_label} &nbsp;•&nbsp; {status_summary}</span>",
                            unsafe_allow_html=True
                        )

                    with c_actions:
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            if st.button("Re-scan", key=f"lib_rescan_{fid}", use_container_width=True):
                                if os.path.exists(f["folder_path"]):
                                    with st.spinner(f"Re-scanning `{f['folder_path']}`..."):
                                        c = pipeline.scan_folder(f["folder_path"], is_recursive=bool(f["is_recursive"]))
                                    watcher.sync_watches()
                                    st.success(f"Synced {c} file(s).")
                                    st.rerun()
                                else:
                                    st.error("Folder no longer exists on disk.")

                        with btn_col2:
                            if st.button("Revoke", key=f"lib_revoke_{fid}", use_container_width=True):
                                st.session_state.pending_revoke_folder_id = fid
                                st.session_state.pending_revoke_folder_path = f["folder_path"]
                                st.rerun()

                    st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px solid #E6E2D8;'>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 2: INDEXED FILE BROWSER & DEEP INSPECTOR
    # ═════════════════════════════════════════════════════════════════════════
    with tab_files:
        st.subheader("Indexed File Records")

        # Filters row
        fc1, fc2, fc3, fc4 = st.columns([1.5, 1.2, 1.2, 1.5])
        with fc1:
            all_auth_folders = repo.get_authorized_folders()
            f_choices = {"All Folders": None}
            for f in all_auth_folders:
                f_name = Path(f["folder_path"]).name or f["folder_path"]
                f_choices[f"{f_name}"] = f["id"]
            selected_f_label = st.selectbox("Filter Folder", list(f_choices.keys()), index=0)
            sel_folder_id = f_choices[selected_f_label]

        with fc2:
            type_filter = st.selectbox("File Type", ["All", "DOCUMENT", "IMAGE"], index=0)
        with fc3:
            tier_filter = st.selectbox("Privacy Tier", ["All", "FULL", "REDACTED", "METADATA_ONLY"], index=0)
        with fc4:
            search_name = st.text_input("Filter by filename", placeholder="Type filename keyword...")

        f_type = None if type_filter == "All" else type_filter
        f_tier = None if tier_filter == "All" else tier_filter

        # Fetch files from repository
        files = repo.get_all_indexed_files(limit=500, file_type=f_type, privacy_tier=f_tier)

        if sel_folder_id is not None:
            files = [f for f in files if f.get("folder_id") == sel_folder_id]

        if search_name and search_name.strip():
            kw = search_name.strip().lower()
            files = [f for f in files if kw in f.get("file_name", "").lower() or kw in f.get("file_path", "").lower()]

        if not files:
            st.info("No files matching the active filter criteria.")
        else:
            st.markdown(
                f"<div style='margin-bottom: 12px; font-family: \"JetBrains Mono\", Consolas, monospace; font-size: 0.78rem; color: #697386;'>DISPLAYING <strong>{len(files)}</strong> FILE RECORD(S)</div>",
                unsafe_allow_html=True
            )

            # Files Table
            table_rows = []
            for f in files:
                table_rows.append({
                    "File Name": f["file_name"],
                    "Type": f["file_type"],
                    "Extension": f["file_extension"],
                    "Size": format_file_size(f["file_size"]),
                    "Privacy Tier": f["privacy_tier"],
                    "Status": f.get("status", "INDEXED"),
                    "Modified": f["modified_at"],
                })

            st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

            # ── Deep File Inspector ──────────────────────────────────────────
            st.markdown("### File Inspector & Representation")
            file_options = {f"{f['id']}: {f['file_name']} [{f['privacy_tier']}]": f for f in files}
            selected_key = st.selectbox("Select a file to inspect full metadata & privacy status:", list(file_options.keys()))

            if selected_key:
                sel = file_options[selected_key]
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.markdown(f"**Filename:** `{sel['file_name']}`")
                    st.markdown(f"**Canonical Path:** `{sel['file_path']}`")
                    st.markdown(f"**File Hash (SHA-256):** `{sel['file_hash']}`")
                with col_m2:
                    st.markdown(f"**Privacy Tier:** {render_tier_badge(sel['privacy_tier'])}", unsafe_allow_html=True)
                    st.markdown(f"**Indexing Status:** `{sel.get('status', 'INDEXED')}`")
                    st.markdown(f"**Size:** {format_file_size(sel['file_size'])} | **Modified:** {sel['modified_at']}")

                # Action buttons
                btn_c1, btn_c2, _ = st.columns([1, 1.3, 3])
                with btn_c1:
                    if st.button("👁️ Open File", key=f"lib_open_{sel['id']}"):
                        ok, msg = open_file_in_os(sel["file_path"])
                        if not ok:
                            st.warning(msg)
                with btn_c2:
                    if st.button("📂 Reveal in Folder", key=f"lib_folder_{sel['id']}"):
                        ok, msg = open_folder_in_os(sel["file_path"])
                        if not ok:
                            st.warning(msg)

                # Content Preview (Respecting Privacy)
                content = repo.get_file_content(sel["id"])
                if content:
                    st.markdown("**Indexed Representation Preview:**")
                    if sel["privacy_tier"] == "METADATA_ONLY":
                        st.info("🔒 **Content Hidden (METADATA_ONLY)**: Zero content text or vectors are stored in the index.")
                    elif sel["privacy_tier"] == "REDACTED":
                        st.warning("🛡️ **Sensitive PII Masked**: All sensitive identifiers are replaced with masked tokens.")
                        st.code(content.get("redacted_preview", "") or "[No text preview]", language="text")
                    else:
                        st.code(content.get("searchable_text_preview", "") or "[No text preview]", language="text")

                # Detected Entities Audit (Zero Raw PII)
                entities = repo.get_detected_entities_for_file(sel["id"])
                if entities:
                    st.markdown("**Detected Sensitive Entities (De-identified Audit):**")
                    ent_rows = []
                    for e in entities:
                        ent_rows.append({
                            "Category": e.get("entity_type", "UNKNOWN"),
                            "Masked Token": e.get("entity_token", "<REDACTED>"),
                            "Confidence Score": f"{e.get('confidence', 1.0):.2f}",
                        })
                    st.dataframe(pd.DataFrame(ent_rows), use_container_width=True)
