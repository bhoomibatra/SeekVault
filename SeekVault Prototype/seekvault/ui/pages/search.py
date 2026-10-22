import streamlit as st
import os
from PIL import Image
from seekvault.search.engine import SearchEngine
from seekvault.ui.components import (
    render_tier_badge,
    render_score_bar,
    format_file_size,
    open_file_in_os,
    open_folder_in_os
)

def render_search_page(search_engine: SearchEngine):
    st.header("🔍 Multimodal Semantic Search")
    st.markdown("Search across local documents and images using natural language queries.")

    stats = search_engine.repository.get_dashboard_stats()
    if stats["total_files"] == 0:
        st.info(
            "📂 **No files are currently indexed.** To use semantic search, please authorize a folder containing documents or images in the **📁 Authorized Folders** tab."
        )
        return

    # Search Bar
    query = st.text_input(
        "Enter natural language query:",
        placeholder="e.g., 'notes about candidate elimination', 'database normalization', 'red car near a building', 'screenshot with java error'",
        key="search_query_input"
    )

    # Filters & Sliders Row
    c1, c2, c3 = st.columns([1.5, 1.5, 2])
    with c1:
        modality = st.selectbox("Search Modality", ["All (Multimodal)", "Documents Only", "Images Only"])
    with c2:
        tier_filter = st.selectbox("Filter by Privacy Tier", ["All Tiers", "FULL", "REDACTED", "METADATA_ONLY"])
    with c3:
        min_score = st.slider("Minimum Similarity Score", min_value=0.10, max_value=0.90, value=0.25, step=0.05)

    if query.strip():
        with st.spinner("Searching semantic vector index & verifying access..."):
            if modality == "Documents Only":
                raw_results = search_engine.search_text(query, top_k=15, min_score=min_score)
            elif modality == "Images Only":
                raw_results = search_engine.search_images(query, top_k=15, min_score=min_score)
            else:
                raw_results = search_engine.search_all(query, top_k=15, min_score=min_score)

        # Apply optional UI tier filter
        if tier_filter != "All Tiers":
            results = [r for r in raw_results if r["privacy_tier"] == tier_filter]
        else:
            results = raw_results

        st.subheader(f"Results ({len(results)} matches found)")

        if not results:
            st.info(f"No matching files found for query '{query}' with score threshold ≥ {min_score:.2f}.")
        else:
            for idx, res in enumerate(results, 1):
                with st.container():
                    col_info, col_visual = st.columns([3, 1.2])

                    with col_info:
                        # Header with badge and score
                        tier_html = render_tier_badge(res["privacy_tier"])
                        score_pct = int(res["similarity_score"] * 100)
                        
                        st.markdown(
                            f"### {idx}. {res['file_name']} &nbsp; {tier_html} &nbsp; <span style='font-size:0.9rem; color:#6B7280;'>Match: {score_pct}% (Score: {res['similarity_score']:.3f})</span>",
                            unsafe_allow_html=True
                        )
                        st.markdown(render_score_bar(res["similarity_score"]), unsafe_allow_html=True)
                        st.caption(f"📁 Path: `{res['file_path']}` | Size: {format_file_size(res['file_size'])} | Modified: {res['modified_at']}")

                        # Snippet Preview
                        if res.get("preview"):
                            with st.expander("📄 View Content Preview", expanded=True):
                                if res["privacy_tier"] == "REDACTED":
                                    st.warning("🛡️ Privacy Notice: Sensitive entities were redacted from the searchable index.")
                                st.markdown(f"```\n{res['preview'][:500]}...\n```")

                        # Entities Preview
                        if res.get("entities"):
                            ent_types = set(e["entity_type"] for e in res["entities"])
                            st.caption(f"🛡️ Detected PII Tokens: {', '.join(ent_types)}")

                        # Native OS Shell Actions
                        btn_c1, btn_c2, _ = st.columns([1, 1.3, 2])
                        with btn_c1:
                            if st.button("👁️ Open File", key=f"btn_open_file_{res['file_id']}_{idx}"):
                                ok, msg = open_file_in_os(res["file_path"])
                                if not ok:
                                    st.warning(msg)
                        with btn_c2:
                            if st.button("📂 Open in Folder", key=f"btn_open_folder_{res['file_id']}_{idx}"):
                                ok, msg = open_folder_in_os(res["file_path"])
                                if not ok:
                                    st.warning(msg)

                    with col_visual:
                        # If image, show thumbnail!
                        if res["file_type"] == "IMAGE" and os.path.exists(res["file_path"]):
                            try:
                                img = Image.open(res["file_path"])
                                st.image(img, caption=f"Thumbnail ({img.width}x{img.height})", use_container_width=True)
                            except Exception:
                                st.caption("Thumbnail unavailable")

                        # Visual Metadata
                        if res.get("visual_metadata"):
                            vm = res["visual_metadata"]
                            st.caption(f"📐 {vm.get('width')}x{vm.get('height')} px | {vm.get('color_mode')}")

                    st.markdown("<hr style='margin: 10px 0; border: 0.5px solid #E5E7EB;'>", unsafe_allow_html=True)
    else:
        st.write("")
        st.markdown("### 💡 Try these sample demonstration queries:")
        q1, q2 = st.columns(2)
        with q1:
            st.info("📄 **Document Queries:**\n- `notes about candidate elimination`\n- `database normalization`\n- `Java concurrency and exceptions`")
        with q2:
            st.info("🖼️ **Multimodal Image Queries:**\n- `red car near a building`\n- `screenshot containing Java error`\n- `photo of a classroom`")
