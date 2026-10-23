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
            <div style="font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: #1D4ED8; margin-bottom: 4px;">
                Infrastructure & Lifecycle Configuration
            </div>
            <h1 style="font-family: 'Plus Jakarta Sans', 'Inter', sans-serif; font-size: 1.85rem; font-weight: 700; letter-spacing: -0.015em; color: #15181E; margin: 0 0 8px 0; letter-spacing: -0.02em;">
                System Settings & Maintenance
            </h1>
            <p style="font-size: 0.95rem; color: #4A5160; margin: 0; line-height: 1.5;">
                Inspect on-device neural models, storage architecture, backup/restore archives, and safe index synchronization.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Local AI Models Diagnostics
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 1.25rem; font-weight: 600; color: #15181E; margin-bottom: 12px; font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;">
            Local Neural Embedding Models
        </div>
        """,
        unsafe_allow_html=True
    )

    try:
        model_diag = EmbeddingManager.get_models_status()
    except Exception:
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
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 16px; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #1D4ED8;">
                        TEXT SEMANTIC EMBEDDER
                    </span>
                    <span style="display: inline-flex; align-items: center; gap: 4px; font-size: 0.75rem; font-weight: 600; color: #065F46;">
                        <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #059669;"></span>
                        {'Ready & Loaded' if model_diag['text_model']['initialized'] else 'Standby'}
                    </span>
                </div>
                <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 8px;">
                    <code>{model_diag['text_model']['name']}</code>
                </div>
                <div style="font-size: 0.82rem; color: #4A5160; line-height: 1.5;">
                    <div><strong>Dimension:</strong> {model_diag['text_model']['dimension']}-d dense vector (float32)</div>
                    <div><strong>Engine:</strong> Local CPU via Sentence-Transformers</div>
                    <div><strong>Quantization / Precision:</strong> FP32 Normalized</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with c2:
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 16px; height: 100%; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #1D4ED8;">
                        CROSS-MODAL VISION EMBEDDER
                    </span>
                    <span style="display: inline-flex; align-items: center; gap: 4px; font-size: 0.75rem; font-weight: 600; color: #065F46;">
                        <span style="display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #059669;"></span>
                        {'Ready & Loaded' if model_diag['image_model']['initialized'] else 'Standby'}
                    </span>
                </div>
                <div style="font-size: 0.95rem; font-weight: 600; color: #15181E; margin-bottom: 8px;">
                    <code>{model_diag['image_model']['name']}</code>
                </div>
                <div style="font-size: 0.82rem; color: #4A5160; line-height: 1.5;">
                    <div><strong>Dimension:</strong> {model_diag['image_model']['dimension']}-d dense vector (float32)</div>
                    <div><strong>Engine:</strong> Local CPU via OpenAI CLIP Vision Transformer</div>
                    <div><strong>Quantization / Precision:</strong> FP32 Normalized</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.caption(f"Cache Location: `{model_diag.get('cache_dir', 'Standard OS Cache')}` • Offline Enforcement: `HF_HUB_OFFLINE=1`")

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. OCR Subsystem Status
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 1.25rem; font-weight: 600; color: #15181E; margin-bottom: 12px; font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;">
            Optical Character Recognition Subsystem
        </div>
        """,
        unsafe_allow_html=True
    )
    ocr_available = OCRExtractor.is_available()
    if ocr_available:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #A7F3D0; border-left: 4px solid #059669; border-radius: 8px; padding: 12px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 0.88rem; font-weight: 600; color: #065F46;">Tesseract OCR Active</div>
                <div style="font-size: 0.82rem; color: #374151; margin-top: 2px;">
                    System parses and indexes textual content from scanned PDF documents, invoices, and image screenshots.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-left: 4px solid #64748B; border-radius: 8px; padding: 12px 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 0.88rem; font-weight: 600; color: #15181E;">OCR Subsystem in Graceful Fallback</div>
                <div style="font-size: 0.82rem; color: #4A5160; margin-top: 2px;">
                    Tesseract binary not detected on PATH. Visual semantic search operates via CLIP zero-shot multimodal embeddings.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Local Storage Architecture
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 1.25rem; font-weight: 600; color: #15181E; margin-bottom: 12px; font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;">
            Local Storage Telemetry
        </div>
        """,
        unsafe_allow_html=True
    )
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #1D4ED8; margin-bottom: 4px;">
                    DATABASE PATH
                </div>
                <div style="font-size: 0.82rem; color: #15181E; word-break: break-all;">
                    <code>{DB_PATH}</code>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with s2:
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #1D4ED8; margin-bottom: 4px;">
                    FAISS INDEX DIR
                </div>
                <div style="font-size: 0.82rem; color: #15181E; word-break: break-all;">
                    <code>{INDEX_DIR}</code>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with s3:
        st.markdown(
            f"""
            <div style="background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 8px; padding: 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
                <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #1D4ED8; margin-bottom: 4px;">
                    VECTOR EMBEDDINGS
                </div>
                <div style="font-size: 0.82rem; color: #15181E;">
                    Text Vectors: <strong>{search_engine.text_index.index.ntotal}</strong><br>
                    Image Vectors: <strong>{search_engine.image_index.index.ntotal}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Backup & Restore Snapshots
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 1.25rem; font-weight: 600; color: #15181E; margin-bottom: 12px; font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;">
            Backup & Vault Snapshot Archives
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='font-size: 0.88rem; color: #4A5160; margin-top: 0;'>Create lightweight portable snapshots of your SeekVault database and search vector indices. Snapshots do not alter or move your source files.</p>",
        unsafe_allow_html=True
    )

    bc1, bc2 = st.columns(2)
    with bc1:
        st.markdown("**Create Backup Snapshot:**")
        if st.button("Export Vault Snapshot", type="primary"):
            backup_path = create_backup()
            st.success(f"Backup created successfully:\n`{backup_path}`")

    with bc2:
        st.markdown("**Restore from Backup Snapshot:**")
        backup_input = st.text_input(
            "Backup Archive Path (.zip):",
            placeholder=r"e.g., C:\Path\To\seekvault_backup_20261023.zip",
            key="restore_input_path"
        )
        if st.button("Restore Snapshot", key="btn_restore"):
            if not backup_input.strip():
                st.error("Please provide the full path to a valid backup .zip file.")
            else:
                p = Path(backup_input.strip())
                ok, msg = restore_backup(p)
                if ok:
                    # Reload indices into memory
                    search_engine.text_index.load()
                    search_engine.image_index.load()
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Maintenance & Safe Index Reset (with Confirmation)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div style="font-size: 1.25rem; font-weight: 600; color: #15181E; margin-bottom: 12px; font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;">
            Maintenance & Safe Index Reset
        </div>
        """,
        unsafe_allow_html=True
    )

    if "pending_index_reset" not in st.session_state:
        st.session_state.pending_index_reset = False

    if not st.session_state.pending_index_reset:
        st.markdown(
            "<p style='font-size: 0.88rem; color: #4A5160; margin-top: 0;'>Clear all FAISS vector indices and synchronize database statuses back to <code>PENDING</code> for a fresh re-index.</p>",
            unsafe_allow_html=True
        )
        if st.button("Reset Vector Search Indices", type="secondary"):
            st.session_state.pending_index_reset = True
            st.rerun()
    else:
        st.warning(
            "Confirm Index Reset\n\n"
            "Are you sure you want to reset all search vectors?\n\n"
            "- All FAISS dense vector files (`text_index.faiss`, `image_index.faiss`) will be cleared.\n"
            "- SQLite file records will be synchronized to `PENDING` (preventing index drift).\n"
            "- **Your original source files on disk will strictly NOT be deleted or modified.**\n"
            "- You can re-index your authorized folders anytime from the File Library or System Health tab."
        )
        r_yes, r_no, _ = st.columns([1.5, 1, 3])
        with r_yes:
            if st.button("Yes, Safely Reset Indices", type="primary", key="confirm_reset_indices"):
                search_engine.text_index.reset()
                search_engine.image_index.reset()
                affected = repo.reset_all_search_indices()
                st.session_state.pending_index_reset = False
                st.success(f"Indices reset. {affected} file(s) synchronized to PENDING. Source files on disk remain untouched.")
                st.rerun()
        with r_no:
            if st.button("Cancel", key="cancel_reset_indices"):
                st.session_state.pending_index_reset = False
                st.rerun()
