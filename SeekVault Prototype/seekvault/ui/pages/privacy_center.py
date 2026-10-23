import streamlit as st
import pandas as pd
from seekvault.database.repository import Repository
from seekvault.ui.components import render_tier_badge

def render_privacy_center(repo: Repository):
    st.header("🛡️ Privacy Center & De-identification Audit")
    st.markdown("Comprehensive view of detected sensitive entities, tiered classification policies, and local indexing treatments.")

    # Educational Policy Cards
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            """
            <div style="border: 1px solid #10B981; border-radius: 8px; padding: 15px; background: #ECFDF5;">
                <h4 style="color: #065F46; margin: 0;">Tier: FULL</h4>
                <p style="font-size: 0.88rem; color: #047857; margin-top: 6px;">
                    No sensitive entities detected. Content is embedded directly into local FAISS vector space.
                </p>
            </div>
            """, unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            """
            <div style="border: 1px solid #F59E0B; border-radius: 8px; padding: 15px; background: #FFFBEB;">
                <h4 style="color: #92400E; margin: 0;">Tier: REDACTED</h4>
                <p style="font-size: 0.88rem; color: #B45309; margin-top: 6px;">
                    Sensitive entities detected. Tokens are replaced with placeholders in index vectors. Original files are <b>never modified</b>.
                </p>
            </div>
            """, unsafe_allow_html=True
        )
    with c3:
        st.markdown(
            """
            <div style="border: 1px solid #EF4444; border-radius: 8px; padding: 15px; background: #FEF2F2;">
                <h4 style="color: #991B1B; margin: 0;">Tier: METADATA_ONLY</h4>
                <p style="font-size: 0.88rem; color: #B91C1C; margin-top: 6px;">
                    Extreme sensitivity (passwords, master keys). <b>Zero content vectors</b> are stored. Retrievable only via filename/path.
                </p>
            </div>
            """, unsafe_allow_html=True
        )

    st.markdown("---")

    # Detected Entities Audit Table
    st.subheader("Detected Sensitive Entities Across Indexed Files")
    all_entities = repo.get_all_detected_entities()

    if not all_entities:
        st.info("No sensitive entities have been detected in currently indexed files.")
    else:
        df_ent = pd.DataFrame(all_entities)
        
        # Entity breakdown chart
        type_counts = df_ent["entity_type"].value_counts()
        st.bar_chart(type_counts, color="#F59E0B")

        cols = [c for c in ["file_name", "privacy_tier", "entity_type", "entity_token", "confidence"] if c in df_ent.columns]
        st.dataframe(df_ent[cols], use_container_width=True)

    # Privacy Guarantee Checklist
    st.markdown("---")
    st.subheader("SeekVault Privacy Guarantees")
    st.success("✅ **Zero Cloud Transmission**: No file contents, embeddings, or metadata leave your local machine.")
    st.success("✅ **Original Integrity Preserved**: Original user files are never altered, renamed, moved, or deleted.")
    st.success("✅ **Zero-Trust Query Verification**: Files from revoked or deleted folders are suppressed at query time.")
