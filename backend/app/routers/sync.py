"""Sync API routes."""

from fastapi import APIRouter, Depends, Query
from ..dependencies import get_sync_service
from ..services.sync_service import SyncService
from ..models.schemas import SyncAllResponse, SyncPaperResult

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("", response_model=SyncAllResponse)
def sync_all_changes(
    force_full: bool = Query(default=False, description="Force full re-sync ignoring last saved version"),
    sync: SyncService = Depends(get_sync_service),
):
    """Trigger incremental delta sync (or full sync) from Zotero -> Scite -> Obsidian."""
    return SyncAllResponse(**sync.sync_all_changes(force_full=force_full))


@router.post("/{item_key}", response_model=SyncPaperResult)
def sync_single_paper(
    item_key: str,
    force: bool = Query(default=False, description="Force note creation even if paper has 0 highlights"),
    sync: SyncService = Depends(get_sync_service),
):
    """Sync an individual paper by Zotero item key."""
    return SyncPaperResult(**sync.sync_paper(item_key, force=force))
