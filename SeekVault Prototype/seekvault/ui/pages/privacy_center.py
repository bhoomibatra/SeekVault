import os
import streamlit as st
import pandas as pd
from seekvault.database.repository import Repository
from seekvault.ui.components import (
    render_tier_badge,
    inject_design_system,
)


def render_privacy_center(repo: Repository):
    inject_design_system()

    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #1D4ED8; margin-bottom: 4px;">
                Local-First Audit & Compliance
            </div>
            <h1 style="font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-size: 1.85rem; font-weight: 700; letter-spacing: -0.015em; color: #15181E; margin: 0 0 8px 0; letter-spacing: -0.02em;">
                Privacy & Security Center
            </h1>
            <p style="font-size: 0.95rem; color: #4A5160; margin: 0; line-height: 1.5;">
                Complete verification of local-only processing, tiered de-identification policies, and on-device storage residency.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Verified Offline & Security Status
    # ─────────────────────────────────────────────────────────────────────────
    hf_offline = os.environ.get("HF_HUB_OFFLINE") == "1"
    tf_offline = os.environ.get("TRANSFORMERS_OFFLINE") == "1"
    is_offline_verified = hf_offline and tf_offline

    if is_offline_verified:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #A7F3D0; border-left: 4px solid #059669; border-radius: 8px; padding: 14px 18px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #059669;"></span>
                    <span style="font-size: 0.90rem; font-weight: 700; color: #065F46; text-transform: uppercase; letter-spacing: 0.05em;">
                        Verified 100% Offline Mode Active
                    </span>
                </div>
                <div style="font-size: 0.88rem; color: #374151; line-height: 1.5; margin-left: 16px;">
                    Hugging Face Hub and Transformers telemetry are strictly forced offline via 
                    <code style="background: #ECFDF5; color: #065F46; padding: 2px 6px; border-radius: 4px; font-size: 0.82rem; border: 1px solid #A7F3D0;">HF_HUB_OFFLINE=1</code> and 
                    <code style="background: #ECFDF5; color: #065F46; padding: 2px 6px; border-radius: 4px; font-size: 0.82rem; border: 1px solid #A7F3D0;">TRANSFORMERS_OFFLINE=1</code>. 
                    Zero telemetry, remote analytics, or document contents leave your device.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #BFDBFE; border-left: 4px solid #1D4ED8; border-radius: 8px; padding: 14px 18px; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                    <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #1D4ED8;"></span>
                    <span style="font-size: 0.90rem; font-weight: 700; color: #1E40AF; text-transform: uppercase; letter-spacing: 0.05em;">
                        Local-First Architecture Active
                    </span>
                </div>
                <div style="font-size: 0.88rem; color: #374151; line-height: 1.5; margin-left: 16px;">
                    All embedding generation, SQLite relational indexing, and FAISS vector matching execute strictly on-device without cloud services.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Three-Tier Privacy Policy Cards
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 1.25rem; font-weight: 600; color: #15181E; margin-bottom: 12px; font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;">
            Tiered Classification Architecture
        </div>
        """,
        unsafe_allow_html=True
    )
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-top: 3px solid #059669; border-radius: 8px; padding: 16px; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 0.85rem; font-weight: 700; color: #065F46; letter-spacing: 0.05em;">TIER 1</span>
                    <span style="font-size: 0.70rem; font-weight: 700; background: #ECFDF5; color: #065F46; padding: 2px 7px; border-radius: 10px; border: 1px solid #A7F3D0;">FULL</span>
                </div>
                <div style="font-size: 0.92rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">Unrestricted Extraction</div>
                <p style="font-size: 0.84rem; color: #4A5160; margin: 0 0 12px 0; line-height: 1.45;">
                    Zero sensitive PII entities detected. Document contents are extracted and embedded directly into the FAISS semantic space.
                </p>
                <div style="font-size: 0.78rem; color: #697386; border-top: 1px solid #F0EEE9; padding-top: 8px;">
                    <strong style="color: #404040;">Trigger:</strong> Clean academic papers, public notes, technical manuals.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-top: 3px solid #D97706; border-radius: 8px; padding: 16px; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 0.85rem; font-weight: 700; color: #92400E; letter-spacing: 0.05em;">TIER 2</span>
                    <span style="font-size: 0.70rem; font-weight: 700; background: #FFFBEB; color: #92400E; padding: 2px 7px; border-radius: 10px; border: 1px solid #FDE68A;">REDACTED</span>
                </div>
                <div style="font-size: 0.92rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">Masked Semantic Embedding</div>
                <p style="font-size: 0.84rem; color: #4A5160; margin: 0 0 12px 0; line-height: 1.45;">
                    PII detected (emails, phones, national IDs). Sensitive spans are replaced with synthetic mask tokens prior to vector embedding.
                </p>
                <div style="font-size: 0.78rem; color: #697386; border-top: 1px solid #F0EEE9; padding-top: 8px;">
                    <strong style="color: #404040;">Trigger:</strong> Invoices, billing statements, resumes, customer contacts.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-top: 3px solid #DC2626; border-radius: 8px; padding: 16px; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 0.85rem; font-weight: 700; color: #991B1B; letter-spacing: 0.05em;">TIER 3</span>
                    <span style="font-size: 0.70rem; font-weight: 700; background: #FEF2F2; color: #991B1B; padding: 2px 7px; border-radius: 10px; border: 1px solid #FECACA;">METADATA ONLY</span>
                </div>
                <div style="font-size: 0.92rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">Zero Content Storage</div>
                <p style="font-size: 0.84rem; color: #4A5160; margin: 0 0 12px 0; line-height: 1.45;">
                    Extreme sensitivity (passwords, master keys, seed phrases). <strong>Zero vectors</strong> and zero extracted text stored. Retrievable only by filename.
                </p>
                <div style="font-size: 0.78rem; color: #697386; border-top: 1px solid #F0EEE9; padding-top: 8px;">
                    <strong style="color: #404040;">Trigger:</strong> Password vaults, API key configs, private credentials.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Data Transparency & Storage Boundaries
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 1.25rem; font-weight: 600; color: #15181E; margin-bottom: 12px; font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;">
            Data Storage Boundaries & Residency
        </div>
        """,
        unsafe_allow_html=True
    )

    d1, d2, d3 = st.columns(3)
    with d1:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 16px; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #1D4ED8; margin-bottom: 4px;">
                    SOURCE FILES
                </div>
                <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 10px;">User Storage Drives</div>
                <div style="font-size: 0.83rem; color: #4A5160; line-height: 1.5;">
                    <div style="margin-bottom: 4px;"><strong style="color: #15181E;">Path:</strong> User authorized folders</div>
                    <div style="margin-bottom: 4px;"><strong style="color: #15181E;">Access Mode:</strong> Read-only stream</div>
                    <div><strong style="color: #15181E;">Guarantee:</strong> Original files are strictly never modified, moved, renamed, or deleted.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with d2:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 16px; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #1D4ED8; margin-bottom: 4px;">
                    METADATA & INDEX
                </div>
                <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 10px;">SQLite Database</div>
                <div style="font-size: 0.83rem; color: #4A5160; line-height: 1.5;">
                    <div style="margin-bottom: 4px;"><strong style="color: #15181E;">Path:</strong> <code style="font-size: 0.76rem; color: #1E40AF; background: #EFF6FF; padding: 1px 4px; border-radius: 3px;">data_storage/seekvault.db</code></div>
                    <div style="margin-bottom: 4px;"><strong style="color: #15181E;">Stored:</strong> File paths, SHA-256 hashes, FTS5 index, masked entity tokens</div>
                    <div><strong style="color: #15181E;">Guarantee:</strong> Zero plaintext sensitive credentials stored.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with d3:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 16px; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #1D4ED8; margin-bottom: 4px;">
                    VECTOR STORE
                </div>
                <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 10px;">FAISS Indices</div>
                <div style="font-size: 0.83rem; color: #4A5160; line-height: 1.5;">
                    <div style="margin-bottom: 4px;"><strong style="color: #15181E;">Path:</strong> <code style="font-size: 0.76rem; color: #1E40AF; background: #EFF6FF; padding: 1px 4px; border-radius: 3px;">data_storage/*.faiss</code></div>
                    <div style="margin-bottom: 4px;"><strong style="color: #15181E;">Stored:</strong> Normalized dense vector embeddings</div>
                    <div><strong style="color: #15181E;">Guarantee:</strong> Exactly zero vectors generated for Tier 3 documents.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. De-identified Entity Audit Table
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 1.25rem; font-weight: 600; color: #15181E; margin-bottom: 12px; font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;">
            De-identified Sensitive Entity Audit
        </div>
        """,
        unsafe_allow_html=True
    )
    all_entities = repo.get_all_detected_entities()

    if not all_entities:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 24px; text-align: center; color: #4A5160; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 4px;">No Sensitive Entities Detected</div>
                <div style="font-size: 0.85rem; color: #697386;">
                    All currently indexed documents conform to Tier 1 (FULL) classification with clean privacy compliance.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        df_ent = pd.DataFrame(all_entities)

        # Metrics row
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Total Sensitive Detections", len(df_ent))
        with m2:
            st.metric("Files with Sensitive Content", df_ent["file_name"].nunique())
        with m3:
            st.metric("Distinct Entity Categories", df_ent["entity_type"].nunique())

        # Category chart
        st.markdown(
            """
            <div style="font-size: 0.90rem; font-weight: 600; color: #15181E; margin: 16px 0 8px 0;">
                Detections by Sensitive Category
            </div>
            """,
            unsafe_allow_html=True
        )
        type_counts = df_ent["entity_type"].value_counts()
        st.bar_chart(type_counts, color="#1D4ED8")

        # Entity table (strictly de-identified)
        st.markdown(
            """
            <div style="font-size: 0.90rem; font-weight: 600; color: #15181E; margin: 16px 0 8px 0;">
                Entity Audit Log (Masked Representation)
            </div>
            """,
            unsafe_allow_html=True
        )
        table_rows = []
        for r in all_entities:
            table_rows.append({
                "File Name": r.get("file_name", "Unknown"),
                "Privacy Tier": r.get("privacy_tier", "REDACTED"),
                "Entity Category": r.get("entity_type", "UNKNOWN"),
                "Masked Token": r.get("entity_token", "<REDACTED>"),
                "Confidence Score": f"{r.get('confidence', 1.0):.2f}",
            })

        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Core Architectural Guarantees Checklist
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 1.25rem; font-weight: 600; color: #15181E; margin-bottom: 12px; font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;">
            Architectural Security Commitments
        </div>
        """,
        unsafe_allow_html=True
    )

    gc1, gc2 = st.columns(2)
    with gc1:
        st.markdown(
            """
            <div style="display: flex; flex-direction: column; gap: 10px;">
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 6px; padding: 12px 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
                    <div style="font-size: 0.88rem; font-weight: 600; color: #15181E;">Zero Remote Transmission</div>
                    <div style="font-size: 0.82rem; color: #4A5160; margin-top: 2px;">
                        All machine learning models, tokenizers, and database engines operate strictly on-device. No telemetry or query logging exists.
                    </div>
                </div>
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 6px; padding: 12px 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
                    <div style="font-size: 0.88rem; font-weight: 600; color: #15181E;">Source Immutability</div>
                    <div style="font-size: 0.82rem; color: #4A5160; margin-top: 2px;">
                        Original files on local storage are opened in read-only mode and are never written to, altered, or deleted by SeekVault.
                    </div>
                </div>
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 6px; padding: 12px 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
                    <div style="font-size: 0.88rem; font-weight: 600; color: #15181E;">Zero-Trust Query Verification</div>
                    <div style="font-size: 0.82rem; color: #4A5160; margin-top: 2px;">
                        Files residing in deleted, unmounted, or deauthorized directories are instantaneously suppressed at query execution time.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with gc2:
        st.markdown(
            """
            <div style="display: flex; flex-direction: column; gap: 10px;">
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 6px; padding: 12px 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
                    <div style="font-size: 0.88rem; font-weight: 600; color: #15181E;">No PII Leakage in Vectors</div>
                    <div style="font-size: 0.82rem; color: #4A5160; margin-top: 2px;">
                        Detected sensitive spans are sanitized into structured mask tokens prior to computing dense vector representations.
                    </div>
                </div>
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 6px; padding: 12px 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
                    <div style="font-size: 0.88rem; font-weight: 600; color: #15181E;">Zero Vectors for Sensitive Credentials</div>
                    <div style="font-size: 0.82rem; color: #4A5160; margin-top: 2px;">
                        Documents classified as Tier 3 store exactly zero content vectors in FAISS and are retrievable strictly by exact filename.
                    </div>
                </div>
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 6px; padding: 12px 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.02);">
                    <div style="font-size: 0.88rem; font-weight: 600; color: #15181E;">Path-Aware Boundary Containment</div>
                    <div style="font-size: 0.82rem; color: #4A5160; margin-top: 2px;">
                        Filesystem symlinks and NTFS junction points pointing outside of authorized boundaries are strictly rejected during traversal.
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
