import streamlit as st
import pandas as pd
from seekvault.database.repository import Repository
from seekvault.organization.version_detector import VersionDetector
from seekvault.ui.components import (
    format_file_size,
    open_file_in_os,
    open_folder_in_os,
    inject_design_system,
)


def render_duplicates_versions_page(repo: Repository):
    inject_design_system()

    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="font-size: 2.2rem; font-weight: 700; margin-bottom: 6px; color: #F3F4F6;">
                👯 Duplicates & Version History
            </h1>
            <p style="font-size: 0.95rem; color: #9CA3AF; margin-top: 0;">
                Content-hash exact duplicate clustering and heuristic semantic version lineage suggestions.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_dup, tab_ver = st.tabs(["👯 Exact Duplicates (SHA-256)", "🌿 Probable Versions (Suggestions)"])

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 1: EXACT DUPLICATES
    # ═════════════════════════════════════════════════════════════════════════
    with tab_dup:
        st.markdown(
            """
            <div style="background-color: #111827; border: 1px solid #24324D; border-radius: 8px; padding: 12px 18px; margin-bottom: 20px;">
                <span style="font-size: 0.95rem; font-weight: 600; color: #F3F4F6;">🛡️ Non-Destructive Policy:</span>
                <span style="font-size: 0.90rem; color: #9CA3AF; margin-left: 6px;">
                    SeekVault identifies redundant copies for your awareness. 
                    <strong>Original files are strictly never automatically deleted, moved, or altered.</strong>
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

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
                cluster_label = f"Cluster #{idx} — SHA-256: {g['file_hash'][:16]}... ({g['file_count']} copies • Wasted: {format_file_size(g['reclaimable_size'])})"
                with st.expander(cluster_label, expanded=True):
                    st.caption(f"Full Hash: `{g['file_hash']}` | Combined Size: {format_file_size(g['total_size'])}")

                    for p_idx, p in enumerate(g["file_paths"]):
                        c_path, c_btn1, c_btn2 = st.columns([3.5, 0.8, 1])
                        with c_path:
                            # Monospace path
                            st.markdown(f"📄 `{p}`")
                        with c_btn1:
                            if st.button("👁️ Open", key=f"dup_open_{idx}_{p_idx}"):
                                ok, msg = open_file_in_os(p)
                                if not ok:
                                    st.warning(msg)
                        with c_btn2:
                            if st.button("📂 Reveal", key=f"dup_reveal_{idx}_{p_idx}"):
                                ok, msg = open_folder_in_os(p)
                                if not ok:
                                    st.warning(msg)

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 2: PROBABLE VERSIONS (HEURISTIC SUGGESTIONS)
    # ═════════════════════════════════════════════════════════════════════════
    with tab_ver:
        st.markdown(
            """
            <div style="background-color: #111827; border: 1px solid #6366F1; border-radius: 8px; padding: 12px 18px; margin-bottom: 20px;">
                <span style="font-size: 0.95rem; font-weight: 600; color: #E0E7FF;">💡 Heuristic Version Suggestions:</span>
                <span style="font-size: 0.90rem; color: #C7D2FE; margin-left: 6px;">
                    Versions are detected using filename stem alignment and semantic embedding cosine similarity (&ge; 82%). 
                    These are <strong>heuristics for user review</strong>, not an authoritative edit history. Dismiss any incorrect matches below.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_ref, col_dismissed = st.columns([1.5, 1])
        with col_ref:
            if st.button("🔄 Refresh Version Detection", key="btn_refresh_versions", type="primary"):
                with st.spinner("Analyzing document embedding similarity across indexed files..."):
                    VersionDetector.detect_and_update_versions(repo)
                st.success("Version detection refreshed!")
                st.rerun()

        with col_dismissed:
            show_dismissed = st.checkbox("Show dismissed suggestions", value=False)

        version_groups = repo.get_all_version_groups(include_dismissed=show_dismissed)

        if not version_groups:
            st.info(
                "No version chains detected yet. Ingest multiple revisions of a document (e.g., `Draft_v1.docx` and `Draft_v2.docx`) to see them grouped here."
            )
        else:
            for v_idx, vg in enumerate(version_groups, 1):
                # Sort revisions chronologically by modification timestamp
                members = sorted(vg["members"], key=lambda m: m.get("modified_at") or "")
                with st.expander(f"📁 {vg['group_name']} ({len(members)} suggested revisions)", expanded=True):
                    for m_idx, m in enumerate(members, 1):
                        is_d = bool(m.get("is_dismissed", 0))

                        c_order, c_name, c_sim, c_date, c_act1, c_act2, c_dismiss = st.columns([0.8, 2.5, 1.2, 1.6, 0.7, 0.9, 1.2])

                        with c_order:
                            st.markdown(f"**Rev {m_idx}**")
                        with c_name:
                            name_display = f"`{m['file_name']}`"
                            if is_d:
                                name_display += " *(Dismissed)*"
                            st.markdown(name_display)
                        with c_sim:
                            score = m.get("similarity_score")
                            score_txt = f"{score * 100:.1f}%" if score is not None else "Base"
                            st.caption(f"Match: {score_txt}")
                        with c_date:
                            st.caption(f"🕒 {m.get('modified_at', 'Unknown')}")
                        with c_act1:
                            if st.button("👁️", key=f"ver_open_{v_idx}_{m['id']}", help="Open File"):
                                ok, msg = open_file_in_os(m["file_path"])
                                if not ok:
                                    st.warning(msg)
                        with c_act2:
                            if st.button("📂", key=f"ver_folder_{v_idx}_{m['id']}", help="Reveal in Folder"):
                                ok, msg = open_folder_in_os(m["file_path"])
                                if not ok:
                                    st.warning(msg)
                        with c_dismiss:
                            if is_d:
                                if st.button("↩️ Restore", key=f"ver_restore_{v_idx}_{m['id']}", help="Restore Suggestion"):
                                    repo.restore_version_member(m["id"])
                                    st.rerun()
                            else:
                                if st.button("❌ Dismiss", key=f"ver_dismiss_{v_idx}_{m['id']}", help="Dismiss Incorrect Match"):
                                    repo.dismiss_version_member(m["id"])
                                    st.rerun()
