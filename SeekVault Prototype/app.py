import sys
from pathlib import Path

# Ensure SeekVault package root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import logging
from seekvault.database.repository import Repository
from seekvault.search.engine import SearchEngine
from seekvault.ingestion.pipeline import IngestionPipeline
from seekvault.monitoring.watcher import WatcherManager
from seekvault.ui.components import inject_design_system

# Page setup
st.set_page_config(
    page_title="SeekVault - Privacy-First Multimodal Search",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Obsidian Slate design tokens & styles
inject_design_system()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# Process-level Singleton Services (shared across all tabs & sessions)
@st.cache_resource
def get_seekvault_services():
    """Create and cache SeekVault core services once per Python process.

    This ensures that live file additions handled by WatcherManager immediately
    reflect in the SearchEngine FAISS indices across all browser sessions,
    tabs, and page refreshes.
    """
    repo = Repository()
    search_engine = SearchEngine(repository=repo)
    pipeline = IngestionPipeline(
        repository=repo,
        search_engine=search_engine
    )
    watcher = WatcherManager.get_instance(pipeline)
    watcher.start()
    return repo, search_engine, pipeline, watcher

repo, search_engine, pipeline, watcher = get_seekvault_services()

# Synchronize references into session state for page callbacks
st.session_state.repo = repo
st.session_state.search_engine = search_engine
st.session_state.pipeline = pipeline
st.session_state.watcher = watcher

# Sidebar Navigation
st.sidebar.markdown(
    """
    <div style="padding-bottom: 12px; margin-bottom: 16px; border-bottom: 1px solid #E6E2D8;">
        <div style="font-size: 1.20rem; font-weight: 700; color: #15181E; font-family: 'Plus Jakarta Sans', 'Inter', sans-serif;">
            SeekVault
        </div>
        <div style="font-size: 0.78rem; color: #697386; margin-top: 2px;">
            Local File Search
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Navigation Menu — Exact 6 standard sections
nav_choice = st.sidebar.radio(
    "Navigation",
    [
        "Search",
        "My Files",
        "Indexing Status",
        "Privacy",
        "Duplicates",
        "Settings"
    ],
    index=0,
    label_visibility="collapsed"
)

st.sidebar.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

# Page Routing
from seekvault.ui.pages.search import render_search_page
from seekvault.ui.pages.file_library import render_my_files_page
from seekvault.ui.pages.system_health import render_system_health_page
from seekvault.ui.pages.privacy_center import render_privacy_center
from seekvault.ui.pages.duplicates_versions import render_duplicates_versions_page
from seekvault.ui.pages.settings import render_settings_page

if nav_choice == "Search":
    render_search_page(search_engine, pipeline, watcher)
elif nav_choice in ("My Files", "File Library"):
    render_my_files_page(repo, pipeline, watcher)
elif nav_choice in ("Indexing Status", "System Health"):
    render_system_health_page(repo, search_engine, pipeline, watcher)
elif nav_choice in ("Privacy", "Privacy Center"):
    render_privacy_center(repo)
elif nav_choice in ("Duplicates", "Duplicates & Versions"):
    render_duplicates_versions_page(repo)
elif nav_choice == "Settings":
    render_settings_page(repo, search_engine)
