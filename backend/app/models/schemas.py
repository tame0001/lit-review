"""Pydantic schemas for FastAPI request and response models."""

from typing import Any, Literal
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    zotero_mode: str
    zotero_local_available: bool
    obsidian_vault_exists: bool
    obsidian_vault_path: str


class CollectionItem(BaseModel):
    key: str
    name: str
    parent_key: str | None = None


class PaperSummary(BaseModel):
    key: str
    version: int | None = None
    citekey: str
    title: str
    authors: list[str] = []
    author_short: str | None = None
    year: int | None = None
    doi: str | None = None
    publication: str | None = None
    tags: list[str] = []
    collections: list[str] = []
    has_obsidian_note: bool = False
    status: str = "unread"
    priority_score: float = 0.0
    manual_bonus: float = 0.0
    llm_analyzed: bool = False
    llm_analyzed_at: str | None = None
    llm_source: str = "neither"
    scite_total_citations: int = 0


class BonusUpdateRequest(BaseModel):
    manual_bonus: float = Field(..., description="New manual bonus score adjustment")


class BonusUpdateResponse(BaseModel):
    citekey: str
    manual_bonus: float
    priority_score: float


class StatusUpdateRequest(BaseModel):
    status: Literal["read", "unread"]


class StatusUpdateResponse(BaseModel):
    citekey: str
    status: str


class PaperDetailResponse(BaseModel):
    citekey: str
    metadata: dict[str, Any]
    content: str
    path: str


class SyncPaperResult(BaseModel):
    key: str
    citekey: str
    status: str
    highlights: int
    path: str | None = None


class SyncAllResponse(BaseModel):
    previous_version: int | None = None
    new_version: int
    changed_raw_items: int
    affected_papers: int
    results: list[SyncPaperResult]


class AnalyzePaperResult(BaseModel):
    key: str
    citekey: str
    status: str
    priority_score: float = 0.0
    llm_source: str = "neither"
    path: str | None = None
