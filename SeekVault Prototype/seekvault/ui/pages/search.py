import streamlit as st
import os
import re
import time
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


def _get_format_badge(ext: str) -> str:
    """Return styled inline format emblem."""
    ext = (ext or "").lower().replace(".", "")
    if ext in ("pdf",):
        return '<span class="format-badge format-pdf">PDF</span>'
    elif ext in ("docx", "doc"):
        return '<span class="format-badge format-docx">DOCX</span>'
    elif ext in ("txt", "md", "csv", "log", "json"):
        return '<span class="format-badge format-txt">TXT</span>'
    elif ext in ("jpg", "jpeg", "png", "webp", "bmp"):
        return '<span class="format-badge format-img">IMG</span>'
    return f'<span class="format-badge format-txt">{ext.upper() or "FILE"}</span>'


def _format_snippet(text: str, query: str) -> str:
    """Format snippet with query highlighting, supporting existing FTS5 mark tags."""
    if not text:
        return ""
    # If FTS5 already inserted <mark>, preserve it safely
    if "<mark>" in text and "</mark>" in text:
        return text

    # Escape HTML characters first
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Highlight query terms
    terms = [re.escape(w) for w in query.strip().split() if len(w) > 2]
    if terms:
        pattern = re.compile(rf"(?i)\b({'|'.join(terms)})\b")
        safe = pattern.sub(r"<mark>\1</mark>", safe)
    return safe


def render_search_page(search_engine: SearchEngine):
    """Render 'The Private Search Instrument' Search Page."""
    inject_design_system()

    repo = search_engine.repository
    stats = repo.get_dashboard_stats()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. CALM HERO HEADER
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <div style="display: flex; align-items: baseline; justify-content: space-between;">
                <h1 style="font-size: 1.85rem; font-weight: 700; letter-spacing: -0.015em; margin-bottom: 4px; color: #15181E;">
                    Search Documents & Media
                </h1>
                <span style="font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.75rem; color: #697386;">
                    Scope: Local Zero-Trust
                </span>
            </div>
            <p style="font-size: 0.90rem; color: #4A5160; margin-top: 0; margin-bottom: 12px; line-height: 1.5;">
                Search your authorized local files by conceptual meaning, natural language passage, or exact terms.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 2. TRUTHFUL EMPTY INDEX STATE
    # ─────────────────────────────────────────────────────────────────────────
    if stats["total_files"] == 0:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px dashed #D1CBC0; border-radius: 8px; padding: 36px 24px; text-align: center; margin-top: 14px;">
                <div style="font-size: 1.05rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
                    No files are currently indexed in your local vault
                </div>
                <p style="font-size: 0.88rem; color: #4A5160; max-width: 480px; margin: 0 auto 16px auto; line-height: 1.5;">
                    SeekVault only indexes folders you explicitly authorize. To begin searching, open the <strong>File Library</strong> in the navigation and authorize a local folder.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # Check session query pre-population (e.g. from sample chip clicks)
    current_preset = st.session_state.get("search_query_preset", "")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. HERO SEARCH INPUT (PRIMARY INTERACTION)
    # ─────────────────────────────────────────────────────────────────────────
    query = st.text_input(
        "Search your vault:",
        value=current_preset,
        placeholder="Type a concept, question, or term (e.g., 'candidate elimination algorithm', 'database BCNF normalization', 'red car parked')...",
        key="search_hero_input",
        label_visibility="collapsed"
    )

    # Clear preset after applying to input
    if current_preset:
        st.session_state.search_query_preset = ""

    # ─────────────────────────────────────────────────────────────────────────
    # 4. COMPACT INLINE FILTER ROW
    # ─────────────────────────────────────────────────────────────────────────
    col_mode, col_type, col_folder, col_threshold = st.columns([1.6, 1.3, 2.0, 1.1])

    with col_mode:
        search_mode = st.selectbox(
            "Retrieval Mode",
            ["Hybrid (RRF)", "Semantic Only", "Keyword Only"],
            index=0,
            label_visibility="collapsed",
            help="Hybrid merges SQLite FTS5 exact keyword hits with FAISS semantic vectors via Reciprocal Rank Fusion."
        )

    with col_type:
        type_choice = st.selectbox(
            "File Format",
            ["All Formats", "Documents", "Images"],
            index=0,
            label_visibility="collapsed"
        )
        if type_choice == "Documents":
            file_types_filter = ["DOCUMENT"]
        elif type_choice == "Images":
            file_types_filter = ["IMAGE"]
        else:
            file_types_filter = None

    with col_folder:
        auth_folders = repo.get_authorized_folders()
        folder_options = {"All Authorized Folders": None}
        for f in auth_folders:
            folder_name = Path(f["folder_path"]).name or f["folder_path"]
            folder_options[f"Folder: {folder_name}"] = f["id"]

        selected_folder_label = st.selectbox(
            "Folder Scope",
            list(folder_options.keys()),
            index=0,
            label_visibility="collapsed"
        )
        selected_folder_id = folder_options[selected_folder_label]
        folder_filter_ids = [selected_folder_id] if selected_folder_id is not None else None

    with col_threshold:
        min_score = st.slider(
            "Threshold",
            min_value=0.10,
            max_value=0.80,
            value=0.15,
            step=0.05,
            label_visibility="collapsed",
            help="Minimum similarity score threshold (default: 0.15)"
        )

    st.markdown("<hr style='border: none; border-top: 1px solid #E6E2D8; margin: 12px 0 16px 0;' />", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. EXECUTION & RESULTS STREAM
    # ─────────────────────────────────────────────────────────────────────────
    if query and query.strip():
        q_str = query.strip()
        start_t = time.perf_counter()

        try:
            if "Hybrid" in search_mode:
                raw_results = search_engine.search_hybrid(
                    q_str,
                    top_k=20,
                    min_score=min_score,
                    folder_ids=folder_filter_ids,
                    file_types=file_types_filter
                )
            elif "Keyword" in search_mode:
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
                # Semantic Only
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

            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

            # Filter out any lingering unauthorized records
            if folder_filter_ids:
                results = [
                    r for r in raw_results 
                    if repo.get_file_by_id(r["file_id"]) and repo.get_file_by_id(r["file_id"])["folder_id"] in folder_filter_ids
                ]
            else:
                results = raw_results

        except Exception as exc:
            st.error(f"Search query error: {exc}")
            results = []
            elapsed_ms = 0.0

        # Stream Metrics Header
        st.markdown(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.78rem; color: #697386;">
                <div>
                    <span>FOUND <strong style="color: #15181E;">{len(results)}</strong> RELEVANT FILE(S)</span>
                    <span> • </span>
                    <span>{elapsed_ms:.1f}ms (local CPU)</span>
                </div>
                <div>MODE: {search_mode.upper()}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Truthful Empty Results State
        if not results:
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px dashed #D1CBC0; border-radius: 8px; padding: 32px 20px; text-align: center; margin-top: 10px;">
                    <div style="font-size: 1rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
                        No matching documents found for &ldquo;{q_str}&rdquo;
                    </div>
                    <p style="font-size: 0.85rem; color: #4A5160; max-width: 440px; margin: 0 auto; line-height: 1.5;">
                        Try using broader concepts, lowering the threshold slider, or switching to <strong>Hybrid (RRF)</strong> mode to catch exact keywords.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            # Render Genuine Document Cards
            for idx, res in enumerate(results, 1):
                tier_badge = render_tier_badge(res.get("privacy_tier", "FULL"))
                rel_badge = render_relevance_badge(res.get("relevance_label", "Semantic"))
                format_badge = _get_format_badge(res.get("file_extension", ""))

                file_sz = format_file_size(res.get("file_size", 0))
                mod_time = res.get("modified_at", "Unknown")
                file_path = res.get("file_path", "")

                score_val = res.get("similarity_score", 0.0)
                if "Hybrid" in search_mode:
                    score_txt = f"RRF Score: {score_val:.3f}"
                    sem_score = res.get("semantic_score")
                    if sem_score is not None:
                        score_txt += f" | Cosine: {sem_score:.2f}"
                else:
                    score_txt = f"Similarity: {int(score_val * 100)}%"

                raw_snippet = res.get("preview") or ""
                formatted_snippet = _format_snippet(raw_snippet[:500], q_str) if raw_snippet else ""

                with st.container():
                    col_card, col_thumb = st.columns([3.8, 1.2])

                    with col_card:
                        # Top Headline: Format + Name + Badges
                        st.markdown(
                            f"""
                            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    {format_badge}
                                    <span style="font-size: 1rem; font-weight: 600; color: #15181E;">
                                        {res['file_name']}
                                    </span>
                                </div>
                                <div style="display: flex; align-items: center; gap: 6px;">
                                    {rel_badge}
                                    {tier_badge}
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        # Snippet Box
                        if formatted_snippet:
                            if res.get("privacy_tier") == "REDACTED":
                                st.markdown(
                                    "<div style='font-size: 0.72rem; color: #92400E; font-family: \"JetBrains Mono\", monospace; margin-bottom: 2px;'>PROTECTED: Direct PII tokens were sanitized before vector generation</div>",
                                    unsafe_allow_html=True
                                )
                            st.markdown(
                                f"<div class='instrument-snippet'>{formatted_snippet}</div>",
                                unsafe_allow_html=True
                            )

                        # Metadata and File Path (Monospace code for 1-click copy)
                        st.code(file_path, language=None)

                        # Action Row
                        btn_col1, btn_col2, btn_meta = st.columns([1, 1.3, 2.5])
                        with btn_col1:
                            if st.button("👁️ Open", key=f"btn_open_{res['file_id']}_{idx}"):
                                ok, msg = open_file_in_os(file_path)
                                if not ok:
                                    st.warning(msg)
                        with btn_col2:
                            if st.button("📂 Reveal", key=f"btn_reveal_{res['file_id']}_{idx}"):
                                ok, msg = open_folder_in_os(file_path)
                                if not ok:
                                    st.warning(msg)
                        with btn_meta:
                            st.caption(f"{file_sz} • {mod_time} • {score_txt}")

                    with col_thumb:
                        # Real Image Thumbnail
                        if res.get("file_type") == "IMAGE" and os.path.exists(file_path):
                            try:
                                img = Image.open(file_path)
                                st.image(img, caption=f"{img.width}x{img.height}", use_container_width=True)
                            except Exception:
                                st.caption("Thumbnail unavailable")

                    st.markdown("<hr style='border: none; border-top: 1px solid #E6E2D8; margin: 12px 0 16px 0;' />", unsafe_allow_html=True)

    else:
        # ─────────────────────────────────────────────────────────────────────
        # 6. PROMPT STARTER (EMPTY QUERY STATE)
        # ─────────────────────────────────────────────────────────────────────
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px dashed #D1CBC0; border-radius: 8px; padding: 32px 24px; text-align: center; margin-top: 16px;">
                <div style="font-size: 1.05rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
                    Search your local vault by conceptual meaning
                </div>
                <p style="font-size: 0.86rem; color: #4A5160; max-width: 480px; margin: 0 auto 16px auto; line-height: 1.5;">
                    SeekVault indexes full documents and images locally. Click any query starter below to test retrieval against your indexed files:
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            if st.button("Candidate Elimination Algorithm", key="sample_q1", use_container_width=True):
                st.session_state.search_query_preset = "notes about candidate elimination algorithm"
                st.rerun()
        with sc2:
            if st.button("Database Normalization BCNF", key="sample_q2", use_container_width=True):
                st.session_state.search_query_preset = "database relational normalization forms BCNF"
                st.rerun()
        with sc3:
            if st.button("Red Car Parked Outside", key="sample_q3", use_container_width=True):
                st.session_state.search_query_preset = "red car parked near a building"
                st.rerun()

