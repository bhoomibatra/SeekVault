import streamlit as st
import pandas as pd
from seekvault.database.repository import Repository
from seekvault.ui.components import render_tier_badge

def render_dashboard(repo: Repository, watcher_status: dict):
    st.header("📊 System Dashboard & Telemetry")
    st.markdown("Real-time local status of SeekVault index, privacy tiers, and monitoring daemon.")

    stats = repo.get_dashboard_stats()

    # First-Run Onboarding Guide for Clean Empty States
    if stats["active_folders"] == 0:
        st.info("👋 **Welcome to SeekVault!** To start searching your documents, add your first authorized folder.")
        with st.container():
            st.markdown("""
            ### 🚀 Getting Started in 3 Simple Steps:
            1. **Authorize a Folder:** Go to **📁 Authorized Folders** in the sidebar and enter any folder path on your computer.
            2. **Local Indexing:** SeekVault scans your files, classifies sensitive data (`FULL`, `REDACTED`, or `METADATA_ONLY`), and creates local search vectors.
            3. **Semantic Search:** Navigate to **🔍 Semantic Search** and query your files in natural language—100% offline and private!
            """)
        st.markdown("---")
    elif stats["total_files"] == 0:
        st.warning("⚠️ **Authorized folders configured, but no files have been indexed yet.** Visit **📁 Authorized Folders** and click **Rescan** to index your documents.")
        st.markdown("---")

    # KPI Top Metric Row
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("📁 Authorized Folders", stats["active_folders"])
    with c2:
        st.metric("📄 Total Files", stats["total_files"])
    with c3:
        st.metric("📑 Documents", stats["document_count"])
    with c4:
        st.metric("🖼️ Images", stats["image_count"])
    with c5:
        # Watchdog status
        is_active = watcher_status.get("is_running", False)
        st.metric("⚡ Watchdog Monitor", "ACTIVE" if is_active else "IDLE")

    st.markdown("---")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("🛡️ Privacy Tier Classifications")
        tier_counts = stats["tier_counts"]
        if tier_counts:
            df_tiers = pd.DataFrame([
                {"Privacy Tier": k, "Count": v} for k, v in tier_counts.items()
            ])
            st.bar_chart(df_tiers.set_index("Privacy Tier"), color="#3B82F6")
            
            c_f, c_r, c_m = st.columns(3)
            with c_f:
                st.markdown(f"**FULL**: `{tier_counts.get('FULL', 0)}` files")
            with c_r:
                st.markdown(f"**REDACTED**: `{tier_counts.get('REDACTED', 0)}` files")
            with c_m:
                st.markdown(f"**METADATA_ONLY**: `{tier_counts.get('METADATA_ONLY', 0)}` files")
        else:
            st.info("No files indexed yet. Authorize a folder to start.")

    with col_right:
        st.subheader("📑 Duplicate & Version Clusters")
        st.metric("👯 Duplicate Groups (SHA-256)", stats["duplicate_clusters"])
        st.metric("🌿 Version History Trees", stats["version_groups_count"])
        st.metric("🔍 Detected PII Entities", stats["total_pii_entities"])

        st.info("💡 **Local-First Privacy Principle**: Original files are never modified, renamed, moved, or deleted. All embeddings remain strictly on your local machine.")

    # Watched Folders Table
    st.subheader("Active Watched Paths")
    watched_paths = watcher_status.get("watched_paths", [])
    if watched_paths:
        for p in watched_paths:
            st.code(f"🟢 MONITORING: {p}", language="bash")
    else:
        st.warning("No directories currently active in Watchdog. Add folders in the 'Authorized Folders' page.")
