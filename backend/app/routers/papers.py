"""Papers & Reading List API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_zotero_service, get_obsidian_service, get_sync_service
from ..services.zotero_service import ZoteroService
from ..services.obsidian_service import ObsidianService
from ..services.sync_service import SyncService
from ..models.schemas import (
    CollectionItem,
    PaperSummary,
    PaperDetailResponse,
    TagUpdateRequest,
    TagUpdateResponse,
)

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.get("/collections", response_model=list[CollectionItem])
def list_collections(zot: ZoteroService = Depends(get_zotero_service)):
    """List all Zotero collections."""
    return zot.get_collections()


@router.get("", response_model=list[PaperSummary])
def list_papers(
    collection_key: str | None = Query(default=None, description="Filter by Zotero collection key"),
    tag: str | None = Query(default=None, description="Filter by Zotero tag"),
    status: str | None = Query(default=None, description="Filter by 'read' or 'unread' (based on Obsidian note)"),
    limit: int = Query(default=50, ge=1, le=500),
    zot: ZoteroService = Depends(get_zotero_service),
    obs: ObsidianService = Depends(get_obsidian_service),
):
    """List papers from Zotero, enriched with whether an Obsidian note exists."""
    papers = zot.get_read_papers(collection_key=collection_key, tag=tag, limit=limit)
    results: list[PaperSummary] = []

    for p in papers:
        has_note = obs.note_exists(p["citekey"])
        if status == "read" and not has_note:
            continue
        if status == "unread" and has_note:
            continue
        results.append(PaperSummary(**p, has_obsidian_note=has_note))

    return results


@router.get("/{citekey}", response_model=PaperDetailResponse)
def get_paper_note(
    citekey: str,
    obs: ObsidianService = Depends(get_obsidian_service),
):
    """Retrieve the parsed Obsidian note (frontmatter + markdown body) for a paper."""
    note = obs.get_literature_note(citekey)
    if not note:
        raise HTTPException(status_code=404, detail=f"Obsidian note for '@{citekey}' not found.")
    return PaperDetailResponse(**note)


@router.post("/{item_key}/tags", response_model=TagUpdateResponse)
def add_tags_to_paper(
    item_key: str,
    payload: TagUpdateRequest,
    sync: SyncService = Depends(get_sync_service),
):
    """Add tags to a Zotero item and immediately re-sync its Obsidian note."""
    result = sync.sync_tags_to_zotero(item_key, payload.tags)
    return TagUpdateResponse(**result)
