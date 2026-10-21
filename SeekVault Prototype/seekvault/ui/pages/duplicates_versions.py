import streamlit as st
import pandas as pd
from seekvault.database.repository import Repository
from seekvault.organization.version_detector import VersionDetector
from seekvault.ui.components import format_file_size

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
            st.warning(f"⚠️ Found {len(dup_groups)} duplicate clusters. Potential Reclaimable Storage: **{format_file_size(total_reclaimable)}**")

            for idx, g in enumerate(dup_groups, 1):
                with st.expander(f"Cluster #{idx} — Hash: {g['file_hash'][:16]}... ({g['file_count']} files, {format_file_size(g['total_size'])})", expanded=True):
                    st.markdown(f"**Reclaimable space if redundant copies removed:** `{format_file_size(g['reclaimable_size'])}`")
                    for p in g["file_paths"]:
                        st.markdown(f"- 📁 `{p}`")

    with tab_ver:
        st.subheader("Document Version History")
        st.markdown("Identified sequential revisions based on base stem alignment and semantic embedding similarity ($\ge 82\%$).")

        if st.button("🔄 Refresh Version Detection"):
            with st.spinner("Analyzing document embedding similarity across indexed files..."):
                VersionDetector.detect_and_update_versions(repo)
            st.success("Version detection refreshed!")
            st.rerun()

        version_groups = repo.get_all_version_groups()

        if not version_groups:
            st.info("No version chains detected yet. Ingest multiple revisions of a document (e.g., Draft v1 and Draft v2) to see them grouped here.")
        else:
            for vg in version_groups:
                with st.expander(f"📁 {vg['group_name']} ({len(vg['members'])} versions)", expanded=True):
                    for m in vg["members"]:
                        c_order, c_name, c_sim, c_date = st.columns([1, 3, 2, 2])
                        with c_order:
                            st.markdown(f"**Version {m['version_order']}**")
                        with c_name:
                            st.markdown(f"`{m['file_name']}`")
                        with c_sim:
                            st.caption(f"Similarity: {m['similarity_score'] * 100:.1f}%")
                        with c_date:
                            st.caption(f"Modified: {m['modified_at']}")
