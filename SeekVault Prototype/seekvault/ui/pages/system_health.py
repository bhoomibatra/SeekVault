import os
import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional

from seekvault.database.repository import Repository
from seekvault.search.engine import SearchEngine
from seekvault.ingestion.pipeline import IngestionPipeline
from seekvault.monitoring.watcher import WatcherManager
from seekvault.ui.components import (
    render_tier_badge,
    format_file_size,
    open_file_in_os,
    open_folder_in_os,
    inject_design_system,
)
from seekvault.ui.navigator import get_friendly_folder_name


def check_vector_integrity(repo: Repository, search_engine: SearchEngine) -> Dict[str, Any]:
    """
    Diagnose consistency between database file records and search vector indices.
    Preserves exact contract for automated test suite.
    """
    files = repo.get_all_files(status="INDEXED")
    missing_vectors: List[Dict[str, Any]] = []

    for f in files:
        fid = f["id"]
        tier = f.get("privacy_tier")
        sz = f.get("file_size", 0)
        is_image = f.get("file_type") == "IMAGE"

        # Files that require vectors (FULL or REDACTED with > 0 bytes)
        if tier != "METADATA_ONLY" and sz > 0:
            if is_image:
                if not search_engine.image_index.has_file(fid):
                    missing_vectors.append(f)
            else:
                if not search_engine.text_index.has_file(fid):
                    missing_vectors.append(f)

    text_vectors = search_engine.text_index.index.ntotal
    image_vectors = search_engine.image_index.index.ntotal
    failed_files = repo.get_all_files(status="FAILED")
    pending_files = repo.get_all_files(status="PENDING")

    is_consistent = len(missing_vectors) == 0

    return {
        "is_consistent": is_consistent,
        "missing_vector_count": len(missing_vectors),
        "missing_files": missing_vectors,
        "indexed_count": len(files),
        "failed_count": len(failed_files),
        "failed_files": failed_files,
        "pending_count": len(pending_files),
        "pending_files": pending_files,
        "faiss_text_vectors": text_vectors,
        "faiss_image_vectors": image_vectors,
    }


def _human_error_description(raw_error: str) -> str:
    """Translate technical exception tracebacks into plain-language guidance."""
    if not raw_error:
        return "Unknown or unreadable file format"
    err = raw_error.lower()
    if "permission" in err or "access is denied" in err:
        return "Access denied — file is currently locked or requires higher permissions"
    if "password" in err or "encrypted" in err:
        return "File is password-protected and could not be decrypted"
    if "empty" in err or "0 bytes" in err:
        return "File is empty (0 bytes)"
    if "not found" in err or "no such file" in err:
        return "File was moved, renamed, or deleted from disk"
    if "corrupt" in err or "invalid" in err or "bad" in err:
        return "File contents appear corrupted or incomplete"
    if len(raw_error) > 120:
        return raw_error[:120] + "..."
    return raw_error


def render_system_health_page(
    repo: Repository,
    search_engine: SearchEngine,
    pipeline: IngestionPipeline,
    watcher: WatcherManager
):
    """
    User-First Indexing Status & Health screen.
    Answers the user's primary question: "Are my files ready to search?"
    Uses strictly 4 plain statuses:
    1. Ready to search
    2. Being processed
    3. Couldn't be read
    4. Needs attention
    """
    inject_design_system()

    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h1 style="font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-size: 1.65rem; font-weight: 700; color: #15181E; margin: 0 0 4px 0;">
                Indexing Status
            </h1>
            <p style="font-size: 0.88rem; color: #697386; margin: 0;">
                See if your files are ready to search, review any unreadable files, and monitor background folder synchronization.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    watcher_status = watcher.get_status()
    diag = check_vector_integrity(repo, search_engine)
    authorized_folders = repo.get_authorized_folders()

    # Calculate 4 plain user-facing states
    ready_count = max(0, diag["indexed_count"] - diag["missing_vector_count"])
    processing_count = diag["pending_count"]
    failed_count = diag["failed_count"]
    attention_count = diag["missing_vector_count"]

    # ─────────────────────────────────────────────────────────────────────────
    # 1. EXACT 4 PLAIN STATUS CARDS
    # ─────────────────────────────────────────────────────────────────────────
    s1, s2, s3, s4 = st.columns(4)

    with s1:
        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid #A7F3D0;border-left:4px solid #059669;border-radius:8px;padding:14px 16px;">
                <div style="font-size:1.45rem;font-weight:700;color:#065F46;line-height:1.1;">{ready_count}</div>
                <div style="font-size:0.85rem;font-weight:600;color:#15181E;margin-top:4px;">Ready to search</div>
                <div style="font-size:0.75rem;color:#697386;margin-top:2px;">Files up-to-date in library</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with s2:
        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid #BFDBFE;border-left:4px solid #1D4ED8;border-radius:8px;padding:14px 16px;">
                <div style="font-size:1.45rem;font-weight:700;color:#1D4ED8;line-height:1.1;">{processing_count}</div>
                <div style="font-size:0.85rem;font-weight:600;color:#15181E;margin-top:4px;">Being processed</div>
                <div style="font-size:0.75rem;color:#697386;margin-top:2px;">Queued for indexing</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with s3:
        border_col = "#FECACA" if failed_count > 0 else "#E6E2D8"
        bar_col = "#DC2626" if failed_count > 0 else "#9CA3AF"
        text_col = "#991B1B" if failed_count > 0 else "#697386"
        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid {border_col};border-left:4px solid {bar_col};border-radius:8px;padding:14px 16px;">
                <div style="font-size:1.45rem;font-weight:700;color:{text_col};line-height:1.1;">{failed_count}</div>
                <div style="font-size:0.85rem;font-weight:600;color:#15181E;margin-top:4px;">Couldn't be read</div>
                <div style="font-size:0.75rem;color:#697386;margin-top:2px;">Corrupt, locked, or protected</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with s4:
        border_col = "#FDE68A" if attention_count > 0 else "#E6E2D8"
        bar_col = "#D97706" if attention_count > 0 else "#9CA3AF"
        text_col = "#92400E" if attention_count > 0 else "#697386"
        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid {border_col};border-left:4px solid {bar_col};border-radius:8px;padding:14px 16px;">
                <div style="font-size:1.45rem;font-weight:700;color:{text_col};line-height:1.1;">{attention_count}</div>
                <div style="font-size:0.85rem;font-weight:600;color:#15181E;margin-top:4px;">Needs attention</div>
                <div style="font-size:0.75rem;color:#697386;margin-top:2px;">Requires index resync</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. ACTIONS & RE-INDEXING (REAL WORK, ACCURATE PROGRESS)
    # ─────────────────────────────────────────────────────────────────────────
    col_reindex, col_sync = st.columns([1.5, 1.2])

    with col_reindex:
        st.markdown(
            """
            <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
                Library Re-Scan
            </div>
            <div style="font-size: 0.82rem; color: #697386; margin-bottom: 10px;">
                Scan monitored folders to detect newly added or edited files.
            </div>
            """,
            unsafe_allow_html=True
        )

        if authorized_folders:
            if st.button("Scan All Monitored Folders Now", type="primary", use_container_width=True):
                prog_bar = st.progress(0.0)
                status_txt = st.empty()

                def _progress_cb(current_idx: int, total_count: int, file_name: str):
                    if total_count > 0:
                        prog_bar.progress(min(1.0, (current_idx + 1) / total_count))
                        status_txt.caption(f"Indexing file {current_idx + 1} of {total_count}: `{file_name}`")

                with st.spinner("Processing files..."):
                    processed = 0
                    for f in authorized_folders:
                        processed += pipeline.scan_folder(f["folder_path"], is_recursive=True, progress_callback=_progress_cb)

                prog_bar.empty()
                status_txt.empty()
                st.success(f"Scan complete. {processed} files up-to-date and ready to search.")
                st.rerun()
        else:
            st.info("No folders currently monitored. Go to **My Files** to add your first folder.")

    with col_sync:
        if attention_count > 0:
            st.markdown(
                """
                <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
                    Search Resynchronization
                </div>
                <div style="font-size: 0.82rem; color: #92400E; margin-bottom: 10px;">
                    Some search records need to be regenerated from local files.
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("Resynchronize Search Records", type="secondary", use_container_width=True):
                healed = 0
                with st.spinner("Regenerating search entries..."):
                    for mf in diag["missing_files"]:
                        if os.path.exists(mf["file_path"]):
                            pipeline.process_file(mf["file_path"], force_reembed=True)
                            healed += 1
                st.success(f"Resynchronized {healed} file(s).")
                st.rerun()
        else:
            st.markdown(
                """
                <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
                    Search Index Health
                </div>
                <div style="font-size: 0.82rem; color: #065F46; line-height: 1.5; background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 6px; padding: 10px 14px;">
                    All indexed documents are fully synchronized with your search index.
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("<div style='height: 22px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. FILES THAT COULDN'T BE READ (Plain language errors + actionable recovery)
    # ─────────────────────────────────────────────────────────────────────────
    if diag["failed_count"] > 0:
        st.markdown(
            f"""
            <div style="font-size: 1.05rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
                Files That Couldn't Be Read ({diag['failed_count']})
            </div>
            <p style="font-size: 0.84rem; color: #697386; margin-bottom: 12px;">
                These files encountered reading errors. Review the reasons below and retry or exclude them:
            </p>
            """,
            unsafe_allow_html=True
        )

        for ff in diag["failed_files"]:
            f_id = ff["id"]
            f_name = ff["file_name"]
            f_path = ff["file_path"]
            f_err = _human_error_description(ff.get("error_detail") or "")
            parent_name = get_friendly_folder_name(str(Path(f_path).parent))

            with st.container():
                c_desc, c_reveal, c_retry, c_dismiss = st.columns([3.0, 1.0, 1.0, 0.9])
                with c_desc:
                    st.markdown(
                        f"""
                        <div style="font-size: 0.90rem; font-weight: 600; color: #15181E;">{f_name}</div>
                        <div style="font-size: 0.80rem; color: #B42318; margin-top: 1px;">{f_err}</div>
                        <div style="font-size: 0.74rem; color: #697386;">In <strong>{parent_name}</strong> &nbsp;•&nbsp; {f_path}</div>
                        """,
                        unsafe_allow_html=True
                    )
                with c_reveal:
                    if st.button("Show in Folder", key=f"rev_failed_{f_id}", use_container_width=True):
                        ok, msg = open_folder_in_os(f_path)
                        if not ok:
                            st.warning(msg)
                with c_retry:
                    if st.button("Retry Indexing", key=f"retry_single_{f_id}", use_container_width=True):
                        with st.spinner(f"Retrying '{f_name}'..."):
                            if os.path.exists(f_path):
                                pipeline.process_file(f_path, force_reembed=True)
                        st.rerun()
                with c_dismiss:
                    if st.button("Ignore File", key=f"dismiss_failed_{f_id}", use_container_width=True, help="Remove from library catalog"):
                        pipeline.remove_file(f_path)
                        st.rerun()

                st.markdown("<hr style='border: none; border-top: 1px solid #E6E2D8; margin: 8px 0 10px 0;'/>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. BACKGROUND FOLDER MONITORING
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 1.05rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
            Automatic Folder Monitoring
        </div>
        """,
        unsafe_allow_html=True
    )

    is_running = watcher_status.get("is_running", False)
    watched_paths = watcher_status.get("watched_paths", [])

    if is_running and watched_paths:
        friendly_names = [f"<strong>{get_friendly_folder_name(p)}</strong>" for p in watched_paths]
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 14px 18px; color: #374151; font-size: 0.86rem; line-height: 1.5;">
                <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #059669; margin-right: 6px;"></span>
                <strong>Active</strong> — SeekVault automatically updates when files are created, modified, or deleted in: {', '.join(friendly_names)}.
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px dashed #D1CBC0; border-radius: 8px; padding: 14px 18px; color: #697386; font-size: 0.86rem;">
                No background folder monitoring currently active. Add folders in <strong>My Files</strong> to enable automatic updates.
            </div>
            """,
            unsafe_allow_html=True
        )


# Backwards compatibility alias
render_indexing_status_page = render_system_health_page
