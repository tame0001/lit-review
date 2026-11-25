# AGENTS.md

You are an expert software developer assisting the project owner in designing, building, and maintaining this Literature Review Cockpit system.

## Project Context & Documentation

Before planning or editing code, read **[README.md](README.md)** for the system summary, architecture, repository map, setup, and common `make` commands.
- Backend API reference: **[backend/README.md](backend/README.md)**
- Frontend conventions & Angular rules: **[frontend/AGENTS.md](frontend/AGENTS.md)** and **[frontend/README.md](frontend/README.md)**
- Open audit & refactoring backlog: **[CODE_AUDIT.md](CODE_AUDIT.md)**

## Development Workflow

- **Propose before coding:** Before making code changes, present a concise change summary (files to touch, behavior changes, and any open questions) and align with the project owner.
- **Tech Stack & Skills:**
  - **Backend (`backend/`):** Uses **FastAPI** (Python). Follow the `fastapi` skill (`.agents/skills/fastapi/SKILL.md`), use `uv run` / `.venv/bin/python` (never global `python3`), keep route handlers thin, and use synchronous `def` routes for blocking I/O (`httpx2`, `sqlite3`, `pypdf`).
  - **Frontend (`frontend/`):** Uses **Angular** with **Angular Material**. Follow the `angular-developer` skill (`.agents/skills/angular-developer/SKILL.md`) and **[frontend/AGENTS.md](frontend/AGENTS.md)**.
- **Linting & Formatting Before Finishing:**
  - **Backend (`backend/`):** Run `uv run ruff check backend` and `uv run ruff format backend` (or `--check`).
  - **Frontend (`frontend/`):** Run `npm run lint` (`angular-eslint`) and `npm run format` (or `npm run format:check` with Prettier) inside `frontend/`.

## Critical Invariants (Do Not Break)

1. **Zotero is the single source of truth for tags.** Never add LLM-generated tags or web-UI tag-editing endpoints.
2. **Preserve user data on re-sync:** Never overwrite `## 📝 My Personal Reading Notes`, `manual_bonus`, or `status_override` in Obsidian `@citekey.md` notes.
3. **Skip already-analyzed papers:** Never re-run LLM analysis on papers where `llm_analyzed: true` unless `force=True` is explicitly requested.
4. **Secrets stay in Linux keyring (`lit-review` service):** Never hardcode or commit API keys (`ZOTERO_LIBRARY_ID`, `ZOTERO_API_KEY`, `SCITE_API_KEY`, `GENAI_API_KEY`).
5. **Zotero Localhost API quirks:** Always paginate `items` (`_local_get_paginated`) and query `items?itemType=annotation` (not `/items/{pdf_key}/children`) for PDF highlights.
6. **Purdue GenAI quirks:** Keep `"Accept-Encoding": "gzip, deflate"` on `httpx2.Client` and cap parallel workers (`<= 10`, recommended `6` for large batches) to stay under the 20 req/min limit.
