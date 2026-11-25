# Backend (FastAPI)

FastAPI service bridging Zotero, Scite.ai, Purdue GenAI Studio, Obsidian, and the local SQLite read index (`.lit_review_index.db`).

## Running Locally

From the repository root:

```bash
make backend
# or:
uv run uvicorn app.main:app --app-dir backend --reload --port 8000
```

Interactive OpenAPI docs are available at `http://localhost:8000/docs`.

## Services (`backend/app/services/`)

- `zotero_service.py` — Zotero Localhost API (`http://localhost:23119/api`, paginated) with Cloud API fallback.
- `scite_service.py` — Scite.ai citation tallies (`supporting`, `contrasting`, `mentioning`, `total`) and contrasting snippets.
- `llm_service.py` — Purdue GenAI Studio (`qwen3.8:27b`) relevance scoring + structured extraction (`analyze_paper_content()`), priority scoring, and concurrency-capped parallel execution.
- `obsidian_service.py` — Reads and non-destructively updates `@citekey.md` notes in `obsidian/01-Literature/`.
- `index_service.py` — SQLite WAL read-cache (`.lit_review_index.db`) for fast UI queries.
- `sync_service.py` — Orchestrates incremental delta sync, single-paper sync, parallel LLM analysis, and citation refreshes.

## Full API Endpoint Reference

### System
- `GET /api/health` — Backend status, Zotero localhost/cloud availability, and Obsidian vault check.

### Papers (`backend/app/routers/papers.py`)
- `GET /api/papers` — List ranked papers from SQLite index (`collection_key`, `tag`, `status`, `limit` up to `10000`).
- `GET /api/papers/collections` — List Zotero collections.
- `GET /api/papers/{citekey}` — Retrieve parsed Obsidian note (`metadata`, `content`, `path`).
- `PATCH /api/papers/{citekey}/bonus` — Update `manual_bonus` and recalculate `priority_score` in Obsidian + SQLite.
- `PATCH /api/papers/{citekey}/status` — Set persistent `status` (`read` or `unread`) with `status_override`.

### Sync & LLM (`backend/app/routers/sync.py`)
- `POST /api/sync` — Run incremental Zotero → Scite → Obsidian + SQLite delta sync (`force_full=false`).
- `POST /api/sync/{item_key}` — Sync a single Zotero paper and recalculate citation-weighted `priority_score` (`force=false`).
- `POST /api/sync/{item_key}/analyze` — Run LLM relevance scoring + insight extraction for a single paper (`force=false`).

### Research Focus Config (`backend/app/routers/config.py`)
- `GET /api/config/research-focuses` — List active/all research focuses from `research_focus.json` (`active_only=false`).
- `POST /api/config/research-focuses` — Add a new research focus (`title`, `description`).
- `DELETE /api/config/research-focuses/{focus_id}` — Remove a completed research focus.
