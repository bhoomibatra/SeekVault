# SeekVault — Evidence-First Product Plan for Antigravity

Version: 2.0  
Purpose: Turn SeekVault into a dependable local-first Windows file-search application through small, verifiable steps.  
Rule: **Audit first. Prove the core workflow. Improve reliability. Polish the UI. Package only after evidence.**

---

## 0. Product definition

SeekVault helps a person find their own files even when they cannot remember the exact filename or folder. It indexes only explicitly approved folders, searches supported document content, explains why results matched, and opens the original file. Privacy and local processing must be described accurately based on actual code and network behavior.

### Product promise to validate

> “Select a folder, search for a concept inside your files, find the relevant document, and open it — without needing to remember its name.”

Do not claim that this promise works until it passes the end-to-end test in Section 7.

## 1. Non-negotiable working rules

1. Do not start with a rewrite.
2. Do not delete or overwrite application code, Git history, databases, FAISS indexes, user files, model caches, configuration, or test data without explicit approval.
3. Inspect Git status and current changes before touching files. Preserve unrelated user changes.
4. Create a recoverable Git checkpoint or backup before any code changes, after confirming the working tree and available disk space. Do not commit secrets or runtime/private data.
5. Work on **one task at a time**. Do not proceed to the next task until I send `CONTINUE`.
6. Do not mark a task complete based only on code generation. Run relevant tests and report exact commands, results, failures, and limitations.
7. Do not weaken, delete, skip, or rewrite tests merely to make the build pass.
8. Never use fake search results, fake statistics, or sample data in normal production mode. If demo data exists, label it clearly and keep it separate from the real user library.
9. Never claim “local-only” unless network behavior and model/dependency behavior have been inspected and verified.
10. Do not send document contents, OCR text, embeddings, or filenames to a remote service without explicit approval and clear disclosure.
11. Do not stage `.env`, credentials, databases, FAISS indexes, private files, model caches, or other runtime data in Git.
12. If a requirement is ambiguous or a change could destroy data, stop and ask before proceeding.
13. If a command fails, report the failure honestly and do not invent output.
14. UI buttons must perform real actions or be disabled with a clear explanation.
15. Use the existing stack where reasonable. Propose a stack change only with evidence and explain migration cost before implementing it.

---

## 2. Scope: what to build, in order

### Phase A — Audit and evidence (do this first)

No application-code modifications during this phase.

- Inspect repository root, branch, Git status, recent commits, uncommitted changes, `.gitignore`, dependencies, application entry points, tests, data locations, model downloads, and current startup command.
- Identify the frontend framework and the actual path from UI to backend search/indexing functions.
- Run existing tests without modifying them, if safe and feasible.
- Start the current application if feasible and inspect its real UI.
- Trace one representative query from the UI through retrieval and result rendering.
- Inspect whether SQLite metadata and FAISS vector IDs can drift and what recovery exists.
- Inspect actual network calls and model behavior before describing privacy guarantees.
- Classify every major feature as:
  - **Verified working** — tested with reproducible evidence.
  - **Partially working** — some path works, but limitations are identified.
  - **Present but unverified** — code exists, behavior not demonstrated.
  - **Missing/broken** — absent or failing.
- Identify what to retain, refactor, replace, or archive. Do not make those changes yet.
- Create a report `docs/AUDIT_REPORT.md` only if that path does not overwrite existing user work; otherwise propose a safe new filename.

Deliverable:
1. Repository and Git summary.
2. Current architecture diagram.
3. Feature verification table with evidence.
4. Existing test commands and exact outcomes.
5. UI review with concrete issues.
6. Data-safety and privacy risks.
7. Minimal next-step recommendation, including what should be retained.
8. Backup/recovery approach.

**Stop and wait for approval.**

### Phase B — Prove the core user journey

Only start after I approve the audit.

Target journey:
1. Launch SeekVault.
2. See clear first-run onboarding when no folders are configured.
3. Select a test folder and explicitly authorize it.
4. Index a small, known set of supported files.
5. Search for a concept that is not in the filename but is present in document content.
6. See the correct file with a genuine excerpt from its content.
7. Open the original file or reveal it in Windows File Explorer.
8. Restart the application.
9. Repeat the search and verify persisted state.
10. Change a test document and verify re-indexing behavior.

Use a dedicated synthetic test folder with non-sensitive files. Do not run tests against the user's personal folders without permission. Test file types only when their parser is actually supported. Do not claim image/OCR search if OCR/image indexing is not implemented.

Before adding features, make this journey pass and record the result.

### Phase C — Reliability and privacy

After the core journey passes, implement the highest-priority gaps revealed by the audit:

- Approved-root authorization enforced in backend code.
- Windows path normalization and boundary/symlink/junction safety as applicable.
- Incremental indexing for added, modified, renamed, and missing files.
- Idempotent ingestion and duplicate-job prevention.
- Robust handling of locked, corrupt, inaccessible, unsupported, temporary, and oversized files.
- Clear progress, cancellation where feasible, retry, and recoverable errors.
- Database/vector-index consistency checks and safe rebuild path.
- Startup recovery after interruption.
- Clear privacy-mode definitions based on the actual data retained:
  - `FULL`: document content may be extracted/indexed according to documented behavior.
  - `REDACTED`: define exactly what is redacted before storage/embedding; test it.
  - `METADATA_ONLY`: store only the explicitly documented metadata and do not silently retain content chunks or content embeddings.
- Diagnostics/logs must not include document contents or secrets by default.
- “Clear index” must never delete source files.
- Backup/restore must be version-aware and fail safely.
- Any network-dependent capability must be disclosed.

Do not implement every item blindly. Use the audit to order them by risk and dependency, one task at a time.

### Phase D — Design and UI polish

Do not build seven dashboards before the core journey and safety checks work.

First create a design brief and interactive preview for the core Search page. Use the existing frontend framework unless the audit proves it is unsuitable. Get my approval before implementing the full UI redesign.

Design requirements:
- Professional, distinctive Windows desktop experience; not a generic admin dashboard.
- Search field is the visual focus.
- Consistent typography, spacing, icons, colors, and interaction states.
- Useful empty, loading, no-results, indexing, offline/model-missing, permission-denied, and recovery states.
- Keyboard navigation, visible focus, semantic labels, readable contrast, and window resizing.
- No dead buttons, invented metrics, decorative charts, or unlabelled demo data.
- Keep results scannable: filename, type, path, real excerpt, modified date if available, and actual relevance evidence.
- Open, reveal in File Explorer, copy path, and inspect details must work.
- Ask before consequential actions such as revoking a folder, clearing an index, or restoring a backup.

### Phase E — Add supporting pages, only after approval

Implement in this order, according to actual product needs:

1. **Search** — primary workspace and core user journey.
2. **File Library** — approved folders and indexed-file state.
3. **Privacy & Security** — actual privacy modes and stored-data transparency.
4. **Indexing & System Health** — progress, errors, consistency, and recovery.
5. **Settings** — only settings that actually work.
6. **Duplicates & Versions** — exact duplicates first; probable versions clearly labelled as suggestions.
7. **Activity & Insights** — only genuine useful statistics; search history is opt-in.

These are product pages, not a requirement to fill every screen with charts. Avoid vanity metrics. Do not add fake analytics.

### Phase F — Search quality and performance

After core functionality is stable:

- Create a small evaluation corpus of synthetic or approved test documents.
- Define representative queries and expected relevant files.
- Measure a clearly defined metric such as Recall@5 or Precision@5 where suitable.
- Compare keyword and semantic retrieval only if both are implemented.
- Test on increasing library sizes and record hardware/environment, dataset size, latency, memory, and limitations.
- Set file-size limits and provide background processing/cancellation as appropriate.
- Treat relevance scores as ranking signals, not guaranteed probabilities unless calibrated and validated.

### Phase G — Windows release readiness

Only after tests and core acceptance criteria pass:

- Document supported Windows versions and prerequisites.
- Test setup from a clean environment.
- Explain model download size, storage location, offline behavior, and first-run time.
- Provide clear installation, upgrade, uninstall, backup, restore, and troubleshooting instructions.
- Ensure uninstall does not unexpectedly delete user source files or the only copy of app data.
- Review licenses for bundled dependencies and models.
- Verify the repository contains no private runtime data or secrets.
- Create a release checklist and document known limitations.

---

## 3. Dashboard/page definitions

### 3.1 Search (default)
- Natural-language search over real indexed content.
- Keyword and semantic search only if actually implemented.
- Filters by file type, approved folder, date, and indexing state where useful.
- Real excerpts and source path.
- Open file, reveal in File Explorer, copy path, view details.
- Honest no-results and index-not-ready states.

### 3.2 File Library
- Only approved folders and their files.
- File type, size, timestamps, indexing status, and errors when available.
- Sorting and filtering.
- Add folder, revoke access, re-index with confirmation.
- Revoking access removes the folder from future processing according to documented behavior; it does not delete source files.

### 3.3 Privacy & Security
- Plain-language explanation of each privacy mode.
- Actual storage behavior, model/network disclosure, and redaction status.
- Approved-folder permissions.
- Safe clearing/export of SeekVault-generated data.
- No unsupported “100% secure” or “everything stays local” claims.

### 3.4 Indexing & System Health
- Real queued/processing/indexed/skipped/failed counts.
- Last successful sync and current operation when available.
- Actionable errors and retry.
- Database/vector-index consistency status based on a real check.
- Safe rebuild/recovery path.

### 3.5 Duplicates & Versions
- Exact duplicate detection via content hash.
- Probable versions based on explicit evidence, clearly labelled as suggestions.
- Review before any file operation; never automatically delete originals.

### 3.6 Activity & Insights
- Real file-type counts, index size if measurable, indexing outcomes, and optional recent searches.
- Search history opt-in and clearly described.
- No fabricated “time saved” or vanity metrics.

### 3.7 Settings
- Only implemented settings: model configuration, storage, theme, shortcuts, backup/restore, diagnostics.
- Show unavailable features as unavailable rather than pretending they work.

---

## 4. Task protocol

For every task, Antigravity must provide:

**Before work**
- Task ID and objective.
- Acceptance criteria.
- Files/components to inspect and likely change.
- Dependencies and risks.
- Whether any action could affect user data.

**After work**
- Exact files changed and why.
- Exact commands run.
- Test results including passed, failed, skipped, and not-run.
- UI screenshots or reproducible evidence for UI changes.
- Known limitations and any unverified behavior.
- Updated status: Complete with evidence / Partial / Blocked.

Do not continue to another task until I send `CONTINUE`. If blocked, ask a concise question and wait.

---

## 5. Core acceptance test

Use only a dedicated synthetic test folder.

- [ ] App starts from documented instructions.
- [ ] Empty first-run state is clear.
- [ ] User explicitly approves a test folder.
- [ ] Supported sample documents index successfully.
- [ ] A query whose words are absent from the filename can find a relevant document based on its content, if semantic retrieval is implemented.
- [ ] Result excerpt is genuinely derived from the source document.
- [ ] Open/reveal action reaches the correct original file.
- [ ] App restart preserves expected index state.
- [ ] Adding or changing a test file updates results according to documented sync behavior.
- [ ] Locked/corrupt/unsupported/inaccessible files fail gracefully.
- [ ] Unauthorized folders are not indexed.
- [ ] Privacy modes match their documented persisted data.
- [ ] Index repair/rebuild never deletes source files.
- [ ] All automated tests are reported honestly with exact commands.
- [ ] No secrets or private runtime data are committed.

Any unchecked item must be reported as incomplete, not silently treated as passed.

---

## 6. Copy-ready Antigravity master prompt

I want to improve SeekVault based on evidence, not blindly rewrite it. Read this entire document before acting.

My goal is a reliable, polished local-first Windows file-search application. The key user journey is: select an authorized folder, index supported files, search for a concept even when the filename is forgotten, see a real excerpt, open the correct original file, and confirm the index persists after restart.

**Start with Phase A / TASK-00 only. Do not modify application code yet.** Inspect the current repository, Git status and changes, architecture, UI, dependencies, tests, data paths, network/model behavior, SQLite/FAISS consistency, and existing recovery options. Run existing tests only when safe. Create no destructive changes. Report exact evidence and classify each feature as verified working, partially working, present but unverified, or missing/broken.

Do not assume earlier test reports are true. Do not fabricate output. Preserve working code and all user data. Do not delete databases, indexes, model caches, Git history, source files, or configuration. Never weaken tests or send document content to remote services without explicit approval.

Return the audit report, architecture, feature verification table, exact test outcomes, concrete UI findings, risks, and the smallest safe next step. Then stop and wait for my approval. After approval, work on one task at a time and wait for my explicit `CONTINUE` after every task.

Do not build all dashboards first. Prove the core user journey and reliability, then design the Search page preview, then implement supporting pages, evaluate search quality, and prepare Windows packaging. Every claim of completion must have reproducible evidence.
