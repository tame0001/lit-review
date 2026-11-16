"""Papers & Reading List API routes."""

import frontmatter
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import (
    get_index_service,
    get_obsidian_service,
    get_sync_service,
    get_zotero_service,
)
from ..services.index_service import IndexService
from ..services.zotero_service import ZoteroService
from ..services.obsidian_service import ObsidianService
from ..services.sync_service import SyncService
from ..models.schemas import (
    BonusUpdateRequest,
    BonusUpdateResponse,
    CollectionItem,
    PaperSummary,
    PaperDetailResponse,
    StatusUpdateRequest,
    StatusUpdateResponse,
    TagUpdateRequest,
    TagUpdateResponse,
)

router = APIRouter(prefix="/api/papers", tags=["papers"])


@router.get("/collections", response_model=list[CollectionItem])
def list_collections(
    zot: ZoteroService = Depends(get_zotero_service),
    idx: IndexService = Depends(get_index_service),
):
    """List all Zotero collections (served from SQLite index; auto-populated if empty)."""
    if idx.count_collections() == 0:
        cols = zot.get_collections()
        idx.replace_collections(cols)
        return cols
    return idx.list_collections()


@router.get("", response_model=list[PaperSummary])
def list_papers(
    collection_key: str | None = Query(default=None, description="Filter by Zotero collection key"),
    tag: str | None = Query(default=None, description="Filter by Zotero tag"),
    status: str | None = Query(default=None, description="Filter by 'read' or 'unread' (based on Obsidian note)"),
    limit: int = Query(default=2000, ge=1, le=10000),
    zot: ZoteroService = Depends(get_zotero_service),
    obs: ObsidianService = Depends(get_obsidian_service),
    idx: IndexService = Depends(get_index_service),
):
    """List papers from the SQLite index (auto-populates from Zotero + Obsidian on first run)."""
    if idx.count_papers() == 0:
        idx.rebuild_from_sources(zot, obs)

    rows = idx.list_papers(
        collection_key=collection_key,
        tag=tag,
        status=status,
        limit=limit,
    )
    return [PaperSummary(**row) for row in rows]


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


@router.patch("/{citekey}/bonus", response_model=BonusUpdateResponse)
def update_manual_bonus(
    citekey: str,
    payload: BonusUpdateRequest,
    obs: ObsidianService = Depends(get_obsidian_service),
    idx: IndexService = Depends(get_index_service),
):
    """Adjust manual_bonus in an Obsidian note and recalculate its priority_score."""
    note_path = obs.lit_dir / f"@{citekey}.md"
    if not note_path.exists():
        raise HTTPException(status_code=404, detail=f"Obsidian note for '@{citekey}' not found.")

    post = frontmatter.loads(note_path.read_text(encoding="utf-8", errors="ignore"))
    old_bonus = float(post.metadata.get("manual_bonus", 0.0) or 0.0)
    old_score = float(post.metadata.get("priority_score", 0.0) or 0.0)
    new_bonus = round(payload.manual_bonus, 1)
    new_score = round(old_score - old_bonus + new_bonus, 1)

    post.metadata["manual_bonus"] = new_bonus
    post.metadata["priority_score"] = new_score
    note_path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    idx.update_bonus(citekey, new_bonus, new_score)

    return BonusUpdateResponse(
        citekey=citekey,
        manual_bonus=new_bonus,
        priority_score=new_score,
    )


@router.patch("/{citekey}/status", response_model=StatusUpdateResponse)
def update_paper_status(
    citekey: str,
    payload: StatusUpdateRequest,
    obs: ObsidianService = Depends(get_obsidian_service),
    idx: IndexService = Depends(get_index_service),
):
    """Manually mark a paper as 'read' or 'unread' (persists across future syncs)."""
    note_path = obs.lit_dir / f"@{citekey}.md"
    if not note_path.exists():
        raise HTTPException(status_code=404, detail=f"Obsidian note for '@{citekey}' not found.")

    post = frontmatter.loads(note_path.read_text(encoding="utf-8", errors="ignore"))
    post.metadata["status"] = payload.status
    post.metadata["status_override"] = payload.status
    note_path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")
    idx.update_status(citekey, payload.status)

    return StatusUpdateResponse(citekey=citekey, status=payload.status)
