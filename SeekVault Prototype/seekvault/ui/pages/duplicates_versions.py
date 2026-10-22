import streamlit as st
import pandas as pd
from seekvault.database.repository import Repository
from seekvault.organization.version_detector import VersionDetector
from seekvault.ui.components import (
    format_file_size,
    open_file_in_os,
    open_folder_in_os
)

def render_duplicates_versions_page(repo: Repository):
    st.header("👯 Duplicates & Version Detection")
    st.markdown("Intelligent file organization: exact SHA-256 cryptographic duplicate detection and semantic document version clustering.")

    tab_dup, tab_ver = st.tabs(["👯 Exact Duplicates (Hash)", "🌿 Document Version History (Semantic)"])

    with tab_dup:
        st.subheader("Exact Duplicate Clusters (SHA-256)")
        dup_groups = repo.get_duplicate_groups()

        if not dup_groups:
            st.info("No exact duplicate files detected across authorized directories.")
        else:
            total_reclaimable = sum(g["reclaimable_size"] for g in dup_groups)
            total_redundant = sum(g["file_count"] - 1 for g in dup_groups)

            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Duplicate Clusters", len(dup_groups))
            with m2:
                st.metric("Redundant File Copies", total_redundant)
            with m3:
                st.metric("Potential Reclaimable Space", format_file_size(total_reclaimable))

            st.markdown("---")

            for idx, g in enumerate(dup_groups, 1):
                cluster_label = f"Cluster #{idx} — SHA-256: {g['file_hash'][:16]}... ({g['file_count']} files • Wasted: {format_file_size(g['reclaimable_size'])})"
                with st.expander(cluster_label, expanded=True):
                    st.caption(f"Full Hash: `{g['file_hash']}` | Total Combined Size: {format_file_size(g['total_size'])}")
                    for p_idx, p in enumerate(g["file_paths"]):
                        c_path, c_btn1, c_btn2 = st.columns([3.5, 0.8, 1])
                        with c_path:
                            st.markdown(f"📄 `{p}`")
                        with c_btn1:
                            if st.button("👁️ Open", key=f"dup_open_file_{idx}_{p_idx}"):
                                ok, msg = open_file_in_os(p)
                                if not ok:
                                    st.warning(msg)
                        with c_btn2:
                            if st.button("📂 Folder", key=f"dup_open_folder_{idx}_{p_idx}"):
                                ok, msg = open_folder_in_os(p)
                                if not ok:
                                    st.warning(msg)

    with tab_ver:
        st.subheader("Document Version History")
        st.markdown("Identified sequential revisions based on base stem alignment and semantic embedding similarity ($\ge 82\%$).")

        if st.button("🔄 Refresh Version Detection", key="btn_refresh_versions"):
            with st.spinner("Analyzing document embedding similarity across indexed files..."):
                VersionDetector.detect_and_update_versions(repo)
            st.success("Version detection refreshed!")
            st.rerun()

        version_groups = repo.get_all_version_groups()

        if not version_groups:
            st.info("No version chains detected yet. Ingest multiple revisions of a document (e.g., Draft v1 and Draft v2) to see them grouped here.")
        else:
            for v_idx, vg in enumerate(version_groups, 1):
                # Sort revisions chronologically by modification timestamp
                members = sorted(vg["members"], key=lambda m: m.get("modified_at") or "")
                with st.expander(f"📁 {vg['group_name']} ({len(members)} revisions)", expanded=True):
                    for m_idx, m in enumerate(members, 1):
                        c_order, c_name, c_sim, c_date, c_act1, c_act2 = st.columns([1, 2.5, 1.5, 1.8, 0.8, 1])
                        with c_order:
                            st.markdown(f"**Rev {m_idx}**")
                        with c_name:
                            st.markdown(f"`{m['file_name']}`")
                        with c_sim:
                            st.caption(f"Match: {m['similarity_score'] * 100:.1f}%")
                        with c_date:
                            st.caption(f"🕒 {m['modified_at']}")
                        with c_act1:
                            if st.button("👁️", key=f"ver_open_{v_idx}_{m_idx}", help="Open File"):
                                ok, msg = open_file_in_os(m["file_path"])
                                if not ok:
                                    st.warning(msg)
                        with c_act2:
                            if st.button("📂", key=f"ver_folder_{v_idx}_{m_idx}", help="Open in Folder"):
                                ok, msg = open_folder_in_os(m["file_path"])
                                if not ok:
                                    st.warning(msg)

