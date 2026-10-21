import streamlit as st
from pathlib import Path
from typing import Dict, Any

def render_tier_badge(tier: str) -> str:
    """Return colored HTML badge for privacy tiers."""
    colors = {
        "FULL": "#10B981",       # Emerald green
        "REDACTED": "#F59E0B",   # Amber / Orange
        "METADATA_ONLY": "#EF4444" # Red
    }
    color = colors.get(tier, "#6B7280")
    return f"""<span style="background-color: {color}20; color: {color}; border: 1px solid {color}50; padding: 3px 8px; border-radius: 6px; font-weight: 600; font-size: 0.82rem;">{tier}</span>"""

def render_score_bar(score: float) -> str:
    """Render a visual similarity percentage bar."""
    pct = max(0, min(100, int(score * 100)))
    color = "#3B82F6" if pct > 65 else ("#F59E0B" if pct > 45 else "#9CA3AF")
    return f"""
    <div style="background-color: #E5E7EB; border-radius: 4px; height: 8px; width: 100%; margin-top: 4px;">
        <div style="background-color: {color}; width: {pct}%; height: 100%; border-radius: 4px;"></div>
    </div>
    """

def format_file_size(bytes_size: int) -> str:
    """Human readable file sizes."""
    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    else:
        return f"{bytes_size / (1024 * 1024):.2f} MB"
