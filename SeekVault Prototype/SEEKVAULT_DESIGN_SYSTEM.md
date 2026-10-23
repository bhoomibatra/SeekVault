# SeekVault — Frontend Design System & Screen Specifications
**Task:** TASK-02 — Frontend Design System & Visual Preview  
**Date:** 2026-10-23  
**Status:** Ready for User Review & Approval (Gate before implementation)  

---

## 1. Framework Architecture Decision & Trade-offs

### Evaluated Options:
1. **Option A: Pure Custom Desktop (PySide6 / PyQt / Electron)**
   - *Pros:* Complete pixel-level rendering control, native OS window frames.
   - *Cons:* Requires massive new dependencies, C++ binary binding complexities, separate API server / IPC bridge to Python backend, increases packaging footprint by 150MB+, delays shipping core search.
2. **Option B: Retain Python + Streamlit with a Bespoke Design System & CSS Component Injections**
   - *Pros:* Zero new framework dependencies, seamless direct memory access to `Repository`, `SearchEngine`, and `WatcherManager`, fast Windows execution, instant hot-reloading for development, battle-tested with existing 119 automated regression tests.
   - *Cons:* Default Streamlit styles look like an academic dashboard if unstyled.
   - *Resolution:* Inject bespoke CSS design system variables, custom card layouts, polished inputs, and dedicated modal confirmation components while keeping Streamlit as the host engine.

**Recommendation:** Proceed with **Option B** (Enhanced Streamlit Engine with Custom CSS Design System).

---

## 2. Design System Tokens & Specifications

### 2.1 Color Palette (Dark Theme / Obsidian Slate)
| Token | Hex Value | Purpose |
|---|---|---|
| `--bg-base` | `#0B0F17` | Deep obsidian background |
| `--bg-surface` | `#111827` | Primary surface for sidebar, navigation, search bar |
| `--bg-card` | `#182234` | Result cards, table containers, dialogs |
| `--bg-card-hover` | `#1E2B42` | Interactive hover state for cards |
| `--border-subtle` | `#24324D` | Subtle dividers and card outlines |
| `--border-focus` | `#6366F1` | Focus rings and active borders |
| `--accent` | `#6366F1` | Electric Indigo — primary actions and highlights |
| `--accent-hover` | `#4F46E5` | Hover state for primary buttons |
| `--accent-glow` | `rgba(99, 102, 241, 0.25)` | Elevated glow under search bar & cards |
| `--text-primary` | `#F3F4F6` | High-contrast white/light-gray text |
| `--text-secondary` | `#9CA3AF` | Subtitles, path descriptions, metadata |
| `--text-muted` | `#6B7280` | File sizes, helper hints, captions |
| `--success` | `#10B981` | Safe tier, active watchdog, high match scores |
| `--warning` | `#F59E0B` | Redacted PII tier, pending indexing |
| `--danger` | `#EF4444` | Revoke action, reset index, extraction errors |

### 2.2 Typography
- **Primary Interface Font:** `Inter`, `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
  - Headers: 700 weight, -0.02em letter spacing
  - Body: 400 & 500 weight, 1.5line height
- **Code & File Paths:** `JetBrains Mono`, `Consolas`, monospace (12px - 13px)

### 2.3 Spacing, Borders & Radius
- **Border Radius:**
  - Chips & Buttons: `6px` (`--radius-sm`)
  - Cards & Containers: `10px` (`--radius-md`)
  - Search Hero Bar: `14px` (`--radius-lg`)
- **Spacing Scale:** Standard 4px grid (4px, 8px, 12px, 16px, 24px, 32px, 48px)

### 2.4 Accessibility & States
- Minimum contrast ratio > 4.5:1 for all text elements.
- Dedicated interactive states designed:
  - `Default` / `Hover` / `Active` / `Focus-visible`
  - `Empty State` (first run & zero search results)
  - `Loading / Ingestion State` (spinners with real progress)
  - `Error State` (descriptive error banner with retry trigger)
  - `Confirmation Modal State` (prevents destructive actions on single click)

---

## 3. Screen Designs & Navigation Architecture

The navigation is structured across 6 primary functional sections:

```
[SeekVault Shell]
├── 🔍 Search (Default Landing Page)
│    ├── Hero search bar with hybrid keyword + semantic switch
│    ├── Multi-attribute filters (file type, folder, score threshold)
│    ├── Ranked cards with score badges, formatted excerpts, and path metadata
│    └── Direct actions: Open File, Reveal in Explorer, Copy Path
│
├── 📁 My Files (Consolidated Folders + Indexed Files)
│    ├── Authorized folders table with per-folder chunk counts & status
│    ├── Add folder picker with path validation
│    ├── Revoke / deauthorize folder toggle & removal (files remain on disk)
│    └── Safe file inventory table (entity types masked, zero raw PII rendered)
│
├── 📊 Indexing Status (System Health & Telemetry)
│    ├── Background watchdog activity pill & event queue
│    ├── File processing status (INDEXED / FAILED / PENDING)
│    ├── Extraction error log with one-click retry
│    └── FAISS vector / SQLite database consistency telemetry
│
├── 🛡️ Privacy (Privacy Center)
│    ├── 3-tier privacy breakdown: FULL, REDACTED, METADATA_ONLY
│    ├── Entity category audit table (counts and masking strategy)
│    └── Zero raw PII guarantee with sanitized representation previews
│
├── 👥 Duplicates (Duplicates & Versions)
│    ├── Exact SHA-256 duplicate clusters with reclaimable storage counter
│    ├── Side-by-side file reveal actions
│    └── Heuristic version progression chains labeled clearly as suggestions
│
└── ⚙️ Settings (Settings & Maintenance)
     ├── Local directory storage paths
     ├── Model cache verification (HF_HUB_OFFLINE=1)
     ├── Database and FAISS backup / restore action
     └── Factory reset index (safe confirmation dialog + SQLite sync)
```
