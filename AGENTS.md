# AGENTS.md

You are an expert software developer assisting the project owner in building and maintaining this system.

## Docs

Read **[README.md](README.md)** first for architecture, repo map, setup, and `make` commands.
- Backend API: **[backend/README.md](backend/README.md)**
- Frontend stack & Angular rules: **[frontend/README.md](frontend/README.md)**, **[frontend/AGENTS.md](frontend/AGENTS.md)**
- Refactoring backlog: **[CODE_AUDIT.md](CODE_AUDIT.md)**

## Workflow

1. **Propose before coding:** Present a brief change summary (files, behavior changes, open questions) and get alignment before editing code.
2. **Backend (`backend/`):** FastAPI. Follow `.agents/skills/fastapi/SKILL.md`. Use `uv run` (never global `python3`), keep routers thin, and use sync `def` routes for blocking I/O (`httpx2`, `sqlite3`, `pypdf`).
3. **Frontend (`frontend/`):** Angular + Angular Material. Follow `.agents/skills/angular-developer/SKILL.md` and **[frontend/AGENTS.md](frontend/AGENTS.md)**.
4. **Verify before finishing:**
   - Backend: `uv run ruff check backend`, `uv run ruff format backend`, `uv run pyright`
   - Frontend (in `frontend/`): `npm run lint`, `npm run format`, `npm run build`

## Invariants

1. **Zotero owns tags:** Never add LLM-generated tags or web-UI tag editing.
2. **Preserve user data on sync:** Never overwrite `## 📝 My Personal Reading Notes`, `manual_bonus`, or `status_override` in `@citekey.md`.
3. **Skip analyzed papers:** Do not re-run LLM analysis when `llm_analyzed: true` unless `force=True`.
4. **Keyring secrets only:** Keep API keys (`ZOTERO_LIBRARY_ID`, `ZOTERO_API_KEY`, `SCITE_API_KEY`, `GENAI_API_KEY`) in Linux keyring (`lit-review`); never hardcode or commit them.
5. **Zotero localhost API:** Always paginate `items` (`_local_get_paginated`) and fetch highlights via `items?itemType=annotation` (not `/items/{pdf_key}/children`).
6. **Purdue GenAI:** Set `"Accept-Encoding": "gzip, deflate"` on `httpx2.Client` and cap workers (`<= 10`, `6` for batches) to stay under 20 req/min.
