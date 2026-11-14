"""
FastAPI Backend Application
---------------------------
Run locally:
    uvicorn app.main:app --app-dir backend --reload --port 8000
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .dependencies import get_zotero_service, get_obsidian_service
from .services.zotero_service import ZoteroService
from .services.obsidian_service import ObsidianService
from .models.schemas import HealthResponse
from .routers import papers, sync, config

app = FastAPI(
    title="Literature Review Cockpit API",
    description="Backend API bridging Zotero, Scite.ai, and Obsidian.",
    version="0.1.0",
)

# Enable CORS for local Angular development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers.router)
app.include_router(sync.router)
app.include_router(config.router)


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health_check(
    zot: ZoteroService = Depends(get_zotero_service),
    obs: ObsidianService = Depends(get_obsidian_service),
):
    """Check API health, Zotero localhost/cloud mode, and Obsidian vault availability."""
    status = zot.refresh_connection_status()
    return HealthResponse(
        status="ok",
        zotero_mode=status["mode"],
        zotero_local_available=status["local_available"],
        obsidian_vault_exists=obs.vault_path.exists(),
        obsidian_vault_path=str(obs.vault_path),
    )
