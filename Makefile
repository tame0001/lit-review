.PHONY: help backend frontend dev sync analyze citations

help:
	@echo "Available commands:"
	@echo "  make backend    - Start FastAPI backend server (http://localhost:8000)"
	@echo "  make frontend   - Start Angular frontend dev server (http://localhost:4200)"
	@echo "  make dev        - Run both backend and frontend concurrently"
	@echo "  make sync       - Run Zotero -> Scite -> Obsidian incremental delta sync"
	@echo "  make analyze    - Run LLM pipeline on unanalyzed papers"
	@echo "  make citations  - Refresh Scite citation counts and recalculate priority scores"

backend:
	uv run uvicorn app.main:app --app-dir backend --reload --port 8000

frontend:
	@if [ ! -d "frontend" ]; then \
		echo "Error: 'frontend/' directory does not exist yet. Scaffold Angular first."; \
		exit 1; \
	fi
	cd frontend && npm start

dev:
	@if [ ! -d "frontend" ]; then \
		echo "Frontend not scaffolded yet; starting backend only..."; \
		$(MAKE) backend; \
	else \
		trap 'kill 0' SIGINT; \
		$(MAKE) backend & \
		$(MAKE) frontend & \
		wait; \
	fi

sync:
	PYTHONPATH=backend uv run python -c "from app.services.sync_service import SyncService; print(SyncService().sync_all_changes())"

analyze:
	PYTHONPATH=backend uv run python -c "from collections import Counter; from app.services.sync_service import SyncService; from app.services.llm_service import LLMService; res = SyncService().analyze_library(LLMService(), force=False, max_workers=6); print('Summary:', dict(Counter(r['status'] for r in res)))"

citations:
	PYTHONPATH=backend uv run python -c "from app.services.sync_service import SyncService; print(SyncService().refresh_citations())"
