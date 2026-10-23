import os
import json
import streamlit as st
import pandas as pd
from datetime import datetime

from seekvault.config import APP_NAME, APP_VERSION, SUPPORTED_EXTENSIONS
from seekvault.core.database import init_db, get_dashboard_stats, get_indexed_files, get_db_connection
from seekvault.monitoring.folder_guard import FolderGuard
from seekvault.ingestion.scanner import FolderScanner
from seekvault.ingestion.extractor import extract_file
from seekvault.privacy.classifier import PrivacyClassifier
from seekvault.search.retriever import SemanticSearchEngine
from seekvault.embeddings.faiss_manager import FAISSManager
from seekvault.core.logger import logger

# Initialize Database on app startup
init_db()

# Configure Streamlit Page
st.set_page_config(
    page_title=f"{APP_NAME} - Local Multimodal Semantic Search",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Glassmorphism Theme)
st.markdown("""
<style>
    /* Global Base Styling */
    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
    }
    
    /* Card Styling */
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(8px);
        margin-bottom: 15px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #6366F1;
        margin-top: 5px;
    }
    .metric-label {
        font-size: 0.875rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Search Result Card */
    .result-card {
        background: rgba(30, 41, 59, 0.8);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        transition: transform 0.2s ease;
    }
    .result-card:hover {
        border-color: #6366F1;
        box-shadow: 0 6px 12px rgba(99, 102, 241, 0.2);
    }
    .score-badge {
        background-color: #6366F1;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.85rem;
        float: right;
    }
    
    /* Header Customization */
    .app-header {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        padding: 24px;
        border-radius: 16px;
        margin-bottom: 25px;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to format bytes into human-readable size
def format_size(bytes_size: int) -> str:
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.2f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"

# Helper function to fetch privacy audit logs from SQLite
def get_privacy_audit_logs(limit: int = 100) -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT p.*, f.file_name, f.file_path, f.privacy_tier
            FROM privacy_audit_logs p
            JOIN files f ON p.file_id = f.id
            ORDER BY p.scan_timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

# Sidebar Setup
with st.sidebar:
    st.markdown(f"## 🛡️ {APP_NAME}")
    st.caption(f"Local Semantic Engine v{APP_VERSION}")
    st.markdown("---")
    
    navigation = st.radio(
        "Navigation",
        ["🔍 Semantic Search", "📊 Dashboard", "📂 Authorized Folders", "🔬 Extraction & Files", "🛡️ Privacy & Audit"],
        index=0
    )
    
    st.markdown("---")
    st.markdown("### 🔍 Search Model")
    st.caption("- **Text Embedder**: `SentenceTransformers` (`all-MiniLM-L6-v2`)")
    st.caption("- **Vector Engine**: `FAISS` (`IndexIDMap2`)")
    st.caption("- **Metrics**: Cosine Similarity")
    st.markdown("---")
    st.info("Query-Time Access Guard Enabled.")

# 1. SEMANTIC SEARCH VIEW
if navigation == "🔍 Semantic Search":
    st.markdown('<div class="app-header"><h1>🔍 Multimodal Semantic Search</h1><p>Search across authorized documents and images by contextual meaning</p></div>', unsafe_allow_html=True)
    
    query_input = st.text_input(
        "Enter Natural Language Query",
        placeholder="e.g. Candidate Elimination machine learning notes, red car photo, Java error screenshot..."
    )
    
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 1, 1])
    with ctrl_col1:
        top_k = st.slider("Top Results Count", min_value=1, max_value=25, value=10)
    with ctrl_col2:
        min_score = st.slider("Minimum Match Score (%)", min_value=0, max_value=100, value=20)
    with ctrl_col3:
        type_filter = st.selectbox("Category Filter", ["All", "document", "image"])

    search_btn = st.button("🔎 Run Semantic Search", type="primary", use_container_width=True)
    
    if search_btn or query_input.strip():
        if not query_input.strip():
            st.warning("Please enter a natural language search query.")
        else:
            with st.spinner("Embedding query & searching local FAISS vector index..."):
                search_engine = SemanticSearchEngine()
                results = search_engine.search(query_input.strip(), top_k=top_k)
                
                # Apply filters
                if type_filter != "All":
                    results = [r for r in results if r["file_type"] == type_filter]
                results = [r for r in results if r["similarity_score"] >= min_score]

            st.markdown(f"### 🎯 Search Results ({len(results)} matches)")
            
            if not results:
                st.info("No authorized files matched your query above the score threshold.")
            else:
                for idx, res in enumerate(results, 1):
                    tier_badge = "🟢 FULL" if res["privacy_tier"] == "FULL" else "🟡 REDACTED"
                    
                    st.markdown(f"""
                    <div class="result-card">
                        <span class="score-badge">Match: {res['similarity_score']}%</span>
                        <h3>#{idx} 📄 {res['file_name']}</h3>
                        <p><strong>Path:</strong> <code>{res['file_path']}</code></p>
                        <p><strong>Category:</strong> {res['file_type'].upper()} | <strong>Extension:</strong> {res['file_extension']} | <strong>Size:</strong> {format_size(res['file_size'])} | <strong>Privacy:</strong> {tier_badge}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if res["matched_text"]:
                        st.markdown("**Matched Passage Snippet:**")
                        st.info(res["matched_text"])
                    st.divider()

# 2. DASHBOARD VIEW
elif navigation == "📊 Dashboard":
    st.markdown('<div class="app-header"><h1>📊 SeekVault Dashboard</h1><p>System metrics, vector store size, and privacy tier breakdown</p></div>', unsafe_allow_html=True)
    
    stats = get_dashboard_stats()
    indexed_files = get_indexed_files(limit=1000)
    faiss_mgr = FAISSManager()
    
    tier_counts = {"FULL": 0, "REDACTED": 0, "METADATA_ONLY": 0}
    for f in indexed_files:
        t = f.get("privacy_tier", "FULL")
        tier_counts[t] = tier_counts.get(t, 0) + 1
        
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Authorized Folders</div>
            <div class="metric-value">{stats['total_folders']}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Indexed Files</div>
            <div class="metric-value">{stats['total_files']}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">FAISS Text Vectors</div>
            <div class="metric-value">{faiss_mgr.index.ntotal}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">🟢 FULL / 🟡 RED / 🔴 META</div>
            <div class="metric-value">{tier_counts['FULL']} / {tier_counts['REDACTED']} / {tier_counts['METADATA_ONLY']}</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🛡️ Privacy Tiers Distribution")
        if tier_counts:
            df_tiers = pd.DataFrame(list(tier_counts.items()), columns=["Privacy Tier", "File Count"])
            st.bar_chart(df_tiers.set_index("Privacy Tier"))
        else:
            st.info("No files indexed yet.")
            
    with c2:
        st.subheader("📁 Files by Extension")
        if stats['ext_counts']:
            df_ext = pd.DataFrame(list(stats['ext_counts'].items()), columns=["Extension", "Count"])
            st.dataframe(df_ext, use_container_width=True)
        else:
            st.info("No extensions recorded.")

# 3. AUTHORIZED FOLDERS UI
elif navigation == "📂 Authorized Folders":
    st.markdown('<div class="app-header"><h1>📂 Folder Authorization Manager</h1><p>Manage folder permissions & trigger privacy vector indexing</p></div>', unsafe_allow_html=True)
    
    st.subheader("➕ Add New Authorized Directory")
    with st.form("add_folder_form"):
        folder_input = st.text_input("Local Folder Path", placeholder=r"e.g. C:\Users\hp\Documents\ProjectNotes")
        is_recursive = st.checkbox("Scan subdirectories recursively", value=True)
        submit_btn = st.form_submit_button("Authorize Folder")
        
        if submit_btn:
            if not folder_input.strip():
                st.error("Please enter a valid directory path.")
            else:
                try:
                    added_path = FolderGuard.authorize_folder(folder_input.strip(), is_recursive=is_recursive)
                    st.success(f"Successfully authorized: `{added_path}`")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error authorizing folder: {e}")
                    
    st.markdown("---")
    
    col_hdr, col_btn = st.columns([3, 1])
    with col_hdr:
        st.subheader("Active Authorized Directories")
    with col_btn:
        if st.button("🔄 Scan & Vector Index", type="primary"):
            with st.spinner("Scanning folders, running privacy classifier, and updating FAISS vector store..."):
                res = FolderScanner.scan_all_authorized_folders()
                st.success(f"Scan & Vector Indexing Complete! Scanned: {res['total_scanned']}, Indexed: {res['successful']}, Skipped (Incremental): {res['skipped']}, Failed: {res['failed']}.")
                st.rerun()
                
    from seekvault.core.database import get_authorized_folders
    folder_records = get_authorized_folders(active_only=True)
    
    if not folder_records:
        st.warning("No folders are currently authorized.")
    else:
        for f_rec in folder_records:
            f_col1, f_col2, f_col3 = st.columns([4, 1, 1])
            with f_col1:
                st.markdown(f"**`{f_rec['folder_path']}`**")
                st.caption(f"Added: {f_rec['created_at']} | Recursive: {'Yes' if f_rec['is_recursive'] else 'No'}")
            with f_col2:
                st.write("")
            with f_col3:
                if st.button("❌ Revoke", key=f"revoke_{f_rec['id']}"):
                    FolderGuard.revoke_folder(f_rec['id'])
                    st.success("Folder access revoked.")
                    st.rerun()
            st.divider()

# 4. EXTRACTION INSPECTOR & INDEXED FILES UI
elif navigation == "🔬 Extraction & Files":
    st.markdown('<div class="app-header"><h1>🔬 Extraction & Privacy Registry</h1><p>View detected files, stored representation, and privacy tiers</p></div>', unsafe_allow_html=True)
    
    filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 2])
    with filter_col1:
        type_filter = st.selectbox("Category", ["All", "document", "image"])
    with filter_col2:
        tier_filter = st.selectbox("Privacy Tier", ["All", "FULL", "REDACTED", "METADATA_ONLY"])
    with filter_col3:
        search_query = st.text_input("Filter Filename", placeholder="Type keyword...")
        
    indexed_files = get_indexed_files(limit=500, file_type=type_filter if type_filter != "All" else None)
    
    if tier_filter != "All":
        indexed_files = [f for f in indexed_files if f.get("privacy_tier") == tier_filter]
        
    if search_query.strip():
        q = search_query.strip().lower()
        indexed_files = [f for f in indexed_files if q in f["file_name"].lower()]
        
    if not indexed_files:
        st.info("No files match the active filters.")
    else:
        table_rows = []
        for f in indexed_files:
            table_rows.append({
                "ID": f["id"],
                "File Name": f["file_name"],
                "Ext": f["file_extension"],
                "Type": f["file_type"].upper(),
                "Privacy Tier": f.get("privacy_tier", "FULL"),
                "Extraction Method": f.get("extraction_method", "none"),
                "Size": format_size(f["file_size"]),
                "SHA-256": f["sha256_hash"][:12] + "..." if f["sha256_hash"] else "N/A"
            })
            
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

# 5. PRIVACY AUDIT & SETTINGS UI
elif navigation == "🛡️ Privacy & Audit":
    st.markdown('<div class="app-header"><h1>🛡️ Privacy Audit & Redaction Inspector</h1><p>Inspect entity detection logs, sensitivity scores, and in-memory redactions</p></div>', unsafe_allow_html=True)
    
    logs = get_privacy_audit_logs(limit=100)
    
    st.subheader("📋 Privacy Scan Audit Logs")
    if not logs:
        st.info("No privacy audit entries logged yet.")
    else:
        audit_rows = []
        for log in logs:
            entities = json.loads(log.get("detected_pii_types_json") or "[]")
            entity_summary = ", ".join({e.get("type") for e in entities if e.get("type")}) or "None"
            audit_rows.append({
                "Log ID": log["id"],
                "File Name": log["file_name"],
                "Applied Tier": log["applied_tier"],
                "Sensitivity Score": log["sensitivity_score"],
                "Detected Entities": entity_summary,
                "Scan Timestamp": log["scan_timestamp"]
            })
        st.dataframe(pd.DataFrame(audit_rows), use_container_width=True)
