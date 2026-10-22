import streamlit as st
import pandas as pd
from seekvault.database.repository import Repository
from seekvault.ui.components import (
    render_tier_badge,
    format_file_size,
    open_file_in_os,
    open_folder_in_os
)

def render_indexed_files_page(repo: Repository):
    st.header("📄 Indexed Files Explorer")
    st.markdown("Inspect all files indexed by SeekVault with their metadata, privacy status, and cryptographic hashes.")

    c1, c2 = st.columns([1, 1])
    with c1:
        type_filter = st.selectbox("Filter File Type", ["All", "DOCUMENT", "IMAGE"])
    with c2:
        tier_filter = st.selectbox("Filter Privacy Tier", ["All", "FULL", "REDACTED", "METADATA_ONLY"])

    f_type = None if type_filter == "All" else type_filter
    f_tier = None if tier_filter == "All" else tier_filter

    files = repo.get_all_indexed_files(limit=300, file_type=f_type, privacy_tier=f_tier)

    if not files:
        st.info("No files matching the selected filters.")
        return

    st.subheader(f"Total Files: {len(files)}")

    # Display Files Table
    table_data = []
    for f in files:
        table_data.append({
            "ID": f["id"],
            "File Name": f["file_name"],
            "Type": f["file_type"],
            "Extension": f["file_extension"],
            "Size": format_file_size(f["file_size"]),
            "Privacy Tier": f["privacy_tier"],
            "OCR": "Yes" if f.get("has_ocr") else "No",
            "Indexed At": f["indexed_at"]
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)

    # Detailed File Inspection Expander
    st.subheader("🔍 Deep File Inspector")
    file_options = {f"{f['id']}: {f['file_name']} ({f['privacy_tier']})": f for f in files}
    selected_key = st.selectbox("Select file to inspect details:", list(file_options.keys()))

    if selected_key:
        sel_file = file_options[selected_key]
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown(f"**Canonical Path:** `{sel_file['file_path']}`")
            st.markdown(f"**File Hash (SHA-256):** `{sel_file['file_hash']}`")
            st.markdown(f"**Privacy Tier:** {render_tier_badge(sel_file['privacy_tier'])}", unsafe_allow_html=True)
        with col_m2:
            st.markdown(f"**Last Modified:** `{sel_file['modified_at']}`")
            st.markdown(f"**File Size:** {format_file_size(sel_file['file_size'])}")

        btn_c1, btn_c2, _ = st.columns([1, 1.3, 3])
        with btn_c1:
            if st.button("👁️ Open File", key=f"inspect_open_file_{sel_file['id']}"):
                ok, msg = open_file_in_os(sel_file["file_path"])
                if not ok:
                    st.warning(msg)
        with btn_c2:
            if st.button("📂 Open in Folder", key=f"inspect_open_folder_{sel_file['id']}"):
                ok, msg = open_folder_in_os(sel_file["file_path"])
                if not ok:
                    st.warning(msg)

        content = repo.get_file_content(sel_file["id"])
        if content:
            c_raw, c_red = st.columns(2)
            with c_raw:
                st.markdown("**Original Extracted Text Preview:**")
                st.code(content.get("searchable_text_preview", "") or "[No text]", language="text")
            with c_red:
                st.markdown("**Searchable / Redacted Representation:**")
                st.code(content.get("redacted_preview", "") or "[No text]", language="text")

        entities = repo.get_detected_entities_for_file(sel_file["id"])
        if entities:
            st.markdown("**Detected Sensitive Entities:**")
            st.dataframe(pd.DataFrame(entities)[["entity_type", "entity_text", "confidence", "start_char", "end_char"]])
