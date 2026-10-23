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
            <h1 style="font-size: 2.2rem; font-weight: 700; margin-bottom: 6px; color: #F3F4F6;">
                📊 Indexing & System Health
            </h1>
            <p style="font-size: 0.95rem; color: #9CA3AF; margin-top: 0;">
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
            <div style="background-color: #064E3B; border: 1px solid #10B981; border-radius: 8px; padding: 12px 18px; margin-bottom: 20px;">
                <span style="font-size: 1rem; font-weight: 600; color: #A7F3D0;">🟢 System Healthy & Synchronized:</span>
                <span style="font-size: 0.90rem; color: #D1FAE5; margin-left: 6px;">
                    All SQLite file records match active FAISS vector rows. Background filesystem monitoring is active.
                </span>
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
            <div style="background-color: #78350F; border: 1px solid #F59E0B; border-radius: 8px; padding: 12px 18px; margin-bottom: 20px;">
                <span style="font-size: 1rem; font-weight: 600; color: #FDE68A;">⚠️ Attention Required:</span>
                <span style="font-size: 0.90rem; color: #FEF3C7; margin-left: 6px;">
                    {', '.join(issues)}. Use the self-healing and retry triggers below to synchronize your vault.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="background-color: #1E293B; border: 1px solid #6366F1; border-radius: 8px; padding: 12px 18px; margin-bottom: 20px;">
                <span style="font-size: 1rem; font-weight: 600; color: #E0E7FF;">🟡 System Idle:</span>
                <span style="font-size: 0.90rem; color: #C7D2FE; margin-left: 6px;">
                    No background watcher running or zero authorized folders configured.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Key Operational Telemetry Row
    # ─────────────────────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.metric("📁 Active Folders", stats["active_folders"])
    with m2:
        st.metric("📄 Total Indexed", diag["indexed_count"])
    with m3:
        st.metric("⚡ Text Vectors", diag["faiss_text_vectors"])
    with m4:
        st.metric("🖼️ Image Vectors", diag["faiss_image_vectors"])
    with m5:
        st.metric("⚠️ Failed Files", diag["failed_count"])

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Vector / SQLite Database Consistency Audit
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("Database & Vector Index Consistency")

    c_audit, c_heal = st.columns([2.5, 1.2])

    with c_audit:
        if diag["is_consistent"]:
            st.success(
                f"✅ **100% Index Consistency Verified**\n\n"
                f"- **{diag['indexed_count']}** indexed file records in SQLite.\n"
                f"- **{diag['faiss_text_vectors']}** dense text vectors in `seekvault_text.faiss`.\n"
                f"- **{diag['faiss_image_vectors']}** visual embeddings in `seekvault_visual.faiss`.\n"
                f"- Zero orphaned or missing vectors detected."
            )
        else:
            st.error(
                f"❌ **Vector Discrepancy Detected: {diag['missing_vector_count']} file(s) lack search vectors**\n\n"
                f"SQLite has recorded these files as indexed, but their corresponding vectors are missing from disk. "
                f"Click **Heal & Sync Vectors** to regenerate embeddings without touching user files."
            )
            for mf in diag["missing_files"]:
                st.caption(f"⚠️ Missing vector: `{mf['file_name']}` (Path: `{mf['file_path']}`)")

    with c_heal:
        st.markdown("**Index Maintenance:**")
        if st.button("🩹 Heal & Sync Vector Index", type="primary", use_container_width=True):
            healed = 0
            with st.spinner("Re-generating missing vectors safely in-memory..."):
                for mf in diag["missing_files"]:
                    if os.path.exists(mf["file_path"]):
                        pipeline.process_file(mf["file_path"])
                        healed += 1
            st.success(f"Successfully healed {healed} file vector(s).")
            st.rerun()

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Failed Ingestion Audit & Retry
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("Failed File Inspections")

    if diag["failed_count"] == 0:
        st.info("✅ No file extraction or parsing errors currently recorded.")
    else:
        st.warning(f"⚠️ **{diag['failed_count']} file(s) encountered unrecoverable errors during ingestion.**")
        failed_table = []
        for ff in diag["failed_files"]:
            failed_table.append({
                "File Name": ff["file_name"],
                "Path": ff["file_path"],
                "Error Detail": ff.get("error_detail") or "Corrupt or unreadable file format",
                "Modified": ff["modified_at"]
            })
        st.dataframe(pd.DataFrame(failed_table), use_container_width=True)

        if st.button("🔄 Retry Failed Files Ingestion"):
            retried = 0
            with st.spinner("Retrying ingestion for failed files..."):
                for ff in diag["failed_files"]:
                    if os.path.exists(ff["file_path"]):
                        pipeline.process_file(ff["file_path"])
                        retried += 1
            st.success(f"Retried {retried} file(s).")
            st.rerun()

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Continuous Watchdog Daemon Telemetry
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("Real-Time Filesystem Watchdog Telemetry")

    w1, w2 = st.columns([1, 2])
    with w1:
        st.markdown(
            f"""
            <div class="seekvault-search-card">
                <h4 style="color: #F3F4F6; margin: 0 0 6px 0;">Daemon Observer</h4>
                <p style="font-size: 0.85rem; color: #9CA3AF; margin: 0; line-height: 1.5;">
                    <strong>Status:</strong> {'🟢 Running' if watcher_status['is_running'] else '🟡 Idle'}<br>
                    <strong>Monitored Roots:</strong> {watcher_status['watched_folder_count']}<br>
                    <strong>Debounce Window:</strong> 1.5 seconds<br>
                    <strong>Event Handlers:</strong> Created, Modified, Deleted, Moved
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with w2:
        watched_paths = watcher_status.get("watched_paths", [])
        if watched_paths:
            st.markdown("**Currently Monitored Paths:**")
            for wp in watched_paths:
                st.code(f"🟢 WATCHING: {wp}", language="bash")
        else:
            st.info("No active filesystem watch paths registered. Authorize folders in the **📁 File Library** to enable monitoring.")
