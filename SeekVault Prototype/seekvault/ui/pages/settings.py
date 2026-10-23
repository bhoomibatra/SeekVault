import os
import streamlit as st
from pathlib import Path
from typing import Optional

from seekvault.config import DB_PATH, INDEX_DIR, DATA_DIR
from seekvault.extraction.ocr_extractor import OCRExtractor
from seekvault.database.repository import Repository
from seekvault.search.engine import SearchEngine
from seekvault.database.backup import create_backup, restore_backup
from seekvault.ui.components import inject_design_system


def render_settings_page(repo: Repository, search_engine: SearchEngine):
    """
    Direct, efficient Settings dashboard.
    No essays, no machine learning lectures — practical user preferences only.
    """
    inject_design_system()

    # Clean, concise title
    st.markdown(
        """
        <div style="margin-bottom: 16px;">
            <h1 style="font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-size: 1.65rem; font-weight: 700; color: #15181E; margin: 0 0 4px 0;">
                Settings
            </h1>
            <p style="font-size: 0.88rem; color: #697386; margin: 0;">
                Application preferences, search behavior, and library maintenance.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    c_col1, c_col2 = st.columns([1.1, 1.1], gap="large")

    # ─────────────────────────────────────────────────────────────────────────
    # COLUMN 1: Search & Scanning Preferences
    # ─────────────────────────────────────────────────────────────────────────
    with c_col1:
        st.markdown(
            """
            <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 8px;">
                Search Preferences
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("search_settings_form"):
            current_mode = repo.get_setting("search_mode", "HYBRID")
            search_mode = st.radio(
                "Search Matching",
                ["HYBRID", "KEYWORD_ONLY"],
                index=0 if current_mode == "HYBRID" else 1,
                format_func=lambda m: "Smart Match (Concepts & Keywords)" if m == "HYBRID" else "Exact Words Only",
            )

            current_limit = int(repo.get_setting("search_results_per_page", "25"))
            limit_idx = [10, 25, 50].index(current_limit) if current_limit in [10, 25, 50] else 1
            results_per_page = st.selectbox(
                "Results per search",
                [10, 25, 50],
                index=limit_idx,
            )

            ocr_active = OCRExtractor.is_available()
            enable_ocr = st.checkbox(
                "Read text from screenshots and scans (OCR)",
                value=repo.get_setting("enable_ocr", "1") == "1",
                disabled=not ocr_active,
            )

            show_full_path = st.checkbox(
                "Always display full folder paths",
                value=repo.get_setting("show_full_path", "0") == "1",
            )

            if st.form_submit_button("Save Search Preferences", type="primary", use_container_width=True):
                repo.set_setting("search_mode", search_mode)
                repo.set_setting("search_results_per_page", str(results_per_page))
                repo.set_setting("enable_ocr", "1" if enable_ocr else "0")
                repo.set_setting("show_full_path", "1" if show_full_path else "0")
                st.success("Preferences saved.")

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 8px;">
                Scanning Rules
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("scan_rules_form"):
            current_max_mb = int(repo.get_setting("max_file_size_mb", "50"))
            max_size = st.slider("Maximum file size for full search (MB)", 5, 150, current_max_mb, 5)

            rec = st.checkbox(
                "Scan subfolders automatically",
                value=repo.get_setting("default_recursive", "1") == "1"
            )
            skip_tmp = st.checkbox(
                "Ignore temporary and lock files (~$, .tmp)",
                value=repo.get_setting("skip_temp_files", "1") == "1"
            )

            if st.form_submit_button("Save Scanning Rules", type="primary", use_container_width=True):
                repo.set_setting("max_file_size_mb", str(max_size))
                repo.set_setting("default_recursive", "1" if rec else "0")
                repo.set_setting("skip_temp_files", "1" if skip_tmp else "0")
                st.success("Rules saved.")

    # ─────────────────────────────────────────────────────────────────────────
    # COLUMN 2: Backup & Library Maintenance
    # ─────────────────────────────────────────────────────────────────────────
    with c_col2:
        st.markdown(
            """
            <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 8px;">
                Backup & Restore
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px solid #E6E2D8;border-radius:6px;padding:14px;margin-bottom:12px;">
                <div style="font-size:0.86rem;font-weight:600;color:#15181E;margin-bottom:2px;">Export Catalog Backup</div>
                <div style="font-size:0.78rem;color:#697386;margin-bottom:10px;">Save your search catalog and settings to a portable .zip file.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        if "latest_backup_path" not in st.session_state:
            st.session_state.latest_backup_path = None

        if st.button("Generate Backup (.zip)", type="primary", use_container_width=True):
            bp = create_backup()
            st.session_state.latest_backup_path = str(bp)
            st.success(f"Backup created: {Path(bp).name}")

        if st.session_state.latest_backup_path and os.path.exists(st.session_state.latest_backup_path):
            with open(st.session_state.latest_backup_path, "rb") as bf:
                b_bytes = bf.read()
            st.download_button(
                label=f"Download {Path(st.session_state.latest_backup_path).name}",
                data=b_bytes,
                file_name=Path(st.session_state.latest_backup_path).name,
                mime="application/zip",
                use_container_width=True
            )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="background:#FFFFFF;border:1px solid #E6E2D8;border-radius:6px;padding:14px;margin-bottom:10px;">
                <div style="font-size:0.86rem;font-weight:600;color:#15181E;margin-bottom:2px;">Restore from Backup</div>
                <div style="font-size:0.78rem;color:#697386;margin-bottom:8px;">Restore search data from an existing .zip backup file.</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        uploaded_backup = st.file_uploader(
            "Upload backup .zip file",
            type=["zip"],
            key="file_uploader_backup",
            label_visibility="collapsed"
        )
        if uploaded_backup is not None:
            if st.button("Restore from Uploaded Backup", type="primary", use_container_width=True):
                tmp_dir = DATA_DIR / "backups"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                tmp_target = tmp_dir / uploaded_backup.name
                with open(tmp_target, "wb") as f_out:
                    f_out.write(uploaded_backup.getbuffer())
                ok, msg = restore_backup(tmp_target)
                if ok:
                    search_engine.text_index.load()
                    search_engine.image_index.load()
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        restore_path = st.text_input(
            "Or enter backup file path",
            placeholder=r"C:\path\to\backup.zip",
            key="input_restore_zip",
        )
        if st.button("Restore from Path", key="btn_restore_action", use_container_width=True):
            if not restore_path.strip():
                st.warning("Please specify the path to a .zip backup.")
            else:
                ok, msg = restore_backup(Path(restore_path.strip()))
                if ok:
                    search_engine.text_index.load()
                    search_engine.image_index.load()
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 8px;">
                Index Maintenance
            </div>
            """,
            unsafe_allow_html=True
        )

        if "confirm_reset_mode" not in st.session_state:
            st.session_state.confirm_reset_mode = False

        if not st.session_state.confirm_reset_mode:
            st.markdown(
                """
                <div style="font-size:0.80rem;color:#697386;margin-bottom:8px;">
                    Clears search index data so files can be re-indexed. Original files on disk are never touched.
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("Reset Search Index", type="secondary", use_container_width=True):
                st.session_state.confirm_reset_mode = True
                st.rerun()
        else:
            st.markdown(
                """
                <div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:6px;padding:12px;margin-bottom:10px;">
                    <div style="font-size:0.86rem;font-weight:600;color:#B42318;margin-bottom:2px;">Confirm Reset?</div>
                    <div style="font-size:0.80rem;color:#4A5160;">All search records will be cleared for re-indexing. Original documents remain intact.</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            r1, r2 = st.columns(2)
            with r1:
                if st.button("Confirm Reset", type="primary", key="btn_final_reset", use_container_width=True):
                    search_engine.text_index.reset()
                    search_engine.image_index.reset()
                    affected = repo.reset_all_search_indices()
                    st.session_state.confirm_reset_mode = False
                    st.success(f"Reset {affected} files.")
                    st.rerun()
            with r2:
                if st.button("Cancel", key="btn_cancel_reset", use_container_width=True):
                    st.session_state.confirm_reset_mode = False
                    st.rerun()

    # ─────────────────────────────────────────────────────────────────────────
    # Footer: Compact System Info
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    with st.expander("Storage Info", expanded=False):
        st.caption(f"Database: `{DB_PATH}` &nbsp;•&nbsp; Index Directory: `{INDEX_DIR}` &nbsp;•&nbsp; Status: 100% Local")
