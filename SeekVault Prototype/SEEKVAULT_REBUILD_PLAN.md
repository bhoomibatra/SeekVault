# SeekVault — Rebuild Plan & Requirements-to-Test Matrix
**Task:** TASK-01 — UI Audit + Requirement Mapping
**Date:** 2026-10-23
**Status:** Complete — awaiting CONTINUE for TASK-02

---

## 1. Current UI — Page-by-Page Audit

### Navigation & Shell (app.py)
- CRITICAL: Dashboard is the default landing page — spec requires Search as default
- Sidebar uses plain st.radio() with no real design system
- "100% Local & Private" caption is inaccurate until HF_HUB_OFFLINE=1 is set (network ping confirmed)
- No keyboard shortcuts or accessible nav labels

### Page 1 — Dashboard (dashboard.py) → REPLACE with Activity & Insights
- 5 KPI metric boxes — generic admin template look
- Bar chart of privacy tiers — decorative, not actionable
- "Detected PII Entities" metric not useful to end users
- First-run onboarding exists but buried below KPI row

### Page 2 — Search (search.py) → MAJOR REDESIGN, logic retained
- st.text_input() with no visual prominence — search field is not the visual focus
- No filter by authorized folder (spec requires this)
- No filter by modified date
- Semantic-only search — no keyword/FTS fallback for exact queries
- Score shown as float (0.312) — not user-friendly
- No "Copy path" action
- Thumbnail and Open/Open Folder buttons are good — retain

### Page 3 — Authorized Folders (folders.py) → REDESIGN
- CRITICAL: Remove button fires with NO confirmation dialog
- Developer fixture buttons visible in production (Academic Notes, PII Forms)
- No explanation that removing folder does NOT delete source files
- No per-folder indexed file count

### Page 4 — Indexed Files (indexed_files.py) → MERGE INTO File Library
- CRITICAL: entity_text column shows raw PII values (phone numbers, emails) in UI
- Raw st.dataframe() with developer-facing ID column
- No indexing status column (INDEXED/FAILED/PENDING)
- No sort controls

### Page 5 — Privacy Center (privacy_center.py) → REDESIGN
- CRITICAL: entity_text shows raw PII values in the entity audit table
- CRITICAL: "Zero Cloud Transmission" hardcoded as guaranteed — inaccurate
- No way to clear/export SeekVault's own index data from this page
- Tier explanation cards are good — retain concept

### Page 6 — Duplicates & Versions (duplicates_versions.py) → LIGHT REDESIGN
- Version detection not labelled clearly as suggestions/heuristic
- No "Dismiss incorrect match" for versions
- Reclaimable space metric, SHA-256 detection, Open/Folder buttons all good — retain

### Page 7 — Settings (settings.py) → CRITICAL FIX + EXPAND
- CRITICAL: Reset button fires on single click — no confirmation
- CRITICAL: Reset only clears FAISS, not SQLite status — causes drift
- Models show Green Ready hardcoded — not from actual init state
- No backup/restore, no diagnostics panel

---

## 2. Requirements to UI Screen to Backend Module to Test Matrix

| Req | Requirement | UI Page | Backend | Test Coverage | Gap |
|-----|-------------|---------|---------|---------------|-----|
| R-01 | Search as default landing | Page A Search | engine.py | test_semantic_text_search | Navigation order |
| R-02 | Semantic search | Page A | engine.py + embeddings | test_semantic_text_search | Covered |
| R-03 | Filter by file type | Page A | repository.py | None | Add filter |
| R-04 | Filter by authorized folder | Page A | repository.py | None | New backend param |
| R-05 | Filter by date | Page A | repository.py | None | Add filter |
| R-06 | Real excerpts | Page A | engine.py preview field | test_semantic_text_search | Verify fidelity |
| R-07 | Open File / Reveal | Page A,B,E | components.py | Manual only | Manual Windows test |
| R-08 | Copy path | Page A | UI only | None | Add button |
| R-09 | Hybrid keyword+semantic | Page A | engine.py + FTS5 | None | NEW FEATURE |
| R-10 | Folder authorization | Page B | repository.py | test_folder_authorization | Covered |
| R-11 | Revoke with confirmation | Page B | repository.py | test_query_time_deauthorization_suppression | Add confirm dialog |
| R-12 | Revoke != delete files | Page B | pipeline.py | test_original_file_immutability | Covered + UI note |
| R-13 | Per-file indexing state | Page B | repository.py | None | Expose status column |
| R-14 | Privacy tier explanation | Page C | Static UI | test_classification_tiers | Covered |
| R-15 | No unverified local-only claim | Page C | config.py | None | FIX: HF_HUB_OFFLINE=1 |
| R-16 | Hide raw PII from UI | Page C,B | repository.py | test_pii_sanitization_zero_leakage | FIX: redact entity_text |
| R-17 | Safe index clearing | Page C,G | faiss_index.py + repository | None | Add confirm + SQLite sync |
| R-18 | Real indexing progress | Page D | pipeline.py | None | Add status tracking |
| R-19 | Failed file details + retry | Page D | repository.py | None | Add FAILED status + retry |
| R-20 | DB/index consistency check | Page D | faiss_index.py | test_automatic_vector_integrity_healing | Expose in UI |
| R-21 | Safe index repair | Page D | pipeline.py | None | UI-triggered rebuild |
| R-22 | Exact duplicate detection | Page E | duplicate_detector.py | test_duplicate_hashing_and_detection | Covered |
| R-23 | Versions labelled as suggestions | Page E | version_detector.py | test_version_stem_extraction | Wording fix |
| R-24 | No auto-delete files | Page E | All | test_original_file_immutability | Covered |
| R-25 | Genuine stats only | Page F | repository.py | None | Replace Dashboard |
| R-26 | Model config + cache info | Page G | config.py | None | Add model info panel |
| R-27 | Backup/restore | Page G | New utility | None | New feature |
| R-28 | Settings reset with confirmation + sync | Page G | faiss_index.py + repository | None | CRITICAL FIX |

---

## 3. New Navigation Order

Current (wrong): Dashboard > Search > Folders > Indexed Files > Privacy > Duplicates > Settings

New (spec-aligned):
  Search         ← default landing page
  File Library   ← merges Folders + Indexed Files
  Privacy        ← Privacy & Security
  System Health  ← replaces Dashboard with real indexing status
  Duplicates     ← Duplicates & Versions
  Insights       ← Activity & Insights (replaces KPI Dashboard)
  Settings

---

## 4. Critical Bugs (must fix)

F-1: Add HF_HUB_OFFLINE=1 + TRANSFORMERS_OFFLINE=1 to config.py
F-2: Settings reset — add confirmation dialog
F-3: Settings reset — sync SQLite status field to PENDING
F-4: Folder Remove — add confirmation dialog
F-5: Indexed Files + Privacy Center — never render raw entity_text values

---

## 5. New Features Required by Spec

N-1: Hybrid keyword (SQLite FTS5) + semantic search
N-2: Per-file indexing status in UI (PENDING/INDEXED/FAILED)
N-3: Backup/restore for data_storage/
N-4: System Health page with real job status
N-5: Copy path action in search results
N-6: Filter by folder in search
N-7: Dismiss incorrect version match

---

## 6. What Will NOT Change

- All backend modules (database/, extraction/, privacy/, embeddings/, search/, monitoring/, organization/, ingestion/)
- requirements.txt
- SQLite schema
- run_seekvault.ps1, run_seekvault.bat
- All 31 unit tests — zero tests weakened
- data_storage/ runtime data
