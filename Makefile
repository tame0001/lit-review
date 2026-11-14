.PHONY: help backend frontend dev sync

help:
	@echo "Available commands:"
	@echo "  make backend   - Start FastAPI backend server (http://localhost:8000)"
	@echo "  make frontend  - Start Angular frontend dev server (http://localhost:4200)"
	@echo "  make dev       - Run both backend and frontend concurrently"
	@echo "  make sync      - Run Zotero -> Scite -> Obsidian incremental delta sync"

backend:
	python3 -m uvicorn app.main:app --app-dir backend --reload --port 8000

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
	PYTHONPATH=backend python3 -c "from app.services.sync_service import SyncService; print(SyncService().sync_all_changes())"
