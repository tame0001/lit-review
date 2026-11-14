"""Shared FastAPI dependencies for backend services."""

from functools import lru_cache
from .services.zotero_service import ZoteroService
from .services.scite_service import SciteService
from .services.obsidian_service import ObsidianService
from .services.sync_service import SyncService


@lru_cache
def get_zotero_service() -> ZoteroService:
    return ZoteroService()


@lru_cache
def get_scite_service() -> SciteService:
    return SciteService()


@lru_cache
def get_obsidian_service() -> ObsidianService:
    return ObsidianService()


@lru_cache
def get_sync_service() -> SyncService:
    return SyncService(
        zotero_service=get_zotero_service(),
        scite_service=get_scite_service(),
        obsidian_service=get_obsidian_service(),
    )
