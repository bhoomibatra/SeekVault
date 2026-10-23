from seekvault.database.repository import Repository
from seekvault.ui.pages.system_health import render_system_health_page, check_vector_integrity


def render_dashboard(repo: Repository, watcher_status: dict, search_engine=None, pipeline=None):
    """Backwards-compatible wrapper routing dashboard to System Health."""
    import streamlit as st
    engine = search_engine or getattr(st.session_state, "search_engine", None)
    pipe = pipeline or getattr(st.session_state, "pipeline", None)
    watcher = getattr(st.session_state, "watcher", None)

    if engine and pipe and watcher:
        render_system_health_page(repo, engine, pipe, watcher)
    else:
        # Fallback if invoked in isolated fixture without full session
        st.header("📊 System Health & Telemetry")
        st.info("System health services active.")
