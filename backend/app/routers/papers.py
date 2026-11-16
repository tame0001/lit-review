"""Papers & Reading List API routes."""

import frontmatter
from fastapi import APIRouter, Depends, HTTPException, Query
from ..dependencies import get_zotero_service, get_obsidian_service, get_sync_service
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
def list_collections(zot: ZoteroService = Depends(get_zotero_service)):
    """List all Zotero collections."""
    return zot.get_collections()


@router.get("", response_model=list[PaperSummary])
def list_papers(
    collection_key: str | None = Query(default=None, description="Filter by Zotero collection key"),
    tag: str | None = Query(default=None, description="Filter by Zotero tag"),
    status: str | None = Query(default=None, description="Filter by 'read' or 'unread' (based on Obsidian note)"),
    limit: int = Query(default=2000, ge=1, le=10000),
    zot: ZoteroService = Depends(get_zotero_service),
    obs: ObsidianService = Depends(get_obsidian_service),
):
    """List papers from Zotero, enriched with Obsidian note status, priority score, and LLM metadata."""
    papers = zot.get_read_papers(collection_key=collection_key, tag=tag, limit=limit)
    results: list[PaperSummary] = []

    for p in papers:
        note = obs.get_literature_note(p["citekey"])
        has_note = note is not None
        meta = note.get("metadata", {}) if note else {}
        paper_status = meta.get("status", "unread")

        if status == "read" and paper_status != "read":
            continue
        if status == "unread" and paper_status != "unread":
            continue

        analyzed_at = meta.get("llm_analyzed_at")
        results.append(
            PaperSummary(
                **p,
                has_obsidian_note=has_note,
                status=paper_status,
                priority_score=float(meta.get("priority_score", 0.0) or 0.0),
                manual_bonus=float(meta.get("manual_bonus", 0.0) or 0.0),
                llm_analyzed=bool(meta.get("llm_analyzed", False)),
                llm_analyzed_at=str(analyzed_at) if analyzed_at else None,
                llm_source=str(meta.get("llm_source", "neither")),
                scite_total_citations=int(meta.get("scite_total_citations", 0) or 0),
            )
        )

    results.sort(key=lambda item: item.priority_score, reverse=True)
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


@router.patch("/{citekey}/bonus", response_model=BonusUpdateResponse)
def update_manual_bonus(
    citekey: str,
    payload: BonusUpdateRequest,
    obs: ObsidianService = Depends(get_obsidian_service),
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
):
    """Manually mark a paper as 'read' or 'unread' (persists across future syncs)."""
    note_path = obs.lit_dir / f"@{citekey}.md"
    if not note_path.exists():
        raise HTTPException(status_code=404, detail=f"Obsidian note for '@{citekey}' not found.")

    post = frontmatter.loads(note_path.read_text(encoding="utf-8", errors="ignore"))
    post.metadata["status"] = payload.status
    post.metadata["status_override"] = payload.status
    note_path.write_text(frontmatter.dumps(post) + "\n", encoding="utf-8")

    return StatusUpdateResponse(citekey=citekey, status=payload.status)
