"""
preview_search_instrument.py — Real, Navigable Streamlit Prototype of "The Private Search Instrument"

This standalone preview module demonstrates the proposed visual reinvention for SeekVault:
  - Warm parchment canvas (#F7F6F2) with deep sumi-ink typography (#15181E).
  - Editorial spacing and clean typographic hierarchy.
  - Stripped-back, emoji-free minimalist navigation rail.
  - Search as the calm, prominent hero interaction.
  - Scannable document cards with real snippet formatting and quick actions.
  - Clearly isolated prototype sample data (zero side-effects on real indices).

To run this preview:
  & "C:\Users\hp\OneDrive\Documents\Saanjh\python_env\python.exe" -m streamlit run "SeekVault Prototype/preview_search_instrument.py"
"""

import sys
from pathlib import Path
import streamlit as st

# Ensure SeekVault package root is on sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Streamlit Page Config
st.set_page_config(
    page_title="SeekVault — The Private Search Instrument (Visual Proposal)",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────────────────
# INJECT PROPOSED DESIGN SYSTEM (Warm Parchment & Editorial Deep Ink)
# ─────────────────────────────────────────────────────────────────────────────
NEW_DESIGN_SYSTEM = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --canvas-bg: #F7F6F2;
        --canvas-subtle: #F0EEE8;
        --surface-card: #FFFFFF;
        --surface-hover: #FCFBF9;
        --border-hairline: #E6E2D8;
        --border-strong: #D1CBC0;
        --border-focus: #1D4ED8;
        --ink-primary: #15181E;
        --ink-secondary: #4A5160;
        --ink-muted: #828A98;
        --cobalt-primary: #1D4ED8;
        --cobalt-tint: #EFF4FE;
        --cobalt-border: #BFDBFE;
    }

    /* Streamlit Global Overrides */
    .stApp {
        background-color: var(--canvas-bg) !important;
        color: var(--ink-primary) !important;
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
    }

    [data-testid="stSidebar"] {
        background-color: #F2EFEB !important;
        border-right: 1px solid var(--border-hairline) !important;
        padding-top: 1.5rem !important;
    }

    /* Prototype Banner */
    .preview-pill {
        display: inline-block;
        background: #1E293B;
        color: #F8FAFC;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        padding: 3px 10px;
        border-radius: 4px;
        margin-bottom: 12px;
    }

    /* Editorial Document Card */
    .instrument-card {
        background: var(--surface-card);
        border: 1px solid var(--border-hairline);
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 14px;
        box-shadow: 0 1px 3px rgba(22, 25, 30, 0.03);
        transition: all 0.15s ease;
    }
    .instrument-card:hover {
        border-color: var(--border-strong);
        box-shadow: 0 6px 20px rgba(22, 25, 30, 0.05);
    }

    .doc-headline {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }

    .format-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.70rem;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: 4px;
        margin-right: 8px;
    }
    .tag-pdf { background: #FEE2E2; color: #991B1B; }
    .tag-docx { background: #DBEAFE; color: #1E40AF; }
    .tag-txt { background: #F3F4F6; color: #374151; }

    .doc-title {
        font-size: 1rem;
        font-weight: 600;
        color: var(--ink-primary);
    }

    .meta-tag {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72rem;
        font-weight: 500;
        padding: 2px 8px;
        border-radius: 4px;
    }
    .tag-hybrid { background: #EFF4FE; color: #1D4ED8; }
    .tag-semantic { background: #FAF5FF; color: #7E22CE; }
    .tag-keyword { background: #ECFEFF; color: #0E7490; }

    .snippet-passage {
        font-size: 0.88rem;
        line-height: 1.55;
        color: var(--ink-secondary);
        background: var(--canvas-subtle);
        border-left: 2px solid var(--border-strong);
        padding: 9px 13px;
        border-radius: 0 6px 6px 0;
        margin: 10px 0;
    }
    .snippet-passage mark {
        background: #FEF08A;
        color: #854D0E;
        padding: 1px 3px;
        border-radius: 2px;
        font-weight: 600;
    }

    .path-row {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: var(--ink-muted);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
</style>
"""
st.markdown(NEW_DESIGN_SYSTEM, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# MINIMAL EDITORIAL SIDEBAR (NO EMOJIS, CLEAN LABELS)
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="padding-bottom: 12px; margin-bottom: 14px; border-bottom: 1px solid #E6E2D8;">
            <div style="font-size: 1.15rem; font-weight: 700; letter-spacing: -0.4px; color: #15181E;">
                SeekVault
            </div>
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.70rem; color: #828A98; margin-top: 2px;">
                LOCAL ENGINE v1.0
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    page = st.radio(
        "Workspace",
        [
            "Search",
            "File Library",
            "Privacy & Storage",
            "System Health",
            "Duplicates & Versions",
            "Settings"
        ],
        index=0,
        label_visibility="collapsed"
    )

    st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="padding: 10px 12px; background: #FFFFFF; border: 1px solid #E6E2D8; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #4A5160;">
            <span style="color: #10B981; font-weight: 700;">●</span> Offline Verified
        </div>
        """,
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────────────────────────────────────
# HERO SEARCH CANVAS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<span class="preview-pill">ISOLATED DESIGN PREVIEW</span>', unsafe_allow_html=True)

col_title, col_info = st.columns([3, 1])
with col_title:
    st.markdown(
        """
        <h1 style="font-size: 1.9rem; font-weight: 700; letter-spacing: -0.6px; margin-bottom: 4px; color: #15181E;">
            Search Documents & Media
        </h1>
        <p style="font-size: 0.90rem; color: #828A98; margin-top: 0; margin-bottom: 16px;">
            Search your local vault by conceptual meaning, natural language, or exact terms.
        </p>
        """,
        unsafe_allow_html=True
    )

with col_info:
    st.caption("Indexed: 14 files across 4 folders")

# Primary Search Hero Bar
query = st.text_input(
    "Query input",
    value="notes about candidate elimination algorithm",
    placeholder="Type a concept or passage (e.g., 'customer churn comparison', 'BCNF normalization', 'red car parked')...",
    label_visibility="collapsed"
)

# Compact Filter Row
c_mode, c_type, c_folder, c_space = st.columns([1.5, 1.2, 1.8, 1.5])
with c_mode:
    search_mode = st.selectbox("Search Mode", ["Hybrid (RRF)", "Semantic Only", "Keyword Only"], index=0, label_visibility="collapsed")
with c_type:
    file_type = st.selectbox("File Type", ["All Formats", "Documents", "Images"], index=0, label_visibility="collapsed")
with c_folder:
    folder_scope = st.selectbox("Scope", ["All Authorized Folders", "academic_notes", "personal_docs", "images"], index=0, label_visibility="collapsed")

st.markdown("<hr style='border: none; border-top: 1px solid #E6E2D8; margin: 16px 0 20px 0;' />", unsafe_allow_html=True)

# Results Header
st.markdown(
    """
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #828A98;">
        <div><span>FOUND 3 RELEVANT PASSAGES</span> • <span>168ms (local CPU)</span></div>
        <div>FUSION: RECIPROCAL RANK FUSION (RRF)</div>
    </div>
    """,
    unsafe_allow_html=True
)

# ─────────────────────────────────────────────────────────────────────────────
# MOCK SAMPLE RESULTS (CLEARLY LABELLED PROTOTYPE DATA)
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_RESULTS = [
    {
        "format": "PDF",
        "tag_class": "tag-pdf",
        "name": "ML_Unit3_Notes.pdf",
        "badge": "Hybrid Match",
        "badge_class": "tag-hybrid",
        "tier": "FULL",
        "snippet": "...The <mark>candidate elimination algorithm</mark> computes the version space containing all hypotheses consistent with the training examples. It iteratively shrinks the general boundary G and expands the specific boundary S...",
        "path": "C:\\Users\\...\\sample_data\\authorized_academic\\ML_Unit3_Notes.pdf",
        "meta": "42.8 KB • Modified Oct 23, 2026",
    },
    {
        "format": "DOCX",
        "tag_class": "tag-docx",
        "name": "DBMS_Lecture_4.docx",
        "badge": "Semantic Match",
        "badge_class": "tag-semantic",
        "tier": "FULL",
        "snippet": "...Discussion of relational database schema design, functional dependencies, and lossless join decomposition into Boyce-Codd Normal Form (BCNF)...",
        "path": "C:\\Users\\...\\sample_data\\authorized_academic\\DBMS_Lecture_4.docx",
        "meta": "34.1 KB • Modified Oct 22, 2026",
    },
    {
        "format": "TXT",
        "tag_class": "tag-txt",
        "name": "Student_Admission_Form.pdf",
        "badge": "Keyword Match",
        "badge_class": "tag-keyword",
        "tier": "REDACTED",
        "snippet": "...Applicant records: Name: John Doe, Email: <mark>&lt;EMAIL_5b821a&gt;</mark>, Phone: <mark>&lt;PHONE_c93140&gt;</mark>. All direct identifiers sanitized before vector generation...",
        "path": "C:\\Users\\...\\sample_data\\authorized_personal\\Student_Admission_Form.pdf",
        "meta": "18.5 KB • Modified Oct 21, 2026",
    }
]

if query.strip():
    for item in SAMPLE_RESULTS:
        st.markdown(
            f"""
            <div class="instrument-card">
                <div class="doc-headline">
                    <div>
                        <span class="format-tag {item['tag_class']}">{item['format']}</span>
                        <span class="doc-title">{item['name']}</span>
                    </div>
                    <div>
                        <span class="meta-tag {item['badge_class']}">{item['badge']}</span>
                    </div>
                </div>
                <div class="snippet-passage">{item['snippet']}</div>
                <div class="path-row">
                    <span><code>{item['path']}</code></span>
                    <span>{item['meta']}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.info("Type a query above to explore documents in your local vault.")
