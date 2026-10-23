import streamlit as st
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image
from typing import Optional, List, Dict, Any

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
from seekvault.ui.platform import pick_folder_dialog, pick_files_dialog
from seekvault.ui.navigator import get_friendly_folder_name



def _get_format_badge(ext: str) -> str:
    """Return styled inline format badge."""
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
    """Format snippet with query term highlighting."""
    if not text:
        return ""
    if "<mark>" in text and "</mark>" in text:
        return text

    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    terms = [re.escape(w) for w in query.strip().split() if len(w) > 2]
    if terms:
        pattern = re.compile(rf"(?i)\b({'|'.join(terms)})\b")
        safe = pattern.sub(r"<mark>\1</mark>", safe)
    return safe


def render_search_page(search_engine: SearchEngine, pipeline=None, watcher=None):
    """Render the professional Search workspace."""
    inject_design_system()

    repo = search_engine.repository
    stats = repo.get_dashboard_stats()

    if pipeline is None and "pipeline" in st.session_state:
        pipeline = st.session_state.pipeline
    if watcher is None and "watcher" in st.session_state:
        watcher = st.session_state.watcher

    # ─────────────────────────────────────────────────────────────────────────
    # 1. HEADER & TOP ACTIONS
    # ─────────────────────────────────────────────────────────────────────────
    col_header, col_add_file, col_add_folder = st.columns([3.8, 1.1, 1.1])

    with col_header:
        st.markdown(
            """
            <div style="margin-bottom: 14px;">
                <h1 style="font-size: 1.85rem; font-weight: 700; color: #15181E; margin: 0 0 4px 0; letter-spacing: -0.015em;">
                    Search
                </h1>
                <p style="font-size: 0.90rem; color: #4A5160; margin: 0; line-height: 1.4;">
                    Search local documents and media by conceptual meaning, text passage, or filename.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_add_file:
        if st.button("Add Files", key="btn_top_add_files", use_container_width=True):
            st.session_state["show_add_modal"] = "files"

    with col_add_folder:
        if st.button("Add Folder", key="btn_top_add_folder", type="primary", use_container_width=True):
            st.session_state["show_add_modal"] = "folder"

    # Inline Quick Add Panel if triggered
    active_modal = st.session_state.get("show_add_modal")
    if active_modal == "files":
        with st.container():
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 16px; margin-bottom: 14px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 1rem; font-weight: 600; color: #15181E;">Add Individual Files</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #4A5160;">Browse to a folder below and choose specific documents or images to index.</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            from seekvault.ui.navigator import render_file_browser
            chosen_fls = render_file_browser(key_prefix="search_fls_nav")

            c_cancel_top, _ = st.columns([1, 4])
            with c_cancel_top:
                if st.button("Close File Selector", key="btn_close_search_files"):
                    st.session_state["show_add_modal"] = None
                    st.rerun()

            if chosen_fls and pipeline:
                indexed = 0
                prog_bar = st.progress(0)
                for idx, fp in enumerate(chosen_fls):
                    p = Path(fp)
                    prog_bar.progress((idx + 1) / len(chosen_fls))
                    parent_dir = str(p.parent)
                    if not repo.is_path_authorized(str(p)):
                        repo.add_authorized_folder(parent_dir, is_recursive=False)
                    res = pipeline.process_file(str(p))
                    if res and res.get("status") == "INDEXED":
                        indexed += 1
                if watcher:
                    watcher.sync_watches()
                prog_bar.empty()
                st.success(f"Successfully added {indexed} file(s) to your library.")
                st.session_state["show_add_modal"] = None
                st.rerun()

    elif active_modal == "folder":
        with st.container():
            st.markdown(
                """
                <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 16px; margin-bottom: 14px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <span style="font-size: 1rem; font-weight: 600; color: #15181E;">Choose a Folder to Index</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #4A5160;">Select a local folder below to monitor and search its contents.</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            from seekvault.ui.navigator import render_folder_browser, get_friendly_folder_name
            chosen_folder = render_folder_browser(key_prefix="search_fld_nav")

            c_cancel_fld, _ = st.columns([1, 4])
            with c_cancel_fld:
                if st.button("Close Folder Selector", key="btn_close_search_folder"):
                    st.session_state["show_add_modal"] = None
                    st.rerun()

            if chosen_folder and pipeline:
                friendly = get_friendly_folder_name(chosen_folder)
                fid = repo.add_authorized_folder(chosen_folder, is_recursive=True)
                prog_bar = st.progress(0)
                prog_text = st.empty()

                def _prog(idx, total, fname):
                    if total > 0:
                        prog_bar.progress((idx + 1) / total)
                        prog_text.caption(f"Reading {fname}...")

                count = pipeline.scan_folder(chosen_folder, is_recursive=True, progress_callback=_prog)
                if watcher:
                    watcher.sync_watches()
                prog_bar.empty()
                prog_text.empty()
                st.success(f"Successfully added '{friendly}' and indexed {count} file(s).")
                st.session_state["show_add_modal"] = None
                st.rerun()



    # ─────────────────────────────────────────────────────────────────────────
    # 2. EMPTY LIBRARY STATE
    # ─────────────────────────────────────────────────────────────────────────
    if stats["total_files"] == 0:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px dashed #D1CBC0; border-radius: 8px; padding: 40px 24px; text-align: center; margin-top: 14px;">
                <div style="font-size: 1.1rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
                    No files in your library yet
                </div>
                <p style="font-size: 0.88rem; color: #4A5160; max-width: 480px; margin: 0 auto 18px auto; line-height: 1.5;">
                    SeekVault indexes only the folders and files you explicitly authorize on this computer. Select files or an entire folder to begin searching.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    # ─────────────────────────────────────────────────────────────────────────
    # 3. SEARCH INPUT & ACTION
    # ─────────────────────────────────────────────────────────────────────────
    preset_query = st.session_state.get("search_query_preset", "")

    col_input, col_btn = st.columns([4.2, 0.8])
    with col_input:
        query = st.text_input(
            "Search query",
            value=preset_query,
            placeholder="Search files or concepts (e.g. candidate elimination, normalization, receipts)...",
            key="search_main_input",
            label_visibility="collapsed"
        )
    with col_btn:
        search_clicked = st.button("Search", type="primary", use_container_width=True)

    if preset_query:
        st.session_state.search_query_preset = ""

    # ─────────────────────────────────────────────────────────────────────────
    # 4. COMPACT INLINE FILTERS
    # ─────────────────────────────────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([1.5, 2.2, 1.3])

    with fc1:
        type_choice = st.selectbox(
            "File Type",
            ["All Types", "Documents (PDF, DOCX, TXT)", "Images (PNG, JPG)"],
            index=0,
            label_visibility="collapsed"
        )
        if "Documents" in type_choice:
            selected_file_types = ["DOCUMENT"]
        elif "Images" in type_choice:
            selected_file_types = ["IMAGE"]
        else:
            selected_file_types = None

    with fc2:
        auth_folders = repo.get_authorized_folders()
        folder_options = {"All Folders": None}
        for f in auth_folders:
            folder_name = Path(f["folder_path"]).name or f["folder_path"]
            folder_options[f"{folder_name}"] = f["id"]
        selected_folder_label = st.selectbox(
            "Folder",
            list(folder_options.keys()),
            index=0,
            label_visibility="collapsed"
        )
        selected_folder_id = folder_options[selected_folder_label]
        selected_folder_ids = [selected_folder_id] if selected_folder_id else None

    with fc3:
        date_filter = st.selectbox(
            "Date Modified",
            ["Any Time", "Past 7 Days", "Past 30 Days", "Past Year"],
            index=0,
            label_visibility="collapsed"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 5. QUERY EXECUTION & RESULTS PRESENTATION
    # ─────────────────────────────────────────────────────────────────────────
    q_str = query.strip()

    if q_str:
        start_t = time.perf_counter()
        try:
            # Perform hybrid retrieval with active filters
            raw_results = search_engine.search_hybrid(
                query=q_str,
                top_k=30,
                folder_ids=selected_folder_ids,
                file_types=selected_file_types
            )
            elapsed_ms = (time.perf_counter() - start_t) * 1000.0

            # Filter by date if selected
            if date_filter != "Any Time":
                now = datetime.now()
                days = 7 if "7 Days" in date_filter else (30 if "30 Days" in date_filter else 365)
                cutoff = now - timedelta(days=days)
                filtered_results = []
                for r in raw_results:
                    m_str = r.get("modified_at")
                    if m_str:
                        try:
                            dt = datetime.strptime(m_str[:19], "%Y-%m-%d %H:%M:%S")
                            if dt >= cutoff:
                                filtered_results.append(r)
                        except Exception:
                            filtered_results.append(r)
                    else:
                        filtered_results.append(r)
                results = filtered_results
            else:
                results = raw_results

        except Exception as exc:
            st.error(f"Search query error: {exc}")
            results = []
            elapsed_ms = 0.0

        # Result summary count
        st.markdown(
            f"""
            <div style="font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.78rem; color: #697386; margin: 12px 0 16px 0;">
                FOUND <strong style="color: #15181E;">{len(results)}</strong> FILE(S) ({elapsed_ms:.0f}ms)
            </div>
            """,
            unsafe_allow_html=True
        )

        if not results:
            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px dashed #D1CBC0; border-radius: 8px; padding: 32px 20px; text-align: center; margin-top: 10px;">
                    <div style="font-size: 1rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
                        No matching files found for &ldquo;{q_str}&rdquo;
                    </div>
                    <p style="font-size: 0.85rem; color: #4A5160; max-width: 440px; margin: 0 auto; line-height: 1.5;">
                        Try using broader search terms, clearing active filters, or adding more folders to your library.
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            # Clean list of results (no internal algorithmic scores)
            for idx, res in enumerate(results, 1):
                format_badge = _get_format_badge(res.get("file_extension", ""))
                file_sz = format_file_size(res.get("file_size", 0))
                mod_time = res.get("modified_at", "Unknown")
                file_path = res.get("file_path", "")
                raw_snippet = res.get("preview") or ""
                formatted_snippet = _format_snippet(raw_snippet[:450], q_str) if raw_snippet else ""

                with st.container():
                    col_info, col_actions = st.columns([4.0, 1.0])

                    with col_info:
                        # File Name + Format Badge
                        st.markdown(
                            f"""
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                                {format_badge}
                                <span style="font-size: 0.98rem; font-weight: 600; color: #15181E;">
                                    {res['file_name']}
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        # Genuine Passage Excerpt if available
                        if formatted_snippet:
                            st.markdown(
                                f"<div class='instrument-snippet'>{formatted_snippet}</div>",
                                unsafe_allow_html=True
                            )

                        # Location Path and Metadata
                        parent_path = str(Path(file_path).parent)
                        friendly_parent = get_friendly_folder_name(parent_path)
                        st.markdown(
                            f"""
                            <div style="font-size: 0.82rem; color: #4A5160; margin: 4px 0 2px 0;">
                                📁 In <strong>{friendly_parent}</strong> &nbsp;•&nbsp; {file_sz} &nbsp;•&nbsp; Modified {mod_time}
                            </div>
                            <details style="margin: 2px 0 0 0;">
                                <summary style="font-size: 0.75rem; color: #697386; cursor: pointer;">Show file location</summary>
                                <div style="font-family: 'JetBrains Mono', Consolas, monospace; font-size: 0.74rem; color: #4A5160; margin-top: 2px; word-break: break-all;">
                                    {file_path}
                                </div>
                            </details>
                            """,
                            unsafe_allow_html=True
                        )


                    with col_actions:
                        if st.button("Open", key=f"search_open_{res['file_id']}_{idx}", use_container_width=True):
                            ok, msg = open_file_in_os(file_path)
                            if not ok:
                                st.warning(msg)

                        if st.button("Reveal in Explorer", key=f"search_reveal_{res['file_id']}_{idx}", use_container_width=True):
                            ok, msg = open_folder_in_os(file_path)
                            if not ok:
                                st.warning(msg)

                    st.markdown("<hr style='border: none; border-top: 1px solid #E6E2D8; margin: 12px 0 14px 0;' />", unsafe_allow_html=True)

    else:
        # Prompt Starters for initial orientation
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px dashed #D1CBC0; border-radius: 8px; padding: 28px 24px; text-align: center; margin-top: 16px;">
                <div style="font-size: 1rem; font-weight: 600; color: #15181E; margin-bottom: 6px;">
                    Search your library
                </div>
                <p style="font-size: 0.86rem; color: #4A5160; max-width: 460px; margin: 0 auto 14px auto; line-height: 1.5;">
                    Type a query above to search through indexed documents and images, or test search with one of these examples:
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

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
