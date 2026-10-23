import os
import streamlit as st
import pandas as pd
from pathlib import Path

from seekvault.database.repository import Repository
from seekvault.organization.version_detector import VersionDetector
from seekvault.ui.components import (
    format_file_size,
    open_file_in_os,
    open_folder_in_os,
    inject_design_system,
)
from seekvault.ui.navigator import get_friendly_folder_name


def render_duplicates_versions_page(repo: Repository):
    """
    Stage 6: Duplicates & Versions.
    Provides clear, restrained audit of exact file duplicates and advisory version lineage.
    Never auto-deletes original files.
    """
    inject_design_system()

    # Page Header
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h1 style="font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-size: 1.65rem; font-weight: 700; color: #15181E; margin: 0 0 4px 0;">
                Duplicates & Versions
            </h1>
            <p style="font-size: 0.88rem; color: #697386; margin: 0;">
                Review identical files to reclaim disk space, and inspect suggested document revisions.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_dup, tab_ver = st.tabs(["Duplicate Files", "Document Revisions"])


    # ═════════════════════════════════════════════════════════════════════════
    # TAB 1: EXACT DUPLICATES
    # ═════════════════════════════════════════════════════════════════════════
    with tab_dup:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-left: 4px solid #1D4ED8; border-radius: 8px; padding: 14px 18px; margin-bottom: 22px;">
                <div style="font-size: 0.86rem; font-weight: 700; color: #1E40AF; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 3px;">
                    Safe Audit Policy
                </div>
                <div style="font-size: 0.84rem; color: #374151; line-height: 1.5;">
                    SeekVault identifies exact copies sharing identical file contents so you can reclaim disk space. 
                    <strong>Original files are never automatically deleted, moved, or altered.</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        dup_groups = repo.get_duplicate_groups()

        if not dup_groups:
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 22px; text-align: center; color: #4A5160;">
                    <div style="font-size: 0.92rem; font-weight: 600; color: #15181E; margin-bottom: 3px;">No Duplicate Files Found</div>
                    <div style="font-size: 0.82rem; color: #697386;">
                        All files across your monitored folders have unique contents.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            total_reclaimable = sum(g["reclaimable_size"] for g in dup_groups)
            total_redundant = sum(g["file_count"] - 1 for g in dup_groups)

            m1, m2, m3 = st.columns(3)
            with m1:
                st.markdown(
                    f"""
                    <div style="background:#FFFFFF;border:1px solid #E6E2D8;border-radius:8px;padding:12px;text-align:center;">
                        <div style="font-size:1.30rem;font-weight:700;color:#15181E;">{len(dup_groups)}</div>
                        <div style="font-size:0.75rem;color:#697386;margin-top:2px;">Duplicate Groups</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with m2:
                st.markdown(
                    f"""
                    <div style="background:#FFFFFF;border:1px solid #E6E2D8;border-radius:8px;padding:12px;text-align:center;">
                        <div style="font-size:1.30rem;font-weight:700;color:#D97706;">{total_redundant}</div>
                        <div style="font-size:0.75rem;color:#697386;margin-top:2px;">Redundant Copies</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            with m3:
                st.markdown(
                    f"""
                    <div style="background:#FFFFFF;border:1px solid #E6E2D8;border-radius:8px;padding:12px;text-align:center;">
                        <div style="font-size:1.30rem;font-weight:700;color:#10B981;">{format_file_size(total_reclaimable)}</div>
                        <div style="font-size:0.75rem;color:#697386;margin-top:2px;">Potential Reclaimable Space</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

            for idx, g in enumerate(dup_groups, 1):
                first_name = Path(g["file_paths"][0]).name if g["file_paths"] else f"Group #{idx}"
                cluster_label = f"{first_name} — {g['file_count']} identical copies ({format_file_size(g['reclaimable_size'])} reclaimable)"

                with st.expander(cluster_label, expanded=True):
                    st.caption(f"Individual File Size: {format_file_size(g.get('file_size') or (g['total_size'] // g['file_count']))} | Total Storage Used: {format_file_size(g['total_size'])}")

                    for p_idx, p in enumerate(g["file_paths"]):
                        p_path = Path(p)
                        friendly_parent = get_friendly_folder_name(str(p_path.parent))
                        copy_badge = (
                            '<span style="background:#ECFDF5;color:#065F46;border:1px solid #A7F3D0;border-radius:4px;padding:2px 6px;font-size:0.72rem;font-weight:600;">Original</span>'
                            if p_idx == 0 else
                            '<span style="background:#FEF3C7;color:#92400E;border:1px solid #FDE68A;border-radius:4px;padding:2px 6px;font-size:0.72rem;font-weight:600;">Duplicate Copy</span>'
                        )

                        c_path, c_btn1, c_btn2 = st.columns([3.4, 1.2, 1.4])
                        with c_path:
                            st.markdown(
                                f"""
                                <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                                    {copy_badge}
                                    <span style="font-size: 0.88rem; font-weight: 600; color: #15181E;">{p_path.name}</span>
                                    <span style="font-size: 0.78rem; color: #697386;">in {friendly_parent}</span>
                                </div>
                                <div style="font-size: 0.72rem; color: #697386; font-family: 'JetBrains Mono', Consolas, monospace; word-break: break-all; margin-top: 2px;">
                                    {p}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        with c_btn1:
                            if st.button("Open File", key=f"dup_open_{idx}_{p_idx}", use_container_width=True):
                                ok, msg = open_file_in_os(p)
                                if not ok:
                                    st.warning(msg)
                        with c_btn2:
                            if st.button("Show in Folder", key=f"dup_reveal_{idx}_{p_idx}", use_container_width=True):
                                ok, msg = open_folder_in_os(p)
                                if not ok:
                                    st.warning(msg)

                        st.markdown("<hr style='border: none; border-top: 1px solid #E6E2D8; margin: 6px 0 8px 0;'/>", unsafe_allow_html=True)

    # ═════════════════════════════════════════════════════════════════════════
    # TAB 2: PROBABLE VERSIONS (HEURISTIC SUGGESTIONS)
    # ═════════════════════════════════════════════════════════════════════════
    with tab_ver:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #BFDBFE; border-left: 4px solid #1D4ED8; border-radius: 8px; padding: 14px 18px; margin-bottom: 22px;">
                <div style="font-size: 0.86rem; font-weight: 700; color: #1E40AF; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 3px;">
                    Advisory Version Suggestions
                </div>
                <div style="font-size: 0.84rem; color: #374151; line-height: 1.5;">
                    SeekVault identifies related document revisions using filename patterns and high content similarity. 
                    These are <strong>automated suggestions for review</strong>, not a strict version control history. You can dismiss any inaccurate matches.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_ref, col_dismissed = st.columns([1.5, 1])
        with col_ref:
            if st.button("Refresh Version Detection", key="btn_refresh_versions", type="primary"):
                with st.spinner("Analyzing document revisions across indexed files..."):
                    VersionDetector.detect_and_update_versions(repo)
                st.success("Version suggestions updated.")
                st.rerun()

        with col_dismissed:
            show_dismissed = st.checkbox("Show dismissed suggestions", value=False)

        version_groups = repo.get_all_version_groups(include_dismissed=show_dismissed)

        if not version_groups:
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 22px; text-align: center; color: #4A5160;">
                    <div style="font-size: 0.92rem; font-weight: 600; color: #15181E; margin-bottom: 3px;">No Version Chains Detected</div>
                    <div style="font-size: 0.82rem; color: #697386;">
                        When multiple revisions of a document exist (e.g., <code>Proposal_v1.docx</code> and <code>Proposal_Final.docx</code>), they will appear grouped here.
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            for v_idx, vg in enumerate(version_groups, 1):
                # Sort revisions chronologically by modification timestamp
                members = sorted(vg["members"], key=lambda m: m.get("modified_at") or "")
                with st.expander(f"{vg['group_name']} ({len(members)} revisions)", expanded=True):
                    for m_idx, m in enumerate(members, 1):
                        is_d = bool(m.get("is_dismissed", 0))

                        is_latest = (m_idx == len(members))
                        latest_badge = '<span style="background:#ECFDF5;color:#065F46;border:1px solid #A7F3D0;border-radius:4px;padding:2px 6px;font-size:0.72rem;font-weight:600;margin-left:6px;">Latest</span>' if is_latest else ""

                        c_info, c_actions = st.columns([3.4, 2.6])

                        with c_info:
                            score = m.get("similarity_score")
                            score_txt = f"{score * 100:.0f}% similarity" if score is not None else "Base Document"
                            mod_date = m.get('modified_at', 'Unknown')
                            name_display = f"<strong>Rev {m_idx}:</strong> {m['file_name']} {latest_badge}"
                            if is_d:
                                name_display += " <em>(Dismissed)</em>"
                            st.markdown(
                                f"""
                                <div style="font-size: 0.90rem; font-weight: 600; color: #15181E; line-height: 1.4;">
                                    {name_display}
                                </div>
                                <div style="font-size: 0.78rem; color: #697386; margin-top: 2px;">
                                    {score_txt} &nbsp;•&nbsp; Modified {mod_date}
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                        with c_actions:
                            ac1, ac2, ac3 = st.columns([1.1, 1.3, 1.0])
                            with ac1:
                                if st.button("Open File", key=f"ver_open_{v_idx}_{m['id']}", use_container_width=True):
                                    ok, msg = open_file_in_os(m["file_path"])
                                    if not ok:
                                        st.warning(msg)
                            with ac2:
                                if st.button("Show in Folder", key=f"ver_folder_{v_idx}_{m['id']}", use_container_width=True):
                                    ok, msg = open_folder_in_os(m["file_path"])
                                    if not ok:
                                        st.warning(msg)
                            with ac3:
                                if is_d:
                                    if st.button("Restore", key=f"ver_restore_{v_idx}_{m['id']}", use_container_width=True):
                                        repo.restore_version_member(m["id"])
                                        st.rerun()
                                else:
                                    if st.button("Dismiss", key=f"ver_dismiss_{v_idx}_{m['id']}", use_container_width=True):
                                        repo.dismiss_version_member(m["id"])
                                        st.rerun()
