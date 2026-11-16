"""
Sync Service
------------
Orchestrates incremental synchronization between Zotero, Scite.ai, and Obsidian.

Key Capabilities:
1. Delta Sync (`sync_all_changes`):
   - Uses Zotero's `Last-Modified-Version` and `?since=` API to fetch ONLY items
     and annotations added or modified since the last sync (< 50 ms even for 1,000+ papers).
   - Resolves parent papers from modified PDF annotations (catching re-reads).
   - Skips unchanged papers and unread papers with 0 highlights.

2. Individual Paper Sync (`sync_paper`):
   - Syncs a single paper by Zotero key (used by Delta Sync and Web App endpoints).
   - Preserves existing Scite tallies if already fetched unless `force=True`.

3. Bidirectional Tag Sync (`sync_tags_to_zotero`):
   - Pushes tags added in the Web App directly to Zotero, then updates the
     corresponding Obsidian note so Zotero remains the single source of truth.
"""

import json
from pathlib import Path
from typing import Any
from ..config import REPO_ROOT, settings
from .zotero_service import ZoteroService
from .scite_service import SciteService
from .obsidian_service import ObsidianService
from .llm_service import LLMService
from .index_service import IndexService


class SyncService:
    EXCLUDED_ITEM_TYPES = {"attachment", "note", "annotation"}

    def __init__(
        self,
        zotero_service: ZoteroService | None = None,
        scite_service: SciteService | None = None,
        obsidian_service: ObsidianService | None = None,
        index_service: IndexService | None = None,
        state_path: str | Path | None = None,
    ):
        self.zot = zotero_service or ZoteroService()
        self.scite = scite_service or SciteService()
        self.obs = obsidian_service or ObsidianService()
        self.idx = index_service or IndexService()
        self.state_path = Path(state_path) if state_path else (REPO_ROOT / ".sync_state.json")

    # -------------------------------------------------------------------------
    # Sync State Persistence
    # -------------------------------------------------------------------------
    def _load_state(self) -> dict[str, Any]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"last_library_version": None}

    def _save_state(self, state: dict[str, Any]) -> None:
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # -------------------------------------------------------------------------
    # Parent Resolution for Delta Items
    # -------------------------------------------------------------------------
    def _resolve_affected_paper_keys(self, changed_items: list[dict[str, Any]]) -> set[str]:
        """
        Given raw Zotero items modified since last sync (papers, attachments, annotations),
        resolve the set of top-level Paper keys that need to be checked/synced.
        """
        paper_keys: set[str] = set()
        # Cache parent lookups during this batch to avoid duplicate HTTP requests
        item_cache: dict[str, dict[str, Any]] = {
            item["key"]: item for item in changed_items if "key" in item
        }

        def get_cached_item(key: str) -> dict[str, Any] | None:
            if key not in item_cache:
                try:
                    item_cache[key] = self.zot.get_item_raw(key)
                except Exception:
                    return None
            return item_cache[key]

        for item in changed_items:
            data = item.get("data", {})
            item_type = data.get("itemType")
            key = item.get("key")

            if not key or not item_type:
                continue

            if item_type not in self.EXCLUDED_ITEM_TYPES:
                paper_keys.add(key)
            elif item_type == "annotation":
                # Annotation -> PDF Attachment -> Paper
                pdf_key = data.get("parentItem")
                if pdf_key:
                    pdf_item = get_cached_item(pdf_key)
                    if pdf_item:
                        parent_paper_key = pdf_item.get("data", {}).get("parentItem")
                        if parent_paper_key:
                            paper_keys.add(parent_paper_key)
            elif item_type in ("attachment", "note"):
                parent_key = data.get("parentItem")
                if parent_key:
                    parent_item = get_cached_item(parent_key)
                    if parent_item and parent_item.get("data", {}).get("itemType") not in self.EXCLUDED_ITEM_TYPES:
                        paper_keys.add(parent_key)

        return paper_keys

    # -------------------------------------------------------------------------
    # Public Sync Methods
    # -------------------------------------------------------------------------
    def _upsert_paper_index(self, paper: dict[str, Any]) -> None:
        note = self.obs.get_literature_note(paper["citekey"])
        obs_meta = note.get("metadata") if note else None
        self.idx.upsert_paper(self.idx.build_summary_record(paper, obs_meta))

    def sync_paper(self, paper_key: str, force: bool = False) -> dict[str, Any]:
        """
        Sync an individual paper from Zotero -> Scite -> Obsidian.
        Skips generating an Obsidian note if the paper has 0 highlights unless `force=True`.
        """
        paper = self.zot.get_paper_metadata(paper_key)
        annotations = self.zot.get_pdf_annotations(paper_key)

        if not annotations and not force:
            self._upsert_paper_index(paper)
            return {
                "key": paper_key,
                "citekey": paper["citekey"],
                "status": "skipped_unread",
                "highlights": 0,
            }

        # Reuse existing Scite tallies from Obsidian frontmatter if already present (unless force=True)
        scite_metrics = None
        existing_note = self.obs.get_literature_note(paper["citekey"])
        if existing_note and not force:
            meta = existing_note.get("metadata", {})
            if "scite_supporting" in meta:
                scite_metrics = {
                    "supporting": meta.get("scite_supporting", 0),
                    "contrasting": meta.get("scite_contrasting", 0),
                    "mentioning": meta.get("scite_mentioning", 0),
                }

        if scite_metrics is None:
            scite_metrics = self.scite.get_tallies(paper.get("doi"))

        note_path = self.obs.create_or_update_literature_note(
            paper_metadata=paper,
            annotations=annotations,
            scite_metrics=scite_metrics,
        )
        self._upsert_paper_index(paper)

        return {
            "key": paper_key,
            "citekey": paper["citekey"],
            "status": "updated" if existing_note else "created",
            "highlights": len(annotations),
            "path": str(note_path),
        }

    def sync_all_changes(self, force_full: bool = False) -> dict[str, Any]:
        """
        Incremental delta sync using Zotero's `?since=` version tracking.
        Only processes papers that were added, edited, or received new highlights.
        """
        state = self._load_state()
        since_version = None if force_full else state.get("last_library_version")

        changed_items, new_version = self.zot.get_changes_since(since_version)
        affected_keys = self._resolve_affected_paper_keys(changed_items)

        results: list[dict[str, Any]] = []
        for key in sorted(affected_keys):
            results.append(self.sync_paper(key, force=force_full))

        if force_full or changed_items:
            self.idx.replace_collections(self.zot.get_collections())

        self._save_state({"last_library_version": new_version})

        return {
            "previous_version": since_version,
            "new_version": new_version,
            "changed_raw_items": len(changed_items),
            "affected_papers": len(affected_keys),
            "results": results,
        }

    def sync_tags_to_zotero(self, paper_key: str, tags: list[str]) -> dict[str, Any]:
        """
        Add tags to a Zotero paper (e.g. from the Web App) and immediately
        re-sync its Obsidian note so Zotero remains the single source of truth.
        """
        added_tags: list[str] = []
        for tag in tags:
            clean_tag = tag.strip()
            if clean_tag and self.zot.add_tag_to_item(paper_key, clean_tag):
                added_tags.append(clean_tag)

        # Refresh local sync for this paper so Obsidian frontmatter reflects the new tags
        sync_result = self.sync_paper(paper_key, force=True)
        return {
            "paper_key": paper_key,
            "tags_synced": added_tags,
            "obsidian_sync": sync_result,
        }

    def analyze_paper(
        self,
        paper_key: str,
        llm: LLMService,
        research_focuses: list[dict[str, Any]] | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """
        Score relevance, extract structured insights (full-text preferred, abstract fallback),
        and update the Obsidian literature note. Skips papers already marked `llm_analyzed: true`
        unless `force=True`.
        """
        if research_focuses is None:
            research_focuses = settings.get_research_focuses(active_only=True)["focuses"]

        paper = self.zot.get_paper_metadata(paper_key)
        citekey = paper["citekey"]

        if self.obs.is_llm_analyzed(citekey) and not force:
            existing = self.obs.get_literature_note(citekey) or {}
            meta = existing.get("metadata", {})
            return {
                "key": paper_key,
                "citekey": citekey,
                "status": "skipped_already_analyzed",
                "priority_score": meta.get("priority_score", 0.0),
                "llm_source": meta.get("llm_source", "neither"),
            }

        annotations = self.zot.get_pdf_annotations(paper_key)
        existing_note = self.obs.get_literature_note(citekey)
        existing_meta = existing_note.get("metadata", {}) if existing_note else {}

        if "scite_supporting" in existing_meta and "scite_total_citations" in existing_meta and not force:
            scite_metrics = {
                "supporting": existing_meta.get("scite_supporting", 0),
                "contrasting": existing_meta.get("scite_contrasting", 0),
                "mentioning": existing_meta.get("scite_mentioning", 0),
                "total": existing_meta.get("scite_total_citations", 0),
            }
        else:
            scite_metrics = self.scite.get_tallies(paper.get("doi"))

        full_text = self.zot.get_pdf_full_text(paper_key)
        abstract = paper.get("abstract") or ""
        if full_text and len(full_text.strip()) >= 500:
            llm_source = "full-text"
            analysis_text = full_text
        elif abstract.strip():
            llm_source = "abstract"
            analysis_text = abstract
        else:
            llm_source = "neither"
            analysis_text = ""

        if analysis_text:
            analysis = llm.analyze_paper_content(
                title=paper.get("title", ""),
                text=analysis_text,
                research_focuses=research_focuses,
            )
            relevance_score = analysis["relevance_score"]
            llm_insights = {
                "method_of_study": analysis["method_of_study"],
                "key_findings": analysis["key_findings"],
                "limitations": analysis["limitations"],
            }
        else:
            relevance = llm.score_paper_relevance(
                title=paper.get("title", ""),
                abstract="",
                research_focuses=research_focuses,
            )
            relevance_score = relevance["relevance_score"]
            llm_insights = None

        manual_bonus = float(existing_meta.get("manual_bonus", 0.0) or 0.0)
        priority_scores = llm.calculate_priority_score(
            relevance_score=relevance_score,
            total_citations=scite_metrics.get("total", scite_metrics.get("total_citations", 0)),
            year=paper.get("year"),
            manual_bonus=manual_bonus,
        )

        note_path = self.obs.create_or_update_literature_note(
            paper_metadata=paper,
            annotations=annotations,
            scite_metrics=scite_metrics,
            llm_insights=llm_insights,
            llm_source=llm_source,
            priority_scores=priority_scores,
        )
        self._upsert_paper_index(paper)

        return {
            "key": paper_key,
            "citekey": citekey,
            "status": "analyzed",
            "priority_score": priority_scores["priority_score"],
            "llm_source": llm_source,
            "path": str(note_path),
        }

    def analyze_library(
        self,
        llm: LLMService,
        research_focuses: list[dict[str, Any]] | None = None,
        force: bool = False,
        max_workers: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Analyze all primary papers in Zotero in parallel (capped at `max_workers` <= 10
        and rate-limited by `LLMService` to stay under Purdue GenAI's 20 req/min limit).
        """
        if research_focuses is None:
            research_focuses = settings.get_research_focuses(active_only=True)["focuses"]

        raw_items = self.zot._get_items_raw()
        keys = [
            item["key"]
            for item in raw_items
            if item.get("data", {}).get("itemType") not in self.EXCLUDED_ITEM_TYPES
        ]
        return llm.run_parallel(
            keys,
            lambda key: self.analyze_paper(
                paper_key=key,
                llm=llm,
                research_focuses=research_focuses,
                force=force,
            ),
            max_workers=max_workers,
        )
