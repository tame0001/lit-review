# Literature Review Cockpit — Code Audit & Inspection Roadmap

This document tracks the findings from our code audit of `backend/`, `frontend/`, and `Makefile`, structured into **4 phases** so you can incrementally inspect, verify, and refactor the codebase.

---

## Phase 1: Backend Bug Fixes, Performance & Data Integrity

Focus: Fix functional bugs, eliminate O(N) performance bottlenecks, and ensure data consistency across Zotero, SQLite, and Obsidian frontmatter.

### 1.1 Eliminate Full-Library Annotation Fetching Bottleneck
- **File:** [zotero_service.py](file:///home/tam/github/lit-review/backend/app/services/zotero_service.py#L477-L485)
- **Issue:** In `get_pdf_annotations()`, when `is_local_available` is true, it calls `self._local_get("items", {"itemType": "annotation", "limit": 10000})` and filters in Python by `parentItem == pdf_key`. For a library with hundreds of papers, syncing or rebuilding fetches every annotation in the entire Zotero library for every PDF.
- **Fix:** Query `items/{pdf_key}/children` directly via `_get_children_raw(pdf_key)` in both local and cloud modes.

### 1.2 Fix Zotero `itemType` Exclusion Query Syntax
- **File:** [zotero_service.py](file:///home/tam/github/lit-review/backend/app/services/zotero_service.py#L368-L385)
- **Issue:** `get_read_papers()` passes `"itemType": "-attachment || note"`. In the Zotero Web/Local API, `||` is OR, so `-attachment || note` does not exclude `note` or `annotation` at the API level (relying on the Python post-filter and wasting pagination bandwidth).
- **Fix:** Use `-attachment -note -annotation` (or the `/items/top` endpoint) so Zotero only returns top-level primary items.

### 1.3 Fix Citekey Extraction, Collisions & Path Traversal
- **Files:**
  - [zotero_service.py](file:///home/tam/github/lit-review/backend/app/services/zotero_service.py#L218-L240)
  - [obsidian_service.py](file:///home/tam/github/lit-review/backend/app/services/obsidian_service.py#L51-L65)
  - [papers.py](file:///home/tam/github/lit-review/backend/app/routers/papers.py#L62-L122)
- **Issues:**
  1. `_extract_citekey()` regex `[A-Za-z0-9_-]+` truncates valid Better BibTeX citekeys containing `:` or `.`.
  2. Two papers by the same first author in the same year can generate the same fallback `citekey`, overwriting each other's `@citekey.md` note and colliding on `WHERE citekey = ?` in SQLite.
  3. `citekey` path parameters in `papers.py` are concatenated into `obs.lit_dir / f"@{citekey}.md"` without path-traversal validation.
- **Fix:**
  - Expand allowed citekey characters (while sanitizing filesystem-unsafe characters like `/` or `..`) and verify `note_path.resolve().is_relative_to(self.lit_dir.resolve())`.
  - Store Zotero `key` (`zotero_key`) in Obsidian frontmatter and append a disambiguator (or item key suffix) when a fallback citekey collides.

### 1.4 Prevent Priority Score Drift by Storing Score Components
- **Files:**
  - [llm_service.py](file:///home/tam/github/lit-review/backend/app/services/llm_service.py#L167-L196)
  - [obsidian_service.py](file:///home/tam/github/lit-review/backend/app/services/obsidian_service.py#L195-L213)
  - [sync_service.py](file:///home/tam/github/lit-review/backend/app/services/sync_service.py#L158-L171)
  - [papers.py](file:///home/tam/github/lit-review/backend/app/routers/papers.py#L86-L95)
- **Issue:** Only the sum `priority_score` and `manual_bonus` are persisted in frontmatter/SQLite (`relevance_score` is discarded). Later updates to `manual_bonus` or `scite_total_citations` reverse-engineer the score via `old_score - old_component + new_component`, which can drift or lose precision.
- **Fix:** Persist `relevance_score` in Obsidian frontmatter and SQLite, and always recompute `priority_score` deterministically via `LLMService.calculate_priority_score()`.

### 1.5 Unify Tag Normalization Across Zotero, SQLite & Obsidian
- **Files:**
  - [obsidian_service.py](file:///home/tam/github/lit-review/backend/app/services/obsidian_service.py#L161-L166)
  - [index_service.py](file:///home/tam/github/lit-review/backend/app/services/index_service.py#L154)
- **Issue:** `ObsidianService` converts spaces in tags to hyphens (`re.sub(r"\s+", "-", t.strip())`), while `IndexService` stores raw Zotero tags with spaces.
- **Fix:** Normalize tags consistently in one place (or keep Zotero tags intact in YAML lists, since Obsidian YAML frontmatter supports multi-word/hyphenated tags, and normalize consistently when indexing).

---

## Phase 2: Backend Architecture, Error Handling & Missing Endpoints

Focus: Encapsulate file I/O inside services, harden error handling, and expose implemented-but-unreachable backend capabilities.

### 2.1 Move Direct Frontmatter I/O Out of `routers/papers.py` & Support Unsynced Papers
- **Files:**
  - [papers.py](file:///home/tam/github/lit-review/backend/app/routers/papers.py#L74-L122)
  - [obsidian_service.py](file:///home/tam/github/lit-review/backend/app/services/obsidian_service.py)
- **Issues:**
  1. `update_manual_bonus` and `update_paper_status` manipulate `obs.lit_dir / f"@{citekey}.md"` directly using `frontmatter.loads` in the router instead of calling methods on `ObsidianService`.
  2. If a paper in the Reading Queue does not have an Obsidian note yet (`has_obsidian_note == False`), calling `PATCH /api/papers/{citekey}/status` or `/bonus` fails with `404 Not Found`.
- **Fix:** Add `ObsidianService.update_bonus()` and `ObsidianService.update_status()` (and allow creating the note or updating SQLite so unread papers without notes can still be triaged).

### 2.2 Graceful Error Handling in `LLMService`
- **Files:**
  - [llm_service.py](file:///home/tam/github/lit-review/backend/app/services/llm_service.py#L48-L52)
  - [llm_service.py](file:///home/tam/github/lit-review/backend/app/services/llm_service.py#L89-L105)
- **Issues:**
  1. `LLMService.__init__` raises `ValueError` if `GENAI_API_KEY` is missing in the system keyring, causing FastAPI dependency injection to crash with a 500 error.
  2. `_chat_json()` does not handle malformed JSON responses from the model or HTTP timeouts gracefully.
- **Fix:** Validate the API key lazily or raise an appropriate HTTP 503/400 error; add JSON extraction fallback/retry in `_chat_json()`.

### 2.3 Wire Up Contrasting Snippets, Batch Analysis & Citation Refresh
- **Files:**
  - [sync_service.py](file:///home/tam/github/lit-review/backend/app/services/sync_service.py#L154-L177)
  - [sync_service.py](file:///home/tam/github/lit-review/backend/app/services/sync_service.py#L319-L388)
  - [sync.py](file:///home/tam/github/lit-review/backend/app/routers/sync.py)
- **Issues:**
  1. `SciteService.get_contrasting_snippets()` and `ObsidianService`'s `## ⚖️ Scite.ai Contrasting Evidence` section exist, but `SyncService.sync_paper()` and `analyze_paper()` never pass `contrasting_snippets`.
  2. `SyncService.refresh_citations()` and `SyncService.analyze_library()` are only callable via `make citations` / `make analyze` CLI one-liners, not exposed in `routers/sync.py`.
- **Fix:** Fetch contrasting snippets when `scite_metrics["contrasting"] > 0` (and API key is available), and expose `/api/sync/citations` if desired for the UI.

### 2.4 Push SQLite Collection/Tag Filtering into SQL
- **File:** [index_service.py](file:///home/tam/github/lit-review/backend/app/services/index_service.py#L104-L137)
- **Issue:** `IndexService.list_papers()` runs `SELECT * FROM papers`, deserializes JSON for every row in Python, and filters `collection_key` and `tag` in a Python loop.
- **Fix:** Use SQLite `EXISTS (SELECT 1 FROM json_each(papers.collections_json) WHERE value = ?)` and `LIMIT ?` directly in the SQL query.

---

## Phase 3: Frontend UX, Reactivity & Feature Completeness

Focus: Fix stale UI state after sync, improve Markdown rendering in `PaperDetail`, and expose Research Focuses in the UI.

### 3.1 Refresh Reading Queue Automatically After "Sync Now"
- **Files:**
  - [app.ts](file:///home/tam/github/lit-review/frontend/src/app/app.ts#L38-L56)
  - [reading-queue.ts](file:///home/tam/github/lit-review/frontend/src/app/features/reading-queue/reading-queue.ts)
- **Issue:** Clicking **Sync Now** in `App` header calls `api.syncAll()`, but `ReadingQueue` does not reload its data when sync finishes.
- **Fix:** Introduce a shared signal/trigger (e.g., `syncVersion = signal(0)` in `ApiClient` or a state service) so `ReadingQueue` automatically refreshes when a sync completes.

### 3.2 Fix `PaperDetail` Markdown Parser (Sub-bullets, Blockquotes, Personal Notes)
- **Files:**
  - [paper-detail.ts](file:///home/tam/github/lit-review/frontend/src/app/features/paper-detail/paper-detail.ts#L241-L300)
  - [paper-detail.html](file:///home/tam/github/lit-review/frontend/src/app/features/paper-detail/paper-detail.html#L210-L234)
- **Issue:** `parseObsidianMarkdown()` flattens every line in a section into a single-level `<ul><li>` and strips `*` and `**`:
  - Indented sub-bullets in `## 🤖 LLM Analysis` (e.g., `Key Findings:` items) are flattened to the same level as the header bullet.
  - Annotation comments (`> **Note:** ...`) lose their blockquote styling.
  - Free-form paragraphs in `## 📝 My Personal Reading Notes` are rendered as bullet points.
- **Fix:** Preserve line types (`bullet`, `sub-bullet`, `blockquote`, `paragraph`) in `ParsedLine` and render them with appropriate semantics in `paper-detail.html`.

### 3.3 Reliable Zotero `itemKey` Resolution on `PaperDetail`
- **Files:**
  - [paper-detail.ts](file:///home/tam/github/lit-review/frontend/src/app/features/paper-detail/paper-detail.ts#L110-L120)
  - [papers.py](file:///home/tam/github/lit-review/backend/app/routers/papers.py#L62-L71)
- **Issue:** When navigating directly to `/papers/:citekey` without `?key=...`, `resolveItemKey()` fetches the top 500 papers and searches for `citekey`. If the paper is ranked below #500, `itemKey` is `null` and the Sync/Analyze buttons disappear.
- **Fix:** Include the Zotero `key` directly in `PaperDetailResponse` (looked up from `IndexService` by `citekey` or frontmatter).

### 3.4 Add Research Focuses Management UI
- **Files:**
  - [config.py](file:///home/tam/github/lit-review/backend/app/routers/config.py)
  - [api-client.ts](file:///home/tam/github/lit-review/frontend/src/app/core/services/api-client.ts)
- **Issue:** The backend provides `GET/POST/DELETE /api/config/research-focuses`, which drives LLM relevance scoring, but the frontend has no client methods or UI to view/edit research focuses.
- **Fix:** Add Research Focus methods to `ApiClient` and provide a UI panel/dialog to view, add, and delete active research focuses.

### 3.5 Clean Up Broken Tests, Unused CSS & Font Mismatch
- **Files:**
  - [app.spec.ts](file:///home/tam/github/lit-review/frontend/src/app/app.spec.ts)
  - [paper-detail.scss](file:///home/tam/github/lit-review/frontend/src/app/features/paper-detail/paper-detail.scss#L150-L167)
  - [styles.scss](file:///home/tam/github/lit-review/frontend/src/styles.scss#L75-L81) & [index.html](file:///home/tam/github/lit-review/frontend/src/index.html#L11-L18)
- **Issues:**
  - `app.spec.ts` checks for `<h1>Hello, frontend</h1>` and fails due to missing HTTP/Router providers.
  - `paper-detail.scss` has unused `.tags-editor`, `.add-tag-form`, `.tag-input` rules.
  - `styles.scss` uses `'Inter'` while `index.html` loads `Roboto`.

---

## Phase 4: File-by-File Comprehensive Audit (Backend + Frontend + Makefile)

Use this checklist to walk through every active project file one by one, verify its responsibilities, and sign off on its implementation.

### 4.1 Build & Task Automation
- [ ] [Makefile](file:///home/tam/github/lit-review/Makefile)
  - Review targets: `help`, `backend`, `frontend`, `dev`, `sync`, `analyze`, `citations`.
  - Check process cleanup in `make dev` (`trap 'kill 0' SIGINT`), configurable worker count in `make analyze` (`max_workers=6`), and consider adding `make test` / `make lint` / `make index-rebuild` targets.
- [ ] [pyproject.toml](file:///home/tam/github/lit-review/pyproject.toml)
  - Review dependencies, Python version constraint (`>=3.12`), and FastAPI CLI entrypoint (`[tool.fastapi] entrypoint = "app.main:app"`).

### 4.2 Backend (`backend/app/`)
- [ ] [backend/app/config.py](file:///home/tam/github/lit-review/backend/app/config.py)
  - Keyring integration (`lit-review`), `OBSIDIAN_VAULT_PATH` resolution, and `research_focus.json` read/write helpers.
- [ ] [backend/app/main.py](file:///home/tam/github/lit-review/backend/app/main.py)
  - FastAPI app initialization, CORS middleware, router mounting, and `/api/health` endpoint.
- [ ] [backend/app/dependencies.py](file:///home/tam/github/lit-review/backend/app/dependencies.py)
  - `@lru_cache` singleton service factories and `Annotated[..., Depends(...)]` type aliases.
- [ ] [backend/app/models/schemas.py](file:///home/tam/github/lit-review/backend/app/models/schemas.py)
  - Request/response Pydantic models, field types, and validation rules.
- [ ] [backend/app/services/zotero_service.py](file:///home/tam/github/lit-review/backend/app/services/zotero_service.py)
  - Localhost (`23119`) vs. Cloud fallback, pagination, BBT citekey extraction, PDF text extraction, and 5-color annotation mapping.
- [ ] [backend/app/services/scite_service.py](file:///home/tam/github/lit-review/backend/app/services/scite_service.py)
  - Citation tallies (`/tallies/{doi}`) and contrasting snippets (`/citations/{doi}`).
- [ ] [backend/app/services/obsidian_service.py](file:///home/tam/github/lit-review/backend/app/services/obsidian_service.py)
  - Vault folder structure, non-destructive Markdown updates, frontmatter generation, and personal notes preservation.
- [ ] [backend/app/services/llm_service.py](file:///home/tam/github/lit-review/backend/app/services/llm_service.py)
  - Purdue GenAI Studio client, concurrency semaphore, relevance scoring, structured full-text/abstract extraction, and priority score formula.
- [ ] [backend/app/services/index_service.py](file:///home/tam/github/lit-review/backend/app/services/index_service.py)
  - SQLite WAL schema, paper/collection upserts, query filtering, and full rebuild from Zotero + Obsidian.
- [ ] [backend/app/routers/papers.py](file:///home/tam/github/lit-review/backend/app/routers/papers.py)
  - `/api/papers`, `/api/papers/collections`, `/api/papers/{citekey}`, `/bonus`, and `/status` endpoints.
- [ ] [backend/app/routers/sync.py](file:///home/tam/github/lit-review/backend/app/routers/sync.py)
  - `/api/sync`, `/api/sync/{item_key}`, and `/api/sync/{item_key}/analyze` endpoints.
- [ ] [backend/app/routers/config.py](file:///home/tam/github/lit-review/backend/app/routers/config.py)
  - `/api/config/research-focuses` CRUD endpoints.

### 4.3 Frontend (`frontend/`)
- [ ] [frontend/package.json](file:///home/tam/github/lit-review/frontend/package.json) & [frontend/angular.json](file:///home/tam/github/lit-review/frontend/angular.json)
  - Scripts, Angular v22 dependencies, build budgets, and dev server proxy configuration.
- [ ] [frontend/src/index.html](file:///home/tam/github/lit-review/frontend/src/index.html) & [frontend/src/styles.scss](file:///home/tam/github/lit-review/frontend/src/styles.scss)
  - Material 3 theme definition, Google Fonts loading, and global CSS custom properties.
- [ ] [frontend/src/main.ts](file:///home/tam/github/lit-review/frontend/src/main.ts), [frontend/src/app/app.config.ts](file:///home/tam/github/lit-review/frontend/src/app/app.config.ts), [frontend/src/app/app.routes.ts](file:///home/tam/github/lit-review/frontend/src/app/app.routes.ts)
  - Application bootstrap, providers (`provideRouter`, `provideHttpClient`), and route definitions.
- [ ] [frontend/src/app/core/models/paper.model.ts](file:///home/tam/github/lit-review/frontend/src/app/core/models/paper.model.ts)
  - TypeScript interfaces matching backend Pydantic schemas.
- [ ] [frontend/src/app/core/services/api-client.ts](file:///home/tam/github/lit-review/frontend/src/app/core/services/api-client.ts)
  - HTTP methods for health, papers, collections, bonus/status updates, sync, and LLM analysis.
- [ ] [frontend/src/app/app.ts](file:///home/tam/github/lit-review/frontend/src/app/app.ts), [app.html](file:///home/tam/github/lit-review/frontend/src/app/app.html), [app.scss](file:///home/tam/github/lit-review/frontend/src/app/app.scss), [app.spec.ts](file:///home/tam/github/lit-review/frontend/src/app/app.spec.ts)
  - Top app shell, Zotero connection badge, and global "Sync Now" button.
- [ ] [frontend/src/app/features/reading-queue/reading-queue.ts](file:///home/tam/github/lit-review/frontend/src/app/features/reading-queue/reading-queue.ts), [reading-queue.html](file:///home/tam/github/lit-review/frontend/src/app/features/reading-queue/reading-queue.html), [reading-queue.scss](file:///home/tam/github/lit-review/frontend/src/app/features/reading-queue/reading-queue.scss)
  - Unread KPI card, interactive priority-score histogram, filter toolbar, paginated Material table, and inline bonus controls.
- [ ] [frontend/src/app/features/paper-detail/paper-detail.ts](file:///home/tam/github/lit-review/frontend/src/app/features/paper-detail/paper-detail.ts), [paper-detail.html](file:///home/tam/github/lit-review/frontend/src/app/features/paper-detail/paper-detail.html), [paper-detail.scss](file:///home/tam/github/lit-review/frontend/src/app/features/paper-detail/paper-detail.scss)
  - Paper metadata header, Scite citation breakdown, read/unread toggle, single-paper sync/LLM triggers, and Obsidian Markdown section parser/renderer.
