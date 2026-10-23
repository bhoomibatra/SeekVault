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
            <h1 style="font-size: 2.2rem; font-weight: 700; margin-bottom: 6px; color: #F3F4F6;">
                🛡️ Privacy & Security Center
            </h1>
            <p style="font-size: 0.95rem; color: #9CA3AF; margin-top: 0;">
                Complete transparency into local-only processing, tiered de-identification policies, and data residency.
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
            <div style="background-color: #064E3B; border: 1px solid #10B981; border-radius: 8px; padding: 12px 18px; margin-bottom: 20px;">
                <span style="font-size: 1rem; font-weight: 600; color: #A7F3D0;">🟢 Verified 100% Offline Mode:</span>
                <span style="font-size: 0.90rem; color: #D1FAE5; margin-left: 6px;">
                    Hugging Face Hub and Transformers telemetry are strictly forced offline (<code>HF_HUB_OFFLINE=1</code>, <code>TRANSFORMERS_OFFLINE=1</code>). 
                    No telemetry, model downloads, or document contents leave your device.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="background-color: #1E293B; border: 1px solid #6366F1; border-radius: 8px; padding: 12px 18px; margin-bottom: 20px;">
                <span style="font-size: 1rem; font-weight: 600; color: #E0E7FF;">🛡️ Local-First Architecture:</span>
                <span style="font-size: 0.90rem; color: #C7D2FE; margin-left: 6px;">
                    All embeddings, SQLite metadata, and FAISS vector matching execute locally on-device without cloud services.
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Three-Tier Privacy Policy Cards (Obsidian Slate Theme)
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("Tiered Classification Architecture")
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(
            """
            <div class="seekvault-search-card" style="border-left: 4px solid #10B981;">
                <h3 style="color: #10B981; margin: 0 0 6px 0; font-size: 1.15rem;">FULL TIER</h3>
                <p style="font-size: 0.88rem; color: #9CA3AF; margin: 0 0 10px 0; line-height: 1.4;">
                    Zero sensitive PII entities detected. Document contents are extracted and embedded directly into the FAISS semantic space.
                </p>
                <div style="font-size: 0.80rem; color: #6B7280; border-top: 1px solid #24324D; padding-top: 8px;">
                    <strong>Trigger:</strong> Clean academic papers, notes, public manuals.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            """
            <div class="seekvault-search-card" style="border-left: 4px solid #F59E0B;">
                <h3 style="color: #F59E0B; margin: 0 0 6px 0; font-size: 1.15rem;">REDACTED TIER</h3>
                <p style="font-size: 0.88rem; color: #9CA3AF; margin: 0 0 10px 0; line-height: 1.4;">
                    Moderate PII detected (emails, phones, IDs). Sensitive spans are replaced with masked tokens before embedding.
                </p>
                <div style="font-size: 0.80rem; color: #6B7280; border-top: 1px solid #24324D; padding-top: 8px;">
                    <strong>Trigger:</strong> Invoices, admission forms, resumes, contact lists.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c3:
        st.markdown(
            """
            <div class="seekvault-search-card" style="border-left: 4px solid #EF4444;">
                <h3 style="color: #EF4444; margin: 0 0 6px 0; font-size: 1.15rem;">METADATA ONLY</h3>
                <p style="font-size: 0.88rem; color: #9CA3AF; margin: 0 0 10px 0; line-height: 1.4;">
                    Extreme sensitivity (passwords, master keys, seed phrases). <strong>Zero content vectors</strong> stored. Retrievable only by filename.
                </p>
                <div style="font-size: 0.80rem; color: #6B7280; border-top: 1px solid #24324D; padding-top: 8px;">
                    <strong>Trigger:</strong> Password vaults, API key configs, private credentials.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Data Transparency & Storage Boundaries
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("Data Storage Boundaries & Residency")

    d1, d2, d3 = st.columns(3)
    with d1:
        st.markdown(
            """
            <div class="seekvault-search-card">
                <h4 style="color: #F3F4F6; margin: 0 0 6px 0;">📂 Original Files</h4>
                <p style="font-size: 0.85rem; color: #9CA3AF; line-height: 1.4;">
                    <strong>Location:</strong> Your local user directories.<br>
                    <strong>Access:</strong> Read-only parsing.<br>
                    <strong>Policy:</strong> Files are strictly never modified, moved, renamed, or deleted.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with d2:
        st.markdown(
            """
            <div class="seekvault-search-card">
                <h4 style="color: #F3F4F6; margin: 0 0 6px 0;">🗄️ SQLite Database</h4>
                <p style="font-size: 0.85rem; color: #9CA3AF; line-height: 1.4;">
                    <strong>Location:</strong> <code>data_storage/seekvault.db</code><br>
                    <strong>Stored:</strong> Paths, SHA-256 hashes, FTS5 shadow index, and masked entity tokens.<br>
                    <strong>Policy:</strong> Zero raw credentials stored.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with d3:
        st.markdown(
            """
            <div class="seekvault-search-card">
                <h4 style="color: #F3F4F6; margin: 0 0 6px 0;">⚡ FAISS Vector Indices</h4>
                <p style="font-size: 0.85rem; color: #9CA3AF; line-height: 1.4;">
                    <strong>Location:</strong> <code>data_storage/*.faiss</code><br>
                    <strong>Stored:</strong> 384-d text and 512-d CLIP vector embeddings.<br>
                    <strong>Policy:</strong> Exactly zero vectors stored for METADATA_ONLY files.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. De-identified Entity Audit Table
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("De-identified Sensitive Entity Audit")
    all_entities = repo.get_all_detected_entities()

    if not all_entities:
        st.info("No sensitive entities have been detected in currently indexed files.")
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
        st.markdown("##### Detections by Sensitive Category")
        type_counts = df_ent["entity_type"].value_counts()
        st.bar_chart(type_counts, color="#6366F1")

        # Entity table (strictly de-identified)
        st.markdown("##### Entity Audit Log (Masked Representation)")
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

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Core Architectural Guarantees Checklist
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Core Architectural Guarantees")

    gc1, gc2 = st.columns(2)
    with gc1:
        st.markdown(
            """
            - ✅ **Zero Remote Transmission:** All ML models, tokenizers, and database engines operate strictly on-device.
            - ✅ **Source Immutability:** File contents on disk are never altered, overwritten, or deleted by SeekVault.
            - ✅ **Zero-Trust Query Verification:** Files located in deleted or revoked folders are blocked at query time.
            """
        )
    with gc2:
        st.markdown(
            """
            - ✅ **No PII Leakage in Vectors:** Redacted spans are replaced with masked tokens prior to embedding generation.
            - ✅ **Zero Vectors for Sensitive Credentials:** Files containing master keys or passwords store exactly zero vectors in FAISS.
            - ✅ **Path-Aware Containment:** Symlinks and junctions targeting outside authorized roots are rejected.
            """
        )
