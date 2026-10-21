import streamlit as st
from pathlib import Path
from seekvault.config import DB_PATH, INDEX_DIR, TEXT_EMBEDDING_MODEL, IMAGE_EMBEDDING_MODEL
from seekvault.extraction.ocr_extractor import OCRExtractor
from seekvault.database.repository import Repository
from seekvault.search.engine import SearchEngine

def render_settings_page(repo: Repository, search_engine: SearchEngine):
    st.header("⚙️ System Settings & Configurations")
    st.markdown("Inspect backend hardware status, neural model configurations, and maintenance tools.")

    # Model Configuration Card
    st.subheader("🤖 Local AI Models")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Text Embedding Model**")
        st.code(f"Model: {TEXT_EMBEDDING_MODEL}\nDimensions: 384\nEngine: Sentence-Transformers (Local CPU)", language="text")
        st.success("🟢 Ready")
    with c2:
        st.markdown("**Cross-Modal Vision Model**")
        st.code(f"Model: {IMAGE_EMBEDDING_MODEL}\nDimensions: 512\nEngine: OpenAI CLIP (Local CPU)", language="text")
        st.success("🟢 Ready")

    # OCR Subsystem Card
    st.subheader("👁️ Optical Character Recognition (OCR)")
    ocr_available = OCRExtractor.is_available()
    if ocr_available:
        st.success("🟢 Tesseract OCR binary detected. Full image text extraction active.")
    else:
        st.warning("🟡 Tesseract OCR binary not detected on system PATH. System operates in graceful fallback mode (visual semantic search active via CLIP).")

    # Storage and Database Status
    st.subheader("💾 Local Storage Architecture")
    st.markdown(f"- **SQLite Database:** `{DB_PATH}`")
    st.markdown(f"- **FAISS Index Directory:** `{INDEX_DIR}`")
    st.markdown(f"- **Text Index Vectors:** `{search_engine.text_index.index.ntotal}`")
    st.markdown(f"- **Image Index Vectors:** `{search_engine.image_index.index.ntotal}`")

    # Maintenance Section
    st.markdown("---")
    st.subheader("⚠️ Maintenance & Reset")
    if st.button("🗑️ Reset All Indices & Database"):
        search_engine.text_index.reset()
        search_engine.image_index.reset()
        st.warning("All FAISS vector indices have been cleared.")
        st.rerun()
