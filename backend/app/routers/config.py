"""Configuration API routes (Multiple Research Focuses management)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..config import settings

router = APIRouter(prefix="/api/config", tags=["config"])


class ResearchFocusItem(BaseModel):
    id: str
    title: str
    description: str = ""
    active: bool = True


class ResearchFocusListResponse(BaseModel):
    focuses: list[ResearchFocusItem]
    updated_at: str


class ResearchFocusCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, description="Short title of the research topic")
    description: str = Field(default="", description="Details/questions to guide LLM scoring")


@router.get("/research-focuses", response_model=ResearchFocusListResponse)
def list_research_focuses(active_only: bool = False):
    """List all active (or all) research focuses stored in research_focus.json."""
    return ResearchFocusListResponse(**settings.get_research_focuses(active_only=active_only))


@router.post("/research-focuses", response_model=ResearchFocusListResponse)
def add_research_focus(payload: ResearchFocusCreateRequest):
    """Add or update a research focus."""
    return ResearchFocusListResponse(**settings.add_research_focus(payload.title, payload.description))


@router.delete("/research-focuses/{focus_id}", response_model=ResearchFocusListResponse)
def remove_research_focus(focus_id: str):
    """Remove a completed research focus by ID."""
    before = settings.get_research_focuses()["focuses"]
    if not any(f.get("id") == focus_id for f in before):
        raise HTTPException(status_code=404, detail=f"Research focus '{focus_id}' not found.")
    return ResearchFocusListResponse(**settings.remove_research_focus(focus_id))
