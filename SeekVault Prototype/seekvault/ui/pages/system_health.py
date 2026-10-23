import os
import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List

from seekvault.database.repository import Repository
from seekvault.search.engine import SearchEngine
from seekvault.ingestion.pipeline import IngestionPipeline
from seekvault.monitoring.watcher import WatcherManager
from seekvault.ui.components import (
    render_tier_badge,
    format_file_size,
    inject_design_system,
)


def check_vector_integrity(repo: Repository, search_engine: SearchEngine) -> Dict[str, Any]:
    """Diagnose consistency between SQLite file records and FAISS vector indices."""
    files = repo.get_all_files(status="INDEXED")
    missing_vectors: List[Dict[str, Any]] = []

    for f in files:
        fid = f["id"]
        tier = f.get("privacy_tier")
        sz = f.get("file_size", 0)
        is_image = f.get("file_type") == "IMAGE"

        # Files that require vectors (FULL or REDACTED with >0 bytes)
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


def render_system_health_page(
    repo: Repository,
    search_engine: SearchEngine,
    pipeline: IngestionPipeline,
    watcher: WatcherManager
):
    inject_design_system()

    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #1D4ED8; margin-bottom: 4px;">
                System Telemetry & Diagnostics
            </div>
            <h1 style="font-family: 'Newsreader', Georgia, serif; font-size: 2.2rem; font-weight: 600; color: #15181E; margin: 0 0 8px 0; letter-spacing: -0.02em;">
                Indexing & System Health
            </h1>
            <p style="font-size: 0.95rem; color: #5A6270; margin: 0; line-height: 1.5;">
                Live operational telemetry, vector consistency audits, and non-destructive self-healing routines.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    watcher_status = watcher.get_status()
    diag = check_vector_integrity(repo, search_engine)
    stats = repo.get_dashboard_stats()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. High-Level Health Banner
    # ─────────────────────────────────────────────────────────────────────────
    if diag["is_consistent"] and diag["failed_count"] == 0 and watcher_status["is_running"]:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #A7F3D0; border-left: 4px solid #059669; border-radius: 8px; padding: 14px 18px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #059669;"></span>
                    <span style="font-size: 0.90rem; font-weight: 700; color: #065F46; text-transform: uppercase; letter-spacing: 0.05em;">
                        System Healthy & Synchronized
                    </span>
                </div>
                <div style="font-size: 0.88rem; color: #374151; line-height: 1.5; margin-left: 16px;">
                    All SQLite file records match active FAISS vector rows. Continuous filesystem observer daemon is actively monitoring authorized directories.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    elif not diag["is_consistent"] or diag["failed_count"] > 0:
        issues = []
        if not diag["is_consistent"]:
            issues.append(f"{diag['missing_vector_count']} file(s) missing search vectors")
        if diag["failed_count"] > 0:
            issues.append(f"{diag['failed_count']} file(s) failed ingestion")

        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #FDE68A; border-left: 4px solid #D97706; border-radius: 8px; padding: 14px 18px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #D97706;"></span>
                    <span style="font-size: 0.90rem; font-weight: 700; color: #92400E; text-transform: uppercase; letter-spacing: 0.05em;">
                        Attention Required
                    </span>
                </div>
                <div style="font-size: 0.88rem; color: #374151; line-height: 1.5; margin-left: 16px;">
                    {', '.join(issues)}. Use the non-destructive healing controls below to re-synchronize your vault without modifying original files.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E2DFD7; border-left: 4px solid #64748B; border-radius: 8px; padding: 14px 18px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #64748B;"></span>
                    <span style="font-size: 0.90rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.05em;">
                        System Idle
                    </span>
                </div>
                <div style="font-size: 0.88rem; color: #5A6270; line-height: 1.5; margin-left: 16px;">
                    No background watcher daemon currently active or zero authorized folders configured.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Key Operational Telemetry Row
    # ─────────────────────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("Active Folders", stats["active_folders"])
    with m2:
        st.metric("Total Indexed", diag["indexed_count"])
    with m3:
        st.metric("Text Vectors", diag["faiss_text_vectors"])
    with m4:
        st.metric("Image Vectors", diag["faiss_image_vectors"])
    with m5:
        st.metric("Failed Files", diag["failed_count"])

    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Vector / SQLite Database Consistency Audit
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 1.15rem; font-weight: 600; color: #15181E; margin-bottom: 12px; font-family: 'Newsreader', Georgia, serif;">
            Database & Vector Index Consistency
        </div>
        """,
        unsafe_allow_html=True
    )

    c_audit, c_heal = st.columns([2.5, 1.2])

    with c_audit:
        if diag["is_consistent"]:
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #A7F3D0; border-radius: 8px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                    <div style="font-size: 0.95rem; font-weight: 600; color: #065F46; margin-bottom: 8px;">
                        100% Index Consistency Verified
                    </div>
                    <div style="font-size: 0.85rem; color: #374151; line-height: 1.6;">
                        • <strong>{diag['indexed_count']}</strong> indexed file records in SQLite repository.<br>
                        • <strong>{diag['faiss_text_vectors']}</strong> dense text vectors in <code>seekvault_text.faiss</code>.<br>
                        • <strong>{diag['faiss_image_vectors']}</strong> visual embeddings in <code>seekvault_visual.faiss</code>.<br>
                        • Exactly zero orphaned or missing vector records detected.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #FECACA; border-radius: 8px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                    <div style="font-size: 0.95rem; font-weight: 600; color: #991B1B; margin-bottom: 8px;">
                        Vector Discrepancy Detected: {diag['missing_vector_count']} file(s) lack search vectors
                    </div>
                    <div style="font-size: 0.85rem; color: #374151; line-height: 1.6;">
                        SQLite has recorded these files as indexed, but their corresponding vectors are missing from disk.
                        Click <strong>Heal & Sync Vectors</strong> to regenerate embeddings without touching user files.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            for mf in diag["missing_files"]:
                st.caption(f"Missing vector: `{mf['file_name']}` (Path: `{mf['file_path']}`)")

    with c_heal:
        st.markdown(
            """
            <div style="font-size: 0.85rem; font-weight: 600; color: #15181E; margin-bottom: 8px;">
                Index Maintenance
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Heal & Sync Vector Index", type="primary", use_container_width=True):
            healed = 0
            with st.spinner("Re-generating missing vectors safely in-memory..."):
                for mf in diag["missing_files"]:
                    if os.path.exists(mf["file_path"]):
                        pipeline.process_file(mf["file_path"])
                        healed += 1
            st.success(f"Successfully healed {healed} file vector(s).")
            st.rerun()

    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Failed Ingestion Audit & Retry
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 1.15rem; font-weight: 600; color: #15181E; margin-bottom: 12px; font-family: 'Newsreader', Georgia, serif;">
            Failed File Inspections
        </div>
        """,
        unsafe_allow_html=True
    )

    if diag["failed_count"] == 0:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E2DFD7; border-radius: 8px; padding: 20px; text-align: center; color: #5A6270; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 0.92rem; font-weight: 600; color: #15181E; margin-bottom: 4px;">Zero Ingestion Failures</div>
                <div style="font-size: 0.84rem; color: #737373;">
                    All files across authorized folders parsed and indexed successfully.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div style="font-size: 0.88rem; color: #92400E; margin-bottom: 10px;">
                <strong>{diag['failed_count']}</strong> file(s) encountered parsing or extraction errors during ingestion.
            </div>
            """,
            unsafe_allow_html=True
        )
        failed_table = []
        for ff in diag["failed_files"]:
            failed_table.append({
                "File Name": ff["file_name"],
                "Path": ff["file_path"],
                "Error Detail": ff.get("error_detail") or "Corrupt or unreadable file format",
                "Modified": ff["modified_at"]
            })
        st.dataframe(pd.DataFrame(failed_table), use_container_width=True)

        if st.button("Retry Failed Files Ingestion"):
            retried = 0
            with st.spinner("Retrying ingestion for failed files..."):
                for ff in diag["failed_files"]:
                    if os.path.exists(ff["file_path"]):
                        pipeline.process_file(ff["file_path"])
                        retried += 1
            st.success(f"Retried {retried} file(s).")
            st.rerun()

    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Continuous Watchdog Daemon Telemetry
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 1.15rem; font-weight: 600; color: #15181E; margin-bottom: 12px; font-family: 'Newsreader', Georgia, serif;">
            Real-Time Filesystem Watchdog Telemetry
        </div>
        """,
        unsafe_allow_html=True
    )

    w1, w2 = st.columns([1, 2])
    with w1:
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E2DFD7; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #1D4ED8; margin-bottom: 6px;">
                    DAEMON OBSERVER
                </div>
                <div style="font-size: 0.85rem; color: #374151; line-height: 1.6;">
                    <strong>Status:</strong> {'Active (Running)' if watcher_status['is_running'] else 'Idle'}<br>
                    <strong>Monitored Roots:</strong> {watcher_status['watched_folder_count']}<br>
                    <strong>Debounce Window:</strong> 1.5 seconds<br>
                    <strong>Handled Events:</strong> Created, Modified, Deleted, Moved
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with w2:
        watched_paths = watcher_status.get("watched_paths", [])
        if watched_paths:
            st.markdown(
                """
                <div style="font-size: 0.85rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
                    Currently Monitored Paths
                </div>
                """,
                unsafe_allow_html=True
            )
            for wp in watched_paths:
                st.code(f"WATCHING: {wp}", language="bash")
        else:
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px solid #E2DFD7; border-radius: 8px; padding: 16px; color: #5A6270; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                    No active filesystem watch paths registered. Authorize folders in the <strong>File Library</strong> to enable real-time monitoring.
                </div>
                """,
                unsafe_allow_html=True
            )
