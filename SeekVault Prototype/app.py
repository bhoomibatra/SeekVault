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

# Initialize Session State Singletons
if "repo" not in st.session_state:
    st.session_state.repo = Repository()

if "search_engine" not in st.session_state:
    st.session_state.search_engine = SearchEngine(repository=st.session_state.repo)

if "pipeline" not in st.session_state:
    st.session_state.pipeline = IngestionPipeline(
        repository=st.session_state.repo,
        search_engine=st.session_state.search_engine
    )

if "watcher" not in st.session_state:
    st.session_state.watcher = WatcherManager.get_instance(st.session_state.pipeline)
    st.session_state.watcher.start()

repo = st.session_state.repo
search_engine = st.session_state.search_engine
pipeline = st.session_state.pipeline
watcher = st.session_state.watcher

# Sidebar Navigation
st.sidebar.markdown(
    """
    <div style="padding-bottom: 14px; margin-bottom: 16px; border-bottom: 1px solid #E6E2D8;">
        <div style="display: flex; align-items: center; justify-content: space-between;">
            <span style="font-size: 1.35rem; font-weight: 800; letter-spacing: -0.5px; background: linear-gradient(135deg, #2563EB 0%, #7C3AED 50%, #EC4899 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                SeekVault
            </span>
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; background: linear-gradient(135deg, #EFF6FF, #F5F3FF); color: #4F46E5; border: 1px solid #C7D2FE; padding: 2px 7px; border-radius: 12px;">
                LOCAL v1.0
            </span>
        </div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.70rem; color: #828A98; margin-top: 4px;">
            ZERO-CLOUD PRIVATE INTELLIGENCE
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Navigation Menu — Minimalist editorial labels
nav_choice = st.sidebar.radio(
    "Workspace Navigation",
    [
        "Search",
        "File Library",
        "System Health",
        "Privacy Center",
        "Duplicates & Versions",
        "Settings"
    ],
    index=0,
    label_visibility="collapsed"
)

st.sidebar.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

# Monitoring Status in Sidebar
watcher_status = watcher.get_status()
if watcher_status["is_running"]:
    watch_count = watcher_status['watched_folder_count']
    st.sidebar.markdown(
        f"""
        <div style="padding: 8px 12px; background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #4A5160;">
            <span style="color: #10B981; font-weight: 700;">●</span> Watchdog Active ({watch_count} folders)
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.sidebar.markdown(
        """
        <div style="padding: 8px 12px; background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #828A98;">
            <span style="color: #F59E0B; font-weight: 700;">●</span> Watchdog Idle
        </div>
        """,
        unsafe_allow_html=True
    )

st.sidebar.markdown(
    """
    <div style="margin-top: 8px; padding: 8px 12px; background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #4A5160;">
        <span style="color: #10B981; font-weight: 700;">●</span> Local Zero-Trust Verified
    </div>
    """,
    unsafe_allow_html=True
)

# Page Routing
from seekvault.ui.pages.search import render_search_page
from seekvault.ui.pages.file_library import render_file_library_page
from seekvault.ui.pages.system_health import render_system_health_page
from seekvault.ui.pages.privacy_center import render_privacy_center
from seekvault.ui.pages.duplicates_versions import render_duplicates_versions_page
from seekvault.ui.pages.settings import render_settings_page

if nav_choice in ("Search", "🔍 Search"):
    render_search_page(search_engine)
elif nav_choice in ("File Library", "📁 File Library"):
    render_file_library_page(repo, pipeline, watcher)
elif nav_choice in ("System Health", "📊 System Health"):
    render_system_health_page(repo, search_engine, pipeline, watcher)
elif nav_choice in ("Privacy Center", "🛡️ Privacy Center"):
    render_privacy_center(repo)
elif nav_choice in ("Duplicates & Versions", "👯 Duplicates & Versions"):
    render_duplicates_versions_page(repo)
elif nav_choice in ("Settings", "⚙️ Settings"):
    render_settings_page(repo, search_engine)
