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
    <div style="text-align: center; margin-bottom: 20px;">
        <h1 style="font-size: 1.8rem; margin-bottom: 0px; color: #F3F4F6;">🛡️ SeekVault</h1>
        <p style="font-size: 0.85rem; color: #9CA3AF; margin-top: 2px;">Local-First Multimodal Search</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Navigation Menu — Search as default landing page, System Health replacing legacy dashboard
nav_choice = st.sidebar.radio(
    "Navigation",
    [
        "🔍 Search",
        "📁 File Library",
        "📊 System Health",
        "🛡️ Privacy Center",
        "👯 Duplicates & Versions",
        "⚙️ Settings"
    ],
    index=0
)

st.sidebar.markdown("---")
# Monitoring Status Pill in Sidebar
watcher_status = watcher.get_status()
if watcher_status["is_running"]:
    st.sidebar.success(f"🟢 Watchdog Active ({watcher_status['watched_folder_count']} folders)")
else:
    st.sidebar.warning("🟡 Watchdog Idle")

st.sidebar.caption("SeekVault v1.0 • 100% Local & Private")

# Page Routing
from seekvault.ui.pages.search import render_search_page
from seekvault.ui.pages.file_library import render_file_library_page
from seekvault.ui.pages.system_health import render_system_health_page
from seekvault.ui.pages.privacy_center import render_privacy_center
from seekvault.ui.pages.duplicates_versions import render_duplicates_versions_page
from seekvault.ui.pages.settings import render_settings_page

if nav_choice == "🔍 Search":
    render_search_page(search_engine)
elif nav_choice == "📁 File Library":
    render_file_library_page(repo, pipeline, watcher)
elif nav_choice == "📊 System Health":
    render_system_health_page(repo, search_engine, pipeline, watcher)
elif nav_choice == "🛡️ Privacy Center":
    render_privacy_center(repo)
elif nav_choice == "👯 Duplicates & Versions":
    render_duplicates_versions_page(repo)
elif nav_choice == "⚙️ Settings":
    render_settings_page(repo, search_engine)
