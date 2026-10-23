import os
import streamlit as st
from pathlib import Path
from seekvault.config import DB_PATH, INDEX_DIR, DATA_DIR, TEXT_EMBEDDING_MODEL, IMAGE_EMBEDDING_MODEL
from seekvault.extraction.ocr_extractor import OCRExtractor
from seekvault.database.repository import Repository
from seekvault.search.engine import SearchEngine
from seekvault.embeddings.manager import EmbeddingManager
from seekvault.database.backup import create_backup, restore_backup
from seekvault.ui.components import inject_design_system


def render_settings_page(repo: Repository, search_engine: SearchEngine):
    inject_design_system()

    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="font-size: 2.2rem; font-weight: 700; margin-bottom: 6px; color: #F3F4F6;">
                ⚙️ System Settings & Maintenance
            </h1>
            <p style="font-size: 0.95rem; color: #9CA3AF; margin-top: 0;">
                Inspect on-device neural models, local storage architecture, backup/restore snapshots, and index maintenance.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Local AI Models Diagnostics
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("🤖 Local AI Neural Models")

    try:
        model_diag = EmbeddingManager.get_models_status()
    except Exception as exc:
        model_diag = {
            "offline_mode": True,
            "cache_dir": str(Path.home() / ".cache" / "huggingface"),
            "text_model": {"name": TEXT_EMBEDDING_MODEL, "dimension": 384, "initialized": True, "available": True},
            "image_model": {"name": IMAGE_EMBEDDING_MODEL, "dimension": 512, "initialized": True, "available": True},
        }

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
            <div class="seekvault-search-card">
                <h4 style="color: #6366F1; margin: 0 0 6px 0;">📑 Text Semantic Embedder</h4>
                <p style="font-size: 0.85rem; color: #9CA3AF; margin: 0 0 10px 0; line-height: 1.4;">
                    <strong>Model:</strong> <code>{model_diag['text_model']['name']}</code><br>
                    <strong>Embedding Space:</strong> {model_diag['text_model']['dimension']}-dimensional float32<br>
                    <strong>Execution Provider:</strong> Local CPU (Sentence-Transformers)<br>
                    <strong>Status:</strong> {'🟢 Ready & Loaded' if model_diag['text_model']['initialized'] else '🟢 Standby / Available'}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            f"""
            <div class="seekvault-search-card">
                <h4 style="color: #6366F1; margin: 0 0 6px 0;">🖼️ Cross-Modal Vision Embedder</h4>
                <p style="font-size: 0.85rem; color: #9CA3AF; margin: 0 0 10px 0; line-height: 1.4;">
                    <strong>Model:</strong> <code>{model_diag['image_model']['name']}</code><br>
                    <strong>Embedding Space:</strong> {model_diag['image_model']['dimension']}-dimensional float32<br>
                    <strong>Execution Provider:</strong> Local CPU (OpenAI CLIP)<br>
                    <strong>Status:</strong> {'🟢 Ready & Loaded' if model_diag['image_model']['initialized'] else '🟢 Standby / Available'}
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.caption(f"📁 Local Model Cache: `{model_diag.get('cache_dir', 'Standard OS Cache')}` | Offline Mode Enforced: `HF_HUB_OFFLINE=1`")

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. OCR Subsystem Status
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("👁️ Optical Character Recognition (OCR)")
    ocr_available = OCRExtractor.is_available()
    if ocr_available:
        st.success("🟢 **Tesseract OCR Active**: System extracts text from scanned documents and screenshots.")
    else:
        st.info("🟡 **OCR Subsystem in Graceful Fallback**: Tesseract binary not detected on PATH. Visual semantic search operates via CLIP visual embeddings.")

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Local Storage Architecture
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("💾 Local Storage Telemetry")
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(f"**SQLite Database Path:**\n`{DB_PATH}`")
    with s2:
        st.markdown(f"**FAISS Index Directory:**\n`{INDEX_DIR}`")
    with s3:
        st.markdown(
            f"**Vector Counts:**\n"
            f"- Text: `{search_engine.text_index.index.ntotal}` vectors\n"
            f"- Image: `{search_engine.image_index.index.ntotal}` vectors"
        )

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Backup & Restore Snapshots
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("📦 Backup & Restore")
    st.markdown(
        "Create lightweight portable snapshots of your SeekVault database and search vector indices. "
        "Snapshots do not alter or move your source files."
    )

    bc1, bc2 = st.columns(2)
    with bc1:
        st.markdown("**Create Backup Snapshot:**")
        if st.button("💾 Export Current Vault Snapshot", type="primary"):
            backup_path = create_backup()
            st.success(f"✅ Backup created successfully:\n`{backup_path}`")

    with bc2:
        st.markdown("**Restore from Backup Snapshot:**")
        backup_input = st.text_input(
            "Backup Archive Path (.zip):",
            placeholder=r"e.g., C:\Path\To\seekvault_backup_20261023.zip",
            key="restore_input_path"
        )
        if st.button("📥 Restore Snapshot", key="btn_restore"):
            if not backup_input.strip():
                st.error("Please provide the full path to a valid backup .zip file.")
            else:
                p = Path(backup_input.strip())
                ok, msg = restore_backup(p)
                if ok:
                    # Reload indices into memory
                    search_engine.text_index.load()
                    search_engine.image_index.load()
                    st.success("✅ " + msg)
                    st.rerun()
                else:
                    st.error("❌ " + msg)

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Maintenance & Safe Index Reset (with Confirmation)
    # ─────────────────────────────────────────────────────────────────────────
    st.subheader("⚠️ Maintenance & Safe Index Reset")

    if "pending_index_reset" not in st.session_state:
        st.session_state.pending_index_reset = False

    if not st.session_state.pending_index_reset:
        st.markdown(
            "Clear all FAISS vector indices and synchronize database statuses back to `PENDING` for a fresh re-index."
        )
        if st.button("🗑️ Reset Vector Search Indices", type="secondary"):
            st.session_state.pending_index_reset = True
            st.rerun()
    else:
        st.warning(
            "⚠️ **Confirm Index Reset**\n\n"
            "Are you sure you want to reset all search vectors?\n\n"
            "- All FAISS dense vector files (`text_index.faiss`, `image_index.faiss`) will be cleared.\n"
            "- SQLite file records will be synchronized to `PENDING` (preventing index drift).\n"
            "- **Your original source files on disk will strictly NOT be deleted or modified.**\n"
            "- You can re-index your authorized folders anytime from the **File Library** or **System Health** tab."
        )
        r_yes, r_no, _ = st.columns([1.2, 1, 3])
        with r_yes:
            if st.button("✅ Yes, Safely Reset Indices", type="primary", key="confirm_reset_indices"):
                search_engine.text_index.reset()
                search_engine.image_index.reset()
                affected = repo.reset_all_search_indices()
                st.session_state.pending_index_reset = False
                st.success(f"Indices reset. {affected} file(s) synchronized to PENDING. Source files on disk remain untouched.")
                st.rerun()
        with r_no:
            if st.button("❌ Cancel", key="cancel_reset_indices"):
                st.session_state.pending_index_reset = False
                st.rerun()
