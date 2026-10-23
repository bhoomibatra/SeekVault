import os
import streamlit as st
import pandas as pd
from typing import Optional, List, Dict, Any
from pathlib import Path

from seekvault.database.repository import Repository
from seekvault.ui.components import (
    open_file_in_os,
    open_folder_in_os,
    inject_design_system,
)
from seekvault.ui.navigator import get_friendly_folder_name


def render_privacy_center(repo: Repository):
    """
    Direct, efficient Privacy & Sensitive Data dashboard.
    No educational lectures or marketing copy — pure user utility and controls.
    """
    inject_design_system()

    # Clean, concise title
    st.markdown(
        """
        <div style="margin-bottom: 16px;">
            <h1 style="font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-size: 1.65rem; font-weight: 700; color: #15181E; margin: 0 0 4px 0;">
                Privacy & Sensitive Data
            </h1>
            <p style="font-size: 0.88rem; color: #697386; margin: 0;">
                Configure automatic masking for sensitive information and manage flagged files.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col_left, col_right = st.columns([1.1, 1.9], gap="large")

    # ─────────────────────────────────────────────────────────────────────────
    # LEFT COLUMN: Direct Detection & Masking Toggles
    # ─────────────────────────────────────────────────────────────────────────
    with col_left:
        st.markdown(
            """
            <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 8px;">
                Automatic Masking
            </div>
            """,
            unsafe_allow_html=True
        )

        with st.form("privacy_settings_form"):
            mask_mode = st.radio(
                "Masking Mode",
                ["MASK_SNIPPETS", "EXCLUDE_BODY"],
                index=0 if repo.get_setting("privacy_protection_mode", "MASK_SNIPPETS") == "MASK_SNIPPETS" else 1,
                format_func=lambda m: "Mask detected items in search snippets" if m == "MASK_SNIPPETS" else "Hide full body text for flagged files",
                label_visibility="collapsed"
            )

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown("<div style='font-size: 0.82rem; font-weight: 600; color: #4A5160; margin-bottom: 6px;'>DETECTION RULES</div>", unsafe_allow_html=True)

            c_phone = st.checkbox("Phone numbers", value=repo.get_setting("detect_phone", "1") == "1")
            c_email = st.checkbox("Email addresses", value=repo.get_setting("detect_email", "1") == "1")
            c_id = st.checkbox("Government & National IDs (Aadhaar, PAN, SSN)", value=repo.get_setting("detect_id", "1") == "1")
            c_financial = st.checkbox("Credit card & account numbers", value=repo.get_setting("detect_financial", "1") == "1")
            c_creds = st.checkbox("Password & private keys", value=True, disabled=True, help="Always masked for security.")

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            if st.form_submit_button("Save Masking Rules", type="primary", use_container_width=True):
                repo.set_setting("privacy_protection_mode", mask_mode)
                repo.set_setting("detect_phone", "1" if c_phone else "0")
                repo.set_setting("detect_email", "1" if c_email else "0")
                repo.set_setting("detect_id", "1" if c_id else "0")
                repo.set_setting("detect_financial", "1" if c_financial else "0")
                st.success("Preferences saved.")

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="background: #F9F8F6; border: 1px solid #E6E2D8; border-radius: 6px; padding: 12px 14px; font-size: 0.82rem; color: #4A5160; line-height: 1.45;">
                <strong style="color: #15181E;">Preview of search masking:</strong><br/>
                <em>&ldquo;Candidate contact: [PHONE REDACTED] &bull; [EMAIL REDACTED]&rdquo;</em>
                <hr style="border: none; border-top: 1px solid #E6E2D8; margin: 8px 0;" />
                <span style="font-size: 0.78rem; color: #166534; font-weight: 500;">
                    ✓ 100% Local &bull; Original files on your computer are never altered or edited.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    # RIGHT COLUMN: Flagged Files & Masked Records
    # ─────────────────────────────────────────────────────────────────────────
    with col_right:
        st.markdown(
            """
            <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 8px;">
                Files with Detected Personal Data
            </div>
            """,
            unsafe_allow_html=True
        )

        all_entities = repo.get_all_detected_entities()
        total_indexed = len(repo.get_all_indexed_files(limit=1))

        if total_indexed == 0:
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px dashed #D1CBC0; border-radius: 8px; padding: 28px 20px; text-align: center;">
                    <div style="font-size: 0.96rem; font-weight: 600; color: #15181E; margin-bottom: 4px;">No files indexed yet</div>
                    <div style="font-size: 0.84rem; color: #697386;">Add folders or files in File Library to begin indexing and privacy scanning.</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        elif not all_entities:
            st.markdown(
                """
                <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 8px; padding: 22px 20px; text-align: center;">
                    <div style="font-size: 0.96rem; font-weight: 600; color: #166534; margin-bottom: 4px;">✓ Scan completed — No sensitive data detected</div>
                    <div style="font-size: 0.84rem; color: #4A5160;">All indexed files were scanned against active privacy rules and no sensitive personal data was detected.</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            # Group by file
            file_groups: Dict[str, Dict[str, Any]] = {}
            for e in all_entities:
                fpath = e.get("file_path", "")
                fname = e.get("file_name", Path(fpath).name if fpath else "Unknown")
                if fname not in file_groups:
                    file_groups[fname] = {
                        "path": fpath,
                        "types": set(),
                        "items_count": 0,
                    }
                file_groups[fname]["types"].add(e.get("entity_type", "UNKNOWN").replace("_", " ").title())
                file_groups[fname]["items_count"] += 1

            # Summary badges
            types_summary = {}
            for e in all_entities:
                t = e.get("entity_type", "UNKNOWN").replace("_", " ").title()
                types_summary[t] = types_summary.get(t, 0) + 1

            badge_spans = " ".join([
                f'<span style="background:#F0EEE8;color:#15181E;border:1px solid #D1CBC0;border-radius:4px;padding:2px 7px;font-size:0.75rem;font-weight:600;margin-right:6px;">{k}: {v}</span>'
                for k, v in types_summary.items()
            ])
            st.markdown(f"<div style='margin-bottom: 12px;'>{badge_spans}</div>", unsafe_allow_html=True)

            if "pending_exclude_fpath" not in st.session_state:
                st.session_state.pending_exclude_fpath = None

            # Actionable file list
            for fn, data in file_groups.items():
                fpath = data["path"]
                types_str = ", ".join(sorted(data["types"]))
                parent_name = get_friendly_folder_name(str(Path(fpath).parent)) if fpath else "Library"

                with st.container():
                    c_info, c_b1, c_b2, c_b3 = st.columns([2.6, 0.9, 1.1, 0.8])
                    with c_info:
                        st.markdown(
                            f"""
                            <div style="font-size: 0.88rem; font-weight: 600; color: #15181E;">{fn}</div>
                            <div style="font-size: 0.76rem; color: #697386;">
                                In <strong>{parent_name}</strong> &nbsp;•&nbsp; Detected: <span style="color: #92400E; font-weight: 500;">{types_str}</span> ({data['items_count']} items)
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    with c_b1:
                        if st.button("Open File", key=f"p_open_{fn}", use_container_width=True):
                            if fpath:
                                ok, msg = open_file_in_os(fpath)
                                if not ok:
                                    st.warning(msg)
                    with c_b2:
                        if st.button("Show in Folder", key=f"p_rev_{fn}", use_container_width=True):
                            if fpath:
                                ok, msg = open_folder_in_os(fpath)
                                if not ok:
                                    st.warning(msg)
                    with c_b3:
                        if st.button("Exclude", key=f"p_del_{fn}", use_container_width=True, help="Remove from search index (file on disk is not touched)"):
                            st.session_state.pending_exclude_fpath = fpath
                            st.rerun()

                    # Inline confirmation dialog for exclude
                    if st.session_state.get("pending_exclude_fpath") == fpath:
                        st.markdown(
                            f"""
                            <div style="background: #FEF2F2; border: 1px solid #FECACA; border-radius: 6px; padding: 10px 14px; margin: 8px 0 10px 0;">
                                <div style="font-size: 0.86rem; font-weight: 600; color: #B42318; margin-bottom: 2px;">
                                    Confirm Exclusion of &ldquo;{fn}&rdquo;?
                                </div>
                                <div style="font-size: 0.78rem; color: #4A5160;">
                                    This removes the file from your searchable library. The original file on your disk remains completely untouched.
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        c_conf, c_canc = st.columns(2)
                        with c_conf:
                            if st.button("Confirm Exclude", key=f"conf_excl_{fn}", type="primary", use_container_width=True):
                                repo.delete_file_by_path(fpath)
                                st.session_state.pending_exclude_fpath = None
                                st.success(f"Excluded '{fn}' from searchable library. File on disk was untouched.")
                                st.rerun()
                        with c_canc:
                            if st.button("Cancel", key=f"canc_excl_{fn}", use_container_width=True):
                                st.session_state.pending_exclude_fpath = None
                                st.rerun()

                    st.markdown("<hr style='border:none;border-top:1px solid #E6E2D8;margin:6px 0 8px 0;'/>", unsafe_allow_html=True)

            # Audit Table (collapsible)
            with st.expander("View masked token audit table", expanded=False):
                table_rows = []
                for r in all_entities:
                    table_rows.append({
                        "File": r.get("file_name", "Unknown"),
                        "Data Type": r.get("entity_type", "UNKNOWN").replace("_", " ").title(),
                        "Masked Replacement": r.get("entity_token", "<REDACTED>"),
                    })
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True)
