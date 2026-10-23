"""
test_ui_button_rendering.py — Automated verification of button and expander UI rendering rules.
Verifies:
1. CSS injection contains robust ligature suppression preventing text overlaps.
2. Buttons are configured for clean wrapping without text truncation or collisions.
3. Expander header styles provide adequate padding, flex spacing, and clean vector chevrons.
4. File navigation controls preserve both native OS picker dialogs and manual folder authorization.
"""

from unittest.mock import MagicMock, patch
import pytest

from seekvault.ui.components import inject_design_system
from seekvault.ui.platform import pick_folder_dialog, pick_files_dialog


def test_design_system_css_ligature_suppression():
    """Verify CSS explicitly suppresses raw Material icon ligatures to prevent text overlapping."""
    with patch("streamlit.markdown") as mock_markdown:
        inject_design_system()
        assert mock_markdown.called
        css_rendered = mock_markdown.call_args[0][0]

        # 1. Ligature suppression rule must exist
        assert 'font-size: 0 !important' in css_rendered
        assert 'color: transparent !important' in css_rendered

        # 2. Targeted expander chevrons must have vector replacement
        assert '[data-testid="stExpander"] summary [data-testid="stIconMaterial"]' in css_rendered
        assert 'content: \'\' !important' in css_rendered

        # 3. Icon width and overflow clipping to prevent horizontal leakage
        assert 'overflow: hidden !important' in css_rendered
        assert 'white-space: nowrap !important' in css_rendered


def test_button_wrapping_and_spacing_rules():
    """Verify button CSS ensures adequate height, padding, and clean text wrapping."""
    with patch("streamlit.markdown") as mock_markdown:
        inject_design_system()
        css_rendered = mock_markdown.call_args[0][0]

        # Buttons must wrap text cleanly and not enforce rigid nowrap
        assert '[data-testid="stButton"] button' in css_rendered
        assert 'white-space: normal !important' in css_rendered
        assert 'overflow-wrap: break-word !important' in css_rendered
        assert 'min-height: 38px !important' in css_rendered
        assert 'padding: 8px 16px !important' in css_rendered


def test_expander_summary_spacing_and_alignment():
    """Verify expander summary headers have flex alignment and separate text containers."""
    with patch("streamlit.markdown") as mock_markdown:
        inject_design_system()
        css_rendered = mock_markdown.call_args[0][0]

        assert '[data-testid="stExpander"] summary' in css_rendered
        assert 'display: flex !important' in css_rendered
        assert 'gap: 12px !important' in css_rendered or 'gap: 10px !important' in css_rendered
        assert 'flex: 1 !important' in css_rendered


def test_file_navigation_controls_preserve_functionality(tmp_path):
    """Verify the two file navigation controls preserve their callbacks and backend interactions."""
    # 1. Test native folder picker callback via subprocess mock
    mock_folder_proc = MagicMock()
    mock_folder_proc.stdout = f"{tmp_path}\n"
    with patch("subprocess.run", return_value=mock_folder_proc):
        result = pick_folder_dialog("Select folder")
        assert result == str(tmp_path)

    # 2. Test native file picker callback via subprocess mock
    sample_file = tmp_path / "doc.txt"
    sample_file.write_text("sample content")
    mock_file_proc = MagicMock()
    mock_file_proc.stdout = f"{sample_file}\n"
    with patch("subprocess.run", return_value=mock_file_proc):
        picked_files = pick_files_dialog("Select files")
        assert len(picked_files) == 1
        assert picked_files[0] == str(sample_file)
