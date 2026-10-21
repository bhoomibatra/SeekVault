import streamlit as st
import os
from pathlib import Path
from seekvault.database.repository import Repository
from seekvault.ingestion.pipeline import IngestionPipeline
from seekvault.monitoring.watcher import WatcherManager

def render_folders_page(repo: Repository, pipeline: IngestionPipeline, watcher: WatcherManager):
    st.header("📁 Authorized Folders Management")
    st.markdown("Control exactly which directories SeekVault is permitted to access, index, and monitor.")

    # Quick Setup Helper for College Demonstration
    with st.expander("⚡ Quick Setup for Demo (Click to add sample folders)", expanded=True):
        st.markdown("Quickly load curated test datasets included with the SeekVault prototype:")
        base_sample = Path(__file__).resolve().parent.parent.parent.parent / "sample_data"

        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button("➕ Academic Notes", use_container_width=True):
                p = base_sample / "authorized_academic"
                repo.add_authorized_folder(str(p))
                pipeline.scan_folder(str(p))
                watcher.sync_watches()
                st.success("Added & Indexed Academic Notes!")
                st.rerun()

        with b2:
            if st.button("➕ Personal & PII Forms", use_container_width=True):
                p = base_sample / "authorized_personal"
                repo.add_authorized_folder(str(p))
                pipeline.scan_folder(str(p))
                watcher.sync_watches()
                st.success("Added & Indexed Personal Forms!")
                st.rerun()

        with b3:
            if st.button("➕ Sample Images", use_container_width=True):
                p = base_sample / "authorized_images"
                repo.add_authorized_folder(str(p))
                pipeline.scan_folder(str(p))
                watcher.sync_watches()
                st.success("Added & Indexed Images!")
                st.rerun()

        with b4:
            if st.button("➕ Versions & Duplicates", use_container_width=True):
                p = base_sample / "authorized_versions"
                repo.add_authorized_folder(str(p))
                pipeline.scan_folder(str(p))
                watcher.sync_watches()
                st.success("Added & Indexed Versions!")
                st.rerun()

    st.markdown("---")

    # Add Custom Folder Section
    st.subheader("Add New Folder")
    with st.form("add_folder_form"):
        col_in, col_rec, col_btn = st.columns([3, 1, 1])
        with col_in:
            folder_input = st.text_input("Folder Path:", placeholder="e.g. C:\\Users\\hp\\Documents\\Notes")
        with col_rec:
            is_recursive = st.checkbox("Recursive", value=True)
        with col_btn:
            submitted = st.form_submit_button("Authorize Folder")

        if submitted and folder_input.strip():
            clean_path = os.path.normpath(folder_input.strip())
            if not os.path.exists(clean_path):
                st.error(f"Error: Path does not exist on disk: {clean_path}")
            elif not os.path.isdir(clean_path):
                st.error(f"Error: Path is not a directory: {clean_path}")
            else:
                repo.add_authorized_folder(clean_path, is_recursive=is_recursive)
                with st.spinner(f"Ingesting files from {clean_path}..."):
                    count = pipeline.scan_folder(clean_path, is_recursive=is_recursive)
                watcher.sync_watches()
                st.success(f"Authorized folder successfully! Ingested {count} files.")
                st.rerun()

    # List of Authorized Folders
    st.subheader("Authorized Locations")
    folders = repo.get_authorized_folders()

    if not folders:
        st.info("No authorized folders yet. Use the buttons above or enter a folder path to get started.")
    else:
        for f in folders:
            with st.container():
                c_status, c_path, c_rec, c_actions = st.columns([0.8, 3.5, 1, 2])
                with c_status:
                    active = bool(f["is_active"])
                    toggle = st.toggle("Active", value=active, key=f"toggle_auth_{f['id']}")
                    if toggle != active:
                        repo.set_folder_active_state(f["id"], toggle)
                        watcher.sync_watches()
                        st.rerun()

                with c_path:
                    st.markdown(f"**`{f['folder_path']}`**")
                    st.caption(f"Added: {f['added_at']}")

                with c_rec:
                    st.caption("Subfolders: Yes" if f["is_recursive"] else "Subfolders: No")

                with c_actions:
                    col_scan, col_del = st.columns(2)
                    with col_scan:
                        if st.button("🔄 Rescan", key=f"scan_btn_{f['id']}"):
                            with st.spinner("Rescanning..."):
                                count = pipeline.scan_folder(f["folder_path"], is_recursive=bool(f["is_recursive"]))
                            st.success(f"Synced {count} files!")
                            st.rerun()
                    with col_del:
                        if st.button("🗑️ Remove", key=f"del_btn_{f['id']}"):
                            repo.remove_authorized_folder(f["id"])
                            watcher.sync_watches()
                            st.warning("Folder authorization revoked.")
                            st.rerun()

                st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
