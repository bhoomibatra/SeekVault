import streamlit as st
import os
from pathlib import Path
from PIL import Image
from seekvault.search.engine import SearchEngine
from seekvault.ui.components import (
    render_tier_badge,
    render_relevance_badge,
    render_score_bar,
    format_file_size,
    open_file_in_os,
    open_folder_in_os,
    inject_design_system,
)


def render_search_page(search_engine: SearchEngine):
    inject_design_system()

    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="font-size: 2.2rem; font-weight: 700; margin-bottom: 6px; color: #F3F4F6;">
                🔍 SeekVault Search
            </h1>
            <p style="font-size: 0.95rem; color: #9CA3AF; margin-top: 0;">
                Privacy-first multimodal search across authorized local documents and images.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    repo = search_engine.repository
    stats = repo.get_dashboard_stats()

    if stats["total_files"] == 0:
        st.info(
            "📂 **No files are currently indexed.** To begin searching, please authorize a folder containing your documents or images in the **📁 Authorized Folders** tab."
        )
        return

    # ─────────────────────────────────────────────────────────────────────────
    # Primary Search Bar (Visual Focus)
    # ─────────────────────────────────────────────────────────────────────────
    query = st.text_input(
        "Search your local vault:",
        placeholder="Type a concept, phrase, or keyword (e.g., 'candidate elimination', 'quarterly report', 'red car parked outside', 'Java exception')...",
        key="search_query_input",
        label_visibility="collapsed"
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Controls & Filter Row
    # ─────────────────────────────────────────────────────────────────────────
    with st.expander("⚙️ Search Controls & Filters", expanded=True):
        c1, c2, c3, c4 = st.columns([1.8, 1.6, 1.4, 1.2])

        with c1:
            search_mode = st.selectbox(
                "Search Mode",
                ["⚡ Hybrid (Recommended)", "🧠 Semantic Only", "🔤 Keyword Only"],
                index=0,
                help="Hybrid merges SQLite FTS5 exact keyword hits with FAISS semantic vectors via Reciprocal Rank Fusion."
            )

        with c2:
            # Dynamic authorized folders list
            auth_folders = repo.get_authorized_folders()
            folder_options = {"All Authorized Folders": None}
            for f in auth_folders:
                folder_name = Path(f["folder_path"]).name or f["folder_path"]
                folder_options[f"📁 {folder_name}"] = f["id"]

            selected_folder_label = st.selectbox(
                "Filter by Folder",
                list(folder_options.keys()),
                index=0
            )
            selected_folder_id = folder_options[selected_folder_label]
            folder_filter_ids = [selected_folder_id] if selected_folder_id is not None else None

        with c3:
            type_choice = st.selectbox(
                "File Type",
                ["All File Types", "Documents Only", "Images Only"],
                index=0
            )
            if type_choice == "Documents Only":
                file_types_filter = ["DOCUMENT"]
            elif type_choice == "Images Only":
                file_types_filter = ["IMAGE"]
            else:
                file_types_filter = None

        with c4:
            min_score = st.slider(
                "Min Score Threshold",
                min_value=0.10,
                max_value=0.85,
                value=0.20,
                step=0.05,
                help="Minimum cosine similarity for semantic candidate matches."
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Execution & Result Rendering
    # ─────────────────────────────────────────────────────────────────────────
    if query and query.strip():
        q_str = query.strip()
        with st.spinner("Searching vault & verifying access boundaries..."):
            if "Hybrid" in search_mode:
                # Hybrid FTS5 + Semantic
                raw_results = search_engine.search_hybrid(
                    q_str,
                    top_k=20,
                    min_score=min_score,
                    folder_ids=folder_filter_ids,
                    file_types=file_types_filter
                )
            elif "Keyword" in search_mode:
                # FTS5 Keyword only
                fts_rows = repo.fts_search_content(
                    q_str,
                    top_k=20,
                    folder_ids=folder_filter_ids,
                    file_types=file_types_filter
                )
                raw_results = []
                for row in fts_rows:
                    f_rec = repo.get_file_by_id(row["file_id"])
                    if f_rec and repo.is_path_authorized(f_rec["file_path"]):
                        enriched = search_engine._enrich_result(
                            f_rec,
                            score=1.0,
                            excerpt=row.get("excerpt", ""),
                            relevance_label="Keyword"
                        )
                        raw_results.append(enriched)
            else:
                # Semantic only
                if file_types_filter == ["IMAGE"]:
                    raw_results = search_engine.search_images(q_str, top_k=20, min_score=min_score)
                    if folder_filter_ids:
                        raw_results = [r for r in raw_results if r.get("folder_id") in folder_filter_ids]
                else:
                    raw_results = search_engine.search_text_filtered(
                        q_str,
                        top_k=20,
                        min_score=min_score,
                        folder_ids=folder_filter_ids,
                        file_types=file_types_filter
                    )
                    for r in raw_results:
                        r["relevance_label"] = "Semantic"

        # Apply client-side folder filter if semantic didn't catch images
        if folder_filter_ids:
            results = [r for r in raw_results if repo.get_file_by_id(r["file_id"]) and repo.get_file_by_id(r["file_id"])["folder_id"] in folder_filter_ids]
        else:
            results = raw_results

        # Summary Header
        st.markdown(
            f"<div style='margin: 16px 0 12px 0; color: #9CA3AF; font-size: 0.95rem;'>"
            f"Found <strong style='color: #F3F4F6;'>{len(results)}</strong> matching file(s) for query "
            f"<em style='color: #6366F1;'>&ldquo;{q_str}&rdquo;</em></div>",
            unsafe_allow_html=True
        )

        if not results:
            st.warning(
                f"No results found matching '{q_str}' with current filters. Try lowering the similarity threshold or switching to Keyword search."
            )
        else:
            for idx, res in enumerate(results, 1):
                tier_html = render_tier_badge(res.get("privacy_tier", "FULL"))
                rel_html = render_relevance_badge(res.get("relevance_label", "Semantic"))
                sim_score = res.get("similarity_score", 0.0)
                sem_score = res.get("semantic_score")

                with st.container():
                    col_info, col_visual = st.columns([3.5, 1.2])

                    with col_info:
                        # Card Title and Attribution
                        score_label = f"Match Score: {sim_score:.3f}" if "Hybrid" in search_mode else f"Similarity: {int(sim_score * 100)}%"
                        if sem_score is not None and "Hybrid" in search_mode:
                            score_label += f" | Cosine: {sem_score:.2f}"

                        st.markdown(
                            f"### {idx}. {res['file_name']} &nbsp; {tier_html} &nbsp; {rel_html} "
                            f"<span style='font-size:0.85rem; color:#9CA3AF; margin-left:8px;'>({score_label})</span>",
                            unsafe_allow_html=True
                        )

                        if "Hybrid" not in search_mode:
                            st.markdown(render_score_bar(sim_score), unsafe_allow_html=True)

                        # File Metadata details
                        file_ext = res.get("file_extension", "").upper()
                        file_sz = format_file_size(res.get("file_size", 0))
                        mod_time = res.get("modified_at", "Unknown")
                        st.caption(f"📁 **Type:** {file_ext} | **Size:** {file_sz} | **Modified:** {mod_time}")

                        # Content Excerpt Preview
                        preview_text = res.get("preview") or ""
                        if preview_text:
                            if res.get("privacy_tier") == "REDACTED":
                                st.markdown("<span style='font-size:0.8rem; color:#F59E0B;'>🛡️ Privacy Protected: Sensitive PII was redacted from index.</span>", unsafe_allow_html=True)
                            
                            # Clean snippet container
                            snippet_preview = preview_text[:600] + ("..." if len(preview_text) > 600 else "")
                            st.markdown(
                                f"<div class='seekvault-snippet-box'>{snippet_preview}</div>",
                                unsafe_allow_html=True
                            )

                        # Detected PII Tokens Notice
                        if res.get("entities"):
                            ent_types = sorted(list(set(e.get("entity_type", "") for e in res["entities"] if e.get("entity_type"))))
                            if ent_types:
                                st.caption(f"🛡️ **Detected PII Categories:** {', '.join(ent_types)}")

                        # Monospace Path with Copy Support
                        st.code(res["file_path"], language=None)

                        # OS Shell Action Buttons
                        btn_col1, btn_col2, _ = st.columns([1, 1.3, 2.5])
                        with btn_col1:
                            if st.button("👁️ Open File", key=f"btn_open_{res['file_id']}_{idx}"):
                                ok, msg = open_file_in_os(res["file_path"])
                                if not ok:
                                    st.warning(msg)
                        with btn_col2:
                            if st.button("📂 Reveal in Folder", key=f"btn_reveal_{res['file_id']}_{idx}"):
                                ok, msg = open_folder_in_os(res["file_path"])
                                if not ok:
                                    st.warning(msg)

                    with col_visual:
                        # Image Thumbnail display
                        if res.get("file_type") == "IMAGE" and os.path.exists(res["file_path"]):
                            try:
                                img = Image.open(res["file_path"])
                                st.image(img, caption=f"{img.width}x{img.height} ({img.format})", use_container_width=True)
                            except Exception:
                                st.caption("Thumbnail unavailable")

                    st.markdown("<hr style='margin: 14px 0; border: 0.5px solid #24324D;'>", unsafe_allow_html=True)

    else:
        # Initial empty state with example queries
        st.markdown(
            """
            <div style="background-color: #111827; border: 1px solid #24324D; border-radius: 10px; padding: 24px; margin-top: 16px;">
                <h3 style="color: #F3F4F6; margin-top: 0;">💡 Quick Query Suggestions</h3>
                <p style="color: #9CA3AF; font-size: 0.9rem;">
                    SeekVault indexes concept meaning, exact keywords, and visual contents. Try searching for:
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        ec1, ec2 = st.columns(2)
        with ec1:
            st.info(
                "📄 **Document Queries:**\n"
                "- `candidate elimination algorithm version space`\n"
                "- `database normalization BCNF decomposition`\n"
                "- `quantum key distribution protocol`\n"
                "- `confidential project report draft`"
            )
        with ec2:
            st.info(
                "🖼️ **Multimodal Visual Queries:**\n"
                "- `red car parked outside a building`\n"
                "- `screenshot showing Java terminal error`\n"
                "- `classroom lecture blackboard notes`\n"
                "- `architectural floor plan diagram`"
            )
