# SeekVault — Product Requirements & Line-by-Line Rebuild Plan

**Product:** SeekVault — Local-First, Privacy-Aware Semantic File Search & Organization  
**Target platform:** Windows 10/11, with a documented Python environment  
**Initial interface:** Product-quality frontend; select the framework after auditing the current implementation  
**Execution rule:** One task at a time. Verify it, report evidence, then wait for approval.

---

## 1. Problem, Users, and Core Journey

People accumulate PDFs, Word documents, notes, screenshots, images, and other files across nested folders. They often remember what a file contains but not its name or location. Traditional filename search does not reliably answer requests such as “find the lecture notes explaining Candidate Elimination” or “find the screenshot with the Java connection error.”

SeekVault is intended to let users search their own files by meaning while preserving control over which folders are accessed and how sensitive content is indexed.

**Primary user:** An individual Windows user with a large collection of documents and images.

**Core journey:** User launches SeekVault → selects and authorizes a folder → reviews the indexing plan → indexes supported files locally → enters a natural-language query → sees relevant documents/images with useful metadata → opens a file or its containing folder → changes are synchronized → results remain available after restart.

## 2. MVP vs Optional

### Must-have MVP
- Professional, coherent, responsive interface suitable for a real product.
- First-run onboarding and clear empty states.
- Explicit folder authorization and revocation.
- Local indexing of PDF, DOCX, TXT/MD, PNG, JPG/JPEG files.
- Text semantic search and text-to-image search, when compatible local embedding models are available.
- Privacy tiers: `FULL`, `REDACTED`, and `METADATA_ONLY`, with behavior defined and tested.
- SQLite metadata persistence and durable FAISS vector indexes with stable mappings.
- Long-document chunking and result deduplication by parent file.
- Search-time authorization checks.
- Open File and Open in File Explorer actions.
- Duplicate and version detection.
- Safe handling of new, modified, moved, and deleted files.
- Useful progress, errors, diagnostics, and logs.
- Repeatable setup, launch instructions, automated tests, and end-to-end verification.

### Defer until core product is stable
- Optional local LLM/VLM or Ollama integration.
- Cloud sync, user accounts, team collaboration, telemetry, or hosted backend.
- Complex packaging/installer work beyond a reliable documented Windows launcher.
- Advanced ranking models or large-scale indexing optimizations.

Do not add optional features simply to make the roadmap look larger. Prioritize a stable end-to-end workflow.

## 3. Product Architecture Summary

Proposed high-level flow:

```text
Product-quality UI
    ↓
Folder authorization and user actions
    ↓
Ingestion coordinator
    ├── File discovery and format detection
    ├── PDF/DOCX/TXT/MD extraction
    ├── Image processing and optional OCR
    ├── Privacy classification and sanitization
    └── Chunking for long documents
            ↓
Local embedding models
    ├── Text embeddings
    └── Image/text embeddings in a compatible space
            ↓
Persistence
    ├── SQLite: folders, file metadata, status, privacy tiers, relationships
    └── FAISS: vectors and stable vector-ID mappings
            ↓
Search engine
    ├── Candidate retrieval and ranking
    ├── File/chunk result aggregation
    ├── Search-time authorization verification
    └── File actions and previews
            ↓
Monitoring and reconciliation
```

**Important:** This is a proposed architecture. Antigravity must inspect the current code and confirm the exact modules and framework before implementation. Do not blindly migrate frameworks or duplicate working components.

## 4. Key Design Decisions

| Decision | Rationale |
|---|---|
| Local-first by default | User documents, extracted content, embeddings, and indexes should remain on the user's machine unless an explicitly configured feature requires otherwise. |
| Explicit folder authorization | Prevents broad, unexpected crawling of the user's drive. |
| SQLite + FAISS | SQLite holds durable metadata; FAISS supports vector retrieval. Stable IDs and reconciliation keep them aligned. |
| Privacy check before embedding | Prevents disallowed raw sensitive content from entering searchable vector representations. |
| Chunk long documents | Makes content from later pages searchable without relying on a single truncated embedding. |
| Idempotent ingestion | Repeated scans should not create duplicate records or vectors. |
| Non-destructive repair | Missing/corrupt indexes should be backed up and rebuilt deliberately, not by silently wiping data. |
| Search-time authorization | Results must be rechecked in case a folder was revoked or a file moved/deleted. |
| Product-first frontend | A visually polished UI is part of the MVP; every control must connect to real behavior. |
| Tests plus manual workflow | Unit tests alone cannot prove that a real user can complete the core journey. |

## 5. Local Data Model — Quick Reference

The final schema must be derived from the current code audit and the actual query patterns. Do not create redundant tables without a reason.

Likely logical records:

| Record | Purpose |
|---|---|
| Authorized folders | Normalized folder path, active/revoked status, creation time and scan status. |
| Files | Stable file ID, path, parent folder ID, file type, size, timestamps, hash, privacy tier, and ingestion status. |
| Chunks | Parent file ID, chunk identifier/order, sanitized text or permitted representation, and vector mapping as needed. |
| Duplicate groups | Exact duplicate grouping based on a content hash. |
| Version relationships | Related file IDs, relationship evidence, timestamps, and confidence/heuristics where applicable. |
| Index state | Schema/index version and reconciliation metadata if needed. |

FAISS stores vectors; it is not the authoritative store for file metadata. Each vector ID must map back to a stable file or chunk record. Define how image vectors differ from text vectors and how text-to-image retrieval uses compatible embedding spaces.

## 6. Prerequisites Checklist

Before implementation:
- [ ] Inspect current repository, README, PRD, synopsis, tests, dependencies, and UI.
- [ ] Confirm the active project root and actual Python interpreter.
- [ ] Check Git status and current branch.
- [ ] Create a dated backup/rollback point before any large changes.
- [ ] Identify the actual location of SQLite databases, FAISS files, sample data, and model caches.
- [ ] Review `.gitignore` for databases, indexes, personal files, `.env`, credentials, virtual environments, and caches.
- [ ] Confirm local model download requirements, disk usage, licensing, and first-run behavior.
- [ ] Document whether OCR requires Tesseract and how the app behaves when it is unavailable.
- [ ] Ensure a mock/test mode exists for tests without representing mock results as real user data.

Never commit secrets, private documents, local databases, or indexes derived from private documents to GitHub.

## 7. Biggest Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Current implementation is inconsistent or hard to maintain | Audit first, then build a clean replacement plan with explicit reuse/replacement decisions. |
| UI looks unfinished | Create and approve a visual system and screen designs before full frontend implementation. Test the real interaction flow. |
| Database and FAISS drift apart | Stable IDs, persistence tests, consistency checks, safe backup-first repair, and explicit reconciliation. |
| Sensitive text leaks into vectors/snippets | Apply and test privacy treatment before embedding; inspect stored representations with security tests. |
| Unauthorized files appear in results | Enforce folder containment during ingestion and recheck authorization at query time. |
| Indexing large folders blocks the UI | Show progress and errors; use background work where appropriate without losing durable state. |
| Watchdog emits duplicate events | Filter temporary files, debounce events, and make processing idempotent. |
| Models are unavailable or fail to download | Explain setup and fallback behavior; never silently claim semantic search works if model initialization failed. |
| Tests pass but the product is unusable | Require manual end-to-end validation using a folder selected by the user. |
| “100% local” claim is not proven | Audit network behavior and dependencies; state precisely what is local and any exceptions. |
| Destructive reset loses user data | Keep a backup/branch, inspect reset scripts, and require explicit approval before deleting or rebuilding state. |

## 8. Exact Implementation Order

Follow these tasks in order. Antigravity must first audit the current code and adapt this plan if a task is already implemented. Do not mark tasks complete without evidence.

### TASK-00 — Audit and protect the current project

1. Run `git status --short --branch` and inspect current branch/remotes.
2. Inventory source, tests, documentation, runtime data, model files, and generated artifacts.
3. Inspect scripts for automatic database/index clearing or sample-data seeding.
4. Create a backup branch/archive and back up local database/index data outside the active project.
5. Record how to restore the previous working state.
6. Do not change or delete application code yet.

**Acceptance:** Audit report exists, backup path is verified, no data was deleted, and the current project can be restored.

### TASK-01 — Product specification and UI audit

1. Inspect the current UI and identify specific issues with hierarchy, spacing, typography, layout, navigation, states, responsiveness, and usability.
2. Define target users, core journey, supported formats, privacy behavior, and MVP boundaries.
3. Map each requirement to a UI screen, backend module, and verification method.
4. Create `SEEKVAULT_REBUILD_PLAN.md` and a requirement-to-test matrix.

**Acceptance:** A concrete, auditable plan exists; no vague “make it better” requirements remain.

### TASK-02 — Frontend design system and preview

1. Inspect current framework and decide whether to retain it or propose a migration. Explain the trade-off first.
2. Define typography, colors, spacing, layout grid, icon style, borders, states, and accessibility rules.
3. Design Welcome/Onboarding, Search, Authorized Folders, Indexed Files, Duplicates & Versions, Privacy/Settings, and Diagnostics screens.
4. Create a visual preview or prototype before wiring all backend functionality.
5. Use realistic example content only in design previews and label it as sample content.

**Acceptance:** The user approves a coherent product design before full UI implementation.

### TASK-03 — Reproducible Windows setup

1. Confirm Python and frontend runtime versions.
2. Define one authoritative dependency setup.
3. Use project-relative configuration and a user-writable application data directory; do not hardcode a developer's home path.
4. Provide `.env.example` only if environment settings are needed, and ignore real `.env` files.
5. Document install, launch, diagnostics, and shutdown commands.
6. Verify a clean launch without a pre-seeded database.

**Acceptance:** Setup instructions work in a clean environment or the exact blockers are documented.

### TASK-04 — SQLite schema and safe initialization

1. Inspect the existing schema and query patterns before changing it.
2. Add versioned migrations or safe initialization.
3. Define folder, file, chunk, privacy, duplicate/version, and indexing-state records as needed.
4. Use transactions and stable IDs.
5. Never reset the database automatically during normal startup.
6. Back up existing state before migrations that could alter data.

**Acceptance:** Database creation and migrations are repeatable and preserve existing records.

### TASK-05 — Folder authorization and path safety

1. Implement add/revoke folder workflow.
2. Normalize absolute paths correctly for Windows.
3. Enforce containment using path-aware logic rather than unsafe string-prefix checks.
4. Define symlink behavior and test it.
5. Verify access during ingestion and immediately before returning search results.
6. Suppress results for revoked folders or files that no longer exist.

**Acceptance:** Tests cover nested folders, case differences, sibling-prefix paths, revocation, missing files, and relevant symlink cases.

### TASK-06 — Extraction and indexing pipeline

1. Enumerate supported files only within authorized folders.
2. Extract PDF, DOCX, TXT/MD text and image metadata; OCR only when configured and available.
3. Handle corrupt, locked, empty, and unsupported files gracefully.
4. Chunk long documents with overlap and retain parent-file mapping.
5. Report per-file status and errors.
6. Prove source files remain unchanged using hashes in tests.

**Acceptance:** A real user-selected folder can be indexed with transparent results and no source-file modifications.

### TASK-07 — Privacy classification and sanitization

1. Define precise FULL, REDACTED, and METADATA_ONLY semantics.
2. Apply classification and sanitization before generating embeddings.
3. Ensure metadata-only files do not leak content through vectors or snippets.
4. Ensure redacted values do not appear in searchable representations where prohibited.
5. Record tier and processing outcome in SQLite.
6. Test false positives, false negatives, malformed text, and image OCR content.

**Acceptance:** Security tests inspect stored representations, not only classifier labels.

### TASK-08 — Embedding providers and model lifecycle

1. Identify the text and image models currently used and verify compatibility.
2. Document model download, cache location, licensing, memory/storage requirements, and offline behavior.
3. Provide clear errors when models are unavailable.
4. Keep text-to-image retrieval within a compatible shared embedding space.
5. Avoid unnecessary repeated model initialization.

**Acceptance:** Model initialization and embedding dimensions are verified; no fake search results are returned on model failure.

### TASK-09 — Persistent FAISS indexes and consistency

1. Define stable mappings between FAISS vector IDs and file/chunk IDs.
2. Persist and reload text and image indices.
3. Handle repeated ingestion idempotently.
4. Detect missing vectors and orphaned mappings.
5. Implement backup-first repair/reindexing.
6. Ensure normal app startup does not silently delete indexes or rebuild all user data.

**Acceptance:** Save/reload/search tests pass, and index/database consistency can be checked and repaired safely.

### TASK-10 — Semantic search engine

1. Embed natural-language queries with the correct local model.
2. Retrieve vector candidates and map them to durable file/chunk records.
3. Recheck authorization and file existence.
4. Aggregate chunk hits so one document does not appear repeatedly.
5. Return useful snippets and accurate metadata.
6. Add text-to-image search if the image model supports compatible cross-modal embeddings.
7. Handle no-results, unavailable-model, and corrupt-index cases.

**Acceptance:** A documented set of natural-language queries retrieves expected files from real indexed data.

### TASK-11 — Product frontend implementation

1. Implement the approved design system and screen layouts.
2. Connect each view to real application state and services.
3. Implement folder selection, indexing progress, cancellation/error states, search filters, previews, and file actions.
4. Remove fake metrics, dead buttons, placeholder controls, and academic branding from the product UI.
5. Ensure keyboard access, readable contrast, responsive layouts, and consistent visual hierarchy.
6. Add empty/loading/success/error/no-results states.

**Acceptance:** Every visible control works, and the user can complete the core journey without developer intervention.

### TASK-12 — Open File and Open Folder actions

1. Check file existence and authorization before acting.
2. Open files through safe OS integration.
3. Reveal files in Windows Explorer.
4. Handle moved/deleted files and permission errors.
5. Never execute document contents or shell commands extracted from files.

**Acceptance:** Manual Windows testing confirms both actions work safely.

### TASK-13 — Watchdog synchronization

1. Filter editor lock files and temporary/incomplete downloads.
2. Debounce noisy filesystem events.
3. Re-index modified files without duplicate records/vectors.
4. Handle create, move, and delete events.
5. Refresh in-memory indices safely.
6. Provide a manual rescan/reconciliation option.

**Acceptance:** Changes appear in search without requiring a restart, and repeated events remain idempotent.

### TASK-14 — Duplicate and version workflows

1. Detect exact duplicates using a content hash.
2. Define conservative version heuristics and show evidence.
3. Display duplicate groups, version relationships, and useful file metadata.
4. Never automatically delete, rename, or move files.

**Acceptance:** Results are correct on a defined fixture set; no original files are changed.

### TASK-15 — Security and reliability tests

1. Test unauthorized access and revoked-folder behavior.
2. Test source-file immutability.
3. Test privacy-tier leakage into stored representations.
4. Test database/index restart persistence and repair.
5. Test corrupt/locked files, path edge cases, and missing models.
6. Test that logs do not expose sensitive content.
7. Audit network behavior before making local-only claims.

**Acceptance:** Required tests pass; limitations and any unresolved risks are documented honestly.

### TASK-16 — Retrieval evaluation

1. Create a small labeled set of test files and natural-language queries.
2. Record expected relevant files.
3. Measure Precision@K, Recall@K, MRR, and latency where appropriate.
4. Document hardware, model versions, dataset size, and method.
5. Do not invent or cherry-pick performance numbers.

**Acceptance:** Results are reproducible and limitations are stated.

### TASK-17 — Packaging and documentation

1. Finalize clean Windows setup and launch instructions.
2. Explain local data paths, model downloads, backups, reindexing, and troubleshooting.
3. Verify `.gitignore` excludes secrets, databases, FAISS indices, personal files, model caches, and virtual environments.
4. Remove unsupported claims from README and UI.
5. Test the complete workflow from a fresh setup.
6. Review final diff before committing or pushing.

**Acceptance:** A new user can install, launch, select a folder, index files, search, open results, restart, and continue searching.

## 9. Minimum End-to-End Acceptance Workflow

The MVP is not complete until all of the following have been demonstrated:

1. Launch SeekVault on Windows using documented commands.
2. See a clean first-run screen without fake user data.
3. Select and authorize a folder.
4. Review the files and start indexing.
5. See clear progress and per-file errors.
6. Search by document meaning rather than filename.
7. Search for an image using a natural-language description where supported.
8. Open a result and reveal it in File Explorer.
9. Close and reopen the app; search results still work.
10. Add, modify, move, and delete a test file; confirm synchronization.
11. Revoke folder access; confirm its results disappear.
12. Verify privacy-tier behavior and original-file immutability.
13. Run automated tests and E2E verification.
14. Confirm documentation matches observed behavior.

## 10. Master Prompt for Antigravity

Paste this prompt into Antigravity with this Markdown file available in the project root:

> I am unhappy with the previous SeekVault implementation, particularly the frontend. I want a deliberate product reset and a professional, sellable-quality local-first file search product that runs on my Windows machine.
>
> Read `SEEKVAULT_PRODUCT_RESET_LINE_BY_LINE.md` from beginning to end. Treat it as the source of truth for scope and execution.
>
> First, audit the existing repository and preserve a verified backup. Do not blindly delete the repository, Git history, database, FAISS indexes, model caches, sample data, or user files. Do not run destructive cleanup or reset scripts without explaining exactly what they will delete and receiving my explicit approval.
>
> The frontend is a core requirement. Do not give me another generic, unfinished dashboard. Inspect the current UI, identify specific failures, propose a coherent visual design system, and create a visual preview before implementing the full UI. The result must have consistent typography, spacing, navigation, useful search result cards, polished empty/loading/error states, responsive layouts, and working controls. No fake metrics, dead buttons, academic branding, or unsupported privacy claims.
>
> The product must index folders I choose, search real local documents and images, enforce authorization, apply privacy tiers before embedding, persist SQLite and FAISS state across restarts, synchronize file changes, and leave original files unchanged.
>
> Execute exactly one numbered task at a time. Before each task, state the goal, files to inspect/change, planned commands, risks, and acceptance criteria. After implementation, show the diff summary, exact commands and actual test output, manual verification evidence where relevant, known limitations, and updated task status. Stop and wait for my explicit `CONTINUE` before starting another task.
>
> Never mark a task DONE just because code was generated or tests were weakened. Never fabricate results. Never silently clear or rebuild user data. Keep the tracker consistent with actual implementation. Do not commit or push until I approve the diff.
>
> Start with TASK-00 only: audit and protect the current project. Do not modify application code yet. Return the audit, backup path, current UI assessment, and proposed clean rebuild plan, then stop.

## 11. How to work through the plan

1. Save this document as `SEEKVAULT_PRODUCT_RESET_LINE_BY_LINE.md` in the repository root.
2. Give the master prompt to Antigravity.
3. Review TASK-00 and confirm the backup exists.
4. Approve one task at a time by replying `CONTINUE`.
5. Review each diff and test report before moving forward.
6. Commit verified milestones, but never commit private runtime data.

**Operating rule:** one task, one diff, one verification report, one approval.


---

# PRODUCT REALISM & DASHBOARD EXPANSION (ADDED)

## 1. Product direction

SeekVault is a local-first desktop product for finding and managing a user's own files. It must not feel like a generic admin template, analytics demo, or cloud-drive clone. The core value is: **find the right file even when the user has forgotten its name or location, while keeping access and processing transparent.**

Build a coherent application shell with one primary Search workspace and focused supporting pages. Use a consistent navigation system, keyboard-accessible controls, clear empty/loading/error/success states, and a visual hierarchy that puts search first.

## 2. Required navigation and dashboards

### Page A — Search (default landing page; highest priority)
- Prominent natural-language search input with examples and a clear action.
- Search actual indexed content, not mock results.
- Filters: file type, authorized folder, modified date, and privacy/indexing state where meaningful.
- Result rows/cards must show filename, file type, folder/path, modified date when available, a real matching excerpt, and a concise reason or matched terms where the engine can support it.
- Actions: open file, reveal in file manager, copy path, and inspect details.
- Show honest no-results guidance, indexing-in-progress messaging, unsupported-file messages, and index-unavailable recovery.
- Search must remain useful without a remote LLM. Explain which capabilities need an optional model, if any.

### Page B — File Library
- List only files within explicitly authorized folders.
- Show supported file type, size and timestamps when available, indexing state, and last error if processing failed.
- Support sorting and filtering.
- Add folder and remove/revoke folder access through explicit confirmation.
- Explain that removing a folder from the index must not delete the original files.
- Provide a safe re-index action with progress and cancellation where feasible.

### Page C — Privacy & Security
- Clearly explain FULL, REDACTED, and METADATA_ONLY modes in plain language.
- Show the effective privacy mode per folder/file and the actual data stored for each mode.
- Show sensitive-content detection/redaction status, including uncertainty and false-positive limitations.
- Make local-vs-network behavior explicit. Do not claim “everything stays local” if any selected capability sends data outside the machine.
- Default to least privilege and do not index outside approved roots.
- Provide a way to inspect, export, and safely clear SeekVault's own index/cache data, with confirmation and clear explanation of what will and will not be deleted.

### Page D — Indexing & System Health
- Display queued, processing, indexed, skipped, and failed counts from real backend state.
- Show last successful sync and current activity, where supported.
- Explain failures in actionable language and expose a diagnostic detail view.
- Support retrying failed files and safe index consistency checks/rebuilds.
- Detect missing files, changed files, unsupported formats, locked files, permission errors, and corrupted/unavailable index state.
- Never imply an index is healthy solely because the UI loaded.

### Page E — Duplicates & Versions
- Start with exact duplicates based on content hashes; label semantic/similar-file matches as suggestions, not confirmed duplicates.
- Group probable versions using evidence such as filename, content similarity, and timestamps; show the evidence and confidence.
- Keep all destructive actions review-first. Do not delete, move, or overwrite original files automatically.
- Let users open/reveal compared files and dismiss incorrect matches.

### Page F — Activity & Insights
- Show truthful, derived statistics only: indexed files by type, index size if measurable, recent indexing events, failure counts, and recent searches only if search history is enabled.
- Make search history optional and explain where it is stored.
- Avoid vanity metrics, invented time-saved claims, fake charts, and analytics that do not support a user task.
- Provide a useful empty state for new installations.

### Page G — Settings
- Configure embedding/model options only when actually supported.
- Show model download/cache locations and storage usage when measurable.
- Manage folder access, theme, keyboard shortcuts, startup behavior, and diagnostics only if implemented.
- Provide backup/restore for SeekVault metadata and index with version compatibility checks and safe failure handling.
- Clearly separate “clear index” from “delete original files”; the former must never silently perform the latter.

## 3. Real-world capabilities to add

Prioritize these by dependency and product value. Do not build everything before the core search loop is reliable.

### P0 — Reliability and user trust (required before calling it a usable product)
1. First-run onboarding that explains local processing, asks the user to select authorized folders, and shows supported file types.
2. Permission-aware folder selection and strict path-boundary checks; prevent traversal and accidental indexing outside approved roots.
3. Incremental indexing: detect new, changed, renamed, and deleted/missing files without reprocessing everything unnecessarily.
4. Robust file handling: temporary files, locked files, permission errors, corrupt files, unsupported formats, very large files, and interrupted processing.
5. Persistent job status and clear progress/error messages; app restart must not leave misleading “in progress” jobs.
6. Index integrity checks and recoverable rebuilds; never silently destroy the only index or user data.
7. Logging and diagnostics with sensitive content redacted; never log full document text, secrets, or unnecessary absolute paths by default.
8. Strong tests for path authorization, privacy-mode behavior, persistence, file changes, index recovery, and actual open/reveal actions.
9. Accessibility and keyboard support: visible focus, semantic labels, predictable tab order, readable contrast, and sensible shortcuts.
10. Clear data lifecycle: what is stored, where, how to back it up, and how to clear SeekVault-generated data safely.

### P1 — Meaningful differentiation
1. Hybrid retrieval combining keyword/full-text search with semantic vector search, if supported by the selected architecture; expose ranking honestly.
2. Search explanations: matched text snippets, matched fields, and relevance signals rather than unsupported “AI reasoning.”
3. OCR for scanned PDFs and images, with clear OCR status and language limitations.
4. Content-hash exact duplicate detection and reviewable version grouping.
5. File watcher with debouncing and a manual “sync now” fallback.
6. Search filters, saved searches, and optional recent-search history.
7. Evaluation set of representative queries and expected files; measure Recall@k/Precision@k or another clearly defined metric and record limitations.
8. Model lifecycle management: first-run download, offline availability, model version, cache location, and graceful failure if a model is missing.

### P2 — Optional after evidence of need
- Image-text search across supported images.
- Local document preview and safe excerpt navigation.
- User-configurable exclusions for folders, file patterns, and file sizes.
- Exportable diagnostic bundle that excludes document contents by default.
- Optional encrypted backups or encryption-at-rest only after a threat model and key-management plan are documented.
- Import/export of settings and saved searches.

Do not add accounts, teams, cloud sync, billing, telemetry, remote LLM calls, or collaboration features to the local-first MVP unless the product scope changes explicitly. These add privacy, security, and support obligations.

## 4. UX and visual design acceptance criteria

- Design the Search page first and present a navigable design preview before implementing the full UI.
- Use a distinctive, polished desktop-product visual system: deliberate typography, consistent spacing, restrained color, high-quality icons, clean tables/cards, and clear focus/hover/disabled states.
- Avoid excessive dashboard KPI cards, gradients used as decoration, fake charts, generic admin-template styling, and unnecessary empty space.
- The Search page should prioritize the query field and result quality; secondary analytics must not compete with it.
- Every button must perform a real action or be clearly disabled with an explanation. No dead controls.
- Every page must include designed empty, loading, error, offline/model-missing, permission-denied, and recovery states as relevant.
- Use realistic demo/sample data only in an explicitly labeled demo mode. Never mix demo data with the user's real library.
- Support practical Windows window sizes, resizing, high-DPI displays, and keyboard-only navigation.
- Use confirmation dialogs for revoking folder access, clearing indexes, restoring backups, or other consequential actions.
- Provide undo/recovery where technically safe; otherwise explain irreversibility before confirmation.

## 5. Security, privacy, and trust requirements

- Treat filenames, paths, extracted text, OCR text, and document metadata as untrusted input.
- Enforce approved-root checks on the backend, not just by hiding files in the UI.
- Use parameterized SQL and safe filesystem operations; guard against symlink/junction escapes where applicable on Windows.
- Do not execute or render active content from indexed files.
- Keep secrets and personal document contents out of logs, crash reports, screenshots, and diagnostic bundles by default.
- Explain that privacy modes may limit search quality and define exactly what each mode indexes, embeds, stores, and deletes.
- If any model or dependency makes a network request, disclose it and provide an offline-safe behavior where possible.
- Include threat-model notes and a clear list of known limitations; do not claim certification or absolute security without evidence.

## 6. Data integrity and recovery

- Make the SQLite database the source of truth for file metadata and indexing state; document the exact relationship between metadata and vector IDs.
- Use stable identifiers and explicit transactions for metadata updates.
- Keep vector-index writes and database state synchronized or recoverable after partial failures.
- Use atomic writes or safe replacement strategies for persisted indexes and backups where possible.
- Make re-indexing idempotent.
- On startup, detect missing/stale index files and offer a safe repair/rebuild path.
- Never remove original user files during index cleanup.
- Test interruption during ingestion and index writes, app restart, and backup restoration.

## 7. Product-quality acceptance workflow

A release candidate is not complete until the following real workflow passes on Windows:
1. Install/setup from documented instructions on a clean environment.
2. Launch and see an honest first-run onboarding screen.
3. Select one test folder and explicitly approve it.
4. Index supported PDF, DOCX, TXT/MD, and image files where the relevant parser/OCR exists.
5. Search for a phrase and a concept that do not appear in the filename.
6. Confirm results show real excerpts and open/reveal the correct source file.
7. Modify, rename, add, and remove a test file; verify incremental sync behavior.
8. Restart the app and confirm metadata/index persistence.
9. Simulate a locked, corrupt, unsupported, and inaccessible file; verify graceful errors and retry.
10. Run integrity checks and rebuild the index without changing original files.
11. Verify each privacy mode's actual stored artifacts and search behavior.
12. Confirm unauthorized sibling folders and paths outside approved roots are not indexed.
13. Test no-results, empty-library, missing-model, database/index failure, and permission-denied states.
14. Run automated tests and report exact commands, counts, failures, and any skipped tests.
15. Verify no private runtime data, local database, embeddings, model cache, secrets, or user documents are staged in Git.

## 8. Updated task sequencing

Keep the original task plan, but insert or adapt tasks so the sequence is:
- TASK-00: Audit repository, current state, dependencies, tests, and Git status; create a safe recovery point before changes.
- TASK-01: Review requirements and current UI; map existing features to requirements and identify gaps.
- TASK-02: Create navigation map, user flows, design system, and clickable/interactive design preview. No backend rewrite yet.
- TASK-03: Validate architecture and Windows setup; document decisions and risks.
- TASK-04: Define data lifecycle, threat model, privacy-mode semantics, and SQLite schema.
- TASK-05: Implement folder authorization and Windows path safety.
- TASK-06: Implement robust extraction and ingestion.
- TASK-07: Implement privacy processing and test actual persisted outputs.
- TASK-08: Implement embedding generation and model lifecycle.
- TASK-09: Implement persistent vector indexing and integrity recovery.
- TASK-10: Implement hybrid/semantic search and result explanations.
- TASK-11: Implement the approved UI against real backend contracts, with every state designed.
- TASK-12: Implement open/reveal/copy-path and safe index-management actions.
- TASK-13: Implement incremental sync/file watching and restart recovery.
- TASK-14: Implement exact duplicates and probable version grouping.
- TASK-15: Implement security, privacy, reliability, accessibility, and end-to-end tests.
- TASK-16: Build a search-quality evaluation set and report metrics honestly.
- TASK-17: Package for Windows, document installation, backup/restore, limitations, troubleshooting, and release checks.
- TASK-18: Final product audit against every acceptance criterion; no feature may be marked complete without evidence.

## 9. Instructions for Antigravity

Read this document completely before making changes. Treat this as a product and engineering contract, not a suggestion list.

First inspect the current repository, Git status, architecture, existing UI, tests, dependency versions, and data paths. Do not assume that existing implementation or reported tests are correct; verify them. Create a recovery point before modifying files. Do not delete or overwrite the database, FAISS index, user files, model caches, Git history, or existing code without explicit approval.

For every task:
1. State the objective and acceptance criteria.
2. List files to inspect and likely files to change.
3. Explain dependencies, risks, and any design/architecture decision.
4. Implement only the current task.
5. Run the relevant tests and report exact commands and results.
6. Show screenshots or a reproducible preview for UI work, and identify what is real versus sample data.
7. Report limitations, failures, and unverified claims honestly.
8. Update the task checklist only when evidence supports completion.
9. Stop and wait for my explicit `CONTINUE`.

Do not start by rebuilding the entire repository. Start with TASK-00 and do not modify application code in that first task. Audit and report first. Then wait.

## 10. Updated copy-ready master prompt

I want to turn SeekVault into a polished, reliable, real-world local-first file search product for Windows. Read `SEEKVAULT_PRODUCT_RESET_LINE_BY_LINE.md` completely and follow it as the source of truth.

My main dissatisfaction is the UI and the feeling that the project is an academic demo rather than a product. The application must have a premium, coherent desktop experience with these pages: Search (default), File Library, Privacy & Security, Indexing & System Health, Duplicates & Versions, Activity & Insights, and Settings. Search is the heart of the product and must be built first in design terms. Prioritize real natural-language search, useful result snippets, filters, open/reveal actions, and clear empty/loading/error/recovery states.

Implement the real-world requirements in this document: safe folder authorization, incremental indexing, robust file handling, persistent jobs, database/vector-index integrity and recovery, explicit privacy semantics, safe diagnostics, optional OCR where supported, duplicate/version review, accessibility, backup/restore, search-quality evaluation, and Windows packaging. Separate P0, P1, and P2. Do not let optional features delay a reliable core search workflow.

Important rules:
- Audit the existing repo and tests; do not assume previous reports are true.
- Preserve Git history and make a safe recovery point before changes.
- Never silently wipe or overwrite source files, databases, FAISS indexes, user files, model caches, or configuration.
- Do not send document content to remote services unless I explicitly approve that product-scope change and it is clearly disclosed.
- Do not fabricate metrics, mock results in production, claim tests passed without running them, weaken tests, or leave dead buttons.
- Do not stage secrets or runtime/private data in Git.
- Work strictly one task at a time. Report changed files, commands, test output, screenshots/evidence, limitations, and status. Stop and wait for my explicit `CONTINUE` after each task.
- Start with TASK-00 only: inspect and report repository/Git status, architecture, UI, tests, dependencies, data paths, risks, and backup/recovery options. Do not modify application code in TASK-00.
- After TASK-00, wait for approval. For TASK-02, present the dashboard navigation, design system, and an interactive UI preview before full implementation.
