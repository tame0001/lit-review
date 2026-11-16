"""
Index Service (SQLite)
----------------------
Lightweight SQLite read-cache for paper metadata, read status, and priority scores.
Allows the web UI (`GET /api/papers`) to load 1,000+ papers in milliseconds without
hitting Zotero or scanning Obsidian markdown files on every page load.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import frontmatter
from ..config import REPO_ROOT


class IndexService:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else (REPO_ROOT / ".lit_review_index.db")
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS papers (
                    key TEXT PRIMARY KEY,
                    version INTEGER,
                    citekey TEXT NOT NULL,
                    title TEXT NOT NULL,
                    authors_json TEXT NOT NULL DEFAULT '[]',
                    author_short TEXT,
                    year INTEGER,
                    doi TEXT,
                    publication TEXT,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    collections_json TEXT NOT NULL DEFAULT '[]',
                    has_obsidian_note INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'unread',
                    priority_score REAL NOT NULL DEFAULT 0.0,
                    manual_bonus REAL NOT NULL DEFAULT 0.0,
                    llm_analyzed INTEGER NOT NULL DEFAULT 0,
                    llm_analyzed_at TEXT,
                    llm_source TEXT NOT NULL DEFAULT 'neither',
                    scite_total_citations INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_citekey ON papers(citekey);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_score ON papers(priority_score DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status);")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS collections (
                    key TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    parent_key TEXT
                );
                """
            )

    def count_papers(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM papers").fetchone()
            return int(row["cnt"]) if row else 0

    def count_collections(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM collections").fetchone()
            return int(row["cnt"]) if row else 0

    @staticmethod
    def _row_to_summary(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "key": row["key"],
            "version": row["version"],
            "citekey": row["citekey"],
            "title": row["title"],
            "authors": json.loads(row["authors_json"] or "[]"),
            "author_short": row["author_short"],
            "year": row["year"],
            "doi": row["doi"],
            "publication": row["publication"],
            "tags": json.loads(row["tags_json"] or "[]"),
            "collections": json.loads(row["collections_json"] or "[]"),
            "has_obsidian_note": bool(row["has_obsidian_note"]),
            "status": row["status"],
            "priority_score": float(row["priority_score"] or 0.0),
            "manual_bonus": float(row["manual_bonus"] or 0.0),
            "llm_analyzed": bool(row["llm_analyzed"]),
            "llm_analyzed_at": row["llm_analyzed_at"],
            "llm_source": row["llm_source"],
            "scite_total_citations": int(row["scite_total_citations"] or 0),
        }

    def list_papers(
        self,
        collection_key: str | None = None,
        tag: str | None = None,
        status: str | None = None,
        limit: int = 2000,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM papers"
        clauses: list[str] = []
        params: list[Any] = []

        if status in ("read", "unread"):
            clauses.append("status = ?")
            params.append(status)

        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        query += " ORDER BY priority_score DESC, COALESCE(year, 0) DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        results: list[dict[str, Any]] = []
        for row in rows:
            item = self._row_to_summary(row)
            if collection_key and collection_key not in item["collections"]:
                continue
            if tag and tag not in item["tags"]:
                continue
            results.append(item)
            if len(results) >= limit:
                break
        return results

    def upsert_papers(self, papers: list[dict[str, Any]]) -> None:
        if not papers:
            return
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        records = [
            (
                p["key"],
                p.get("version"),
                p["citekey"],
                p.get("title", "Untitled"),
                json.dumps(p.get("authors", [])),
                p.get("author_short"),
                p.get("year"),
                p.get("doi"),
                p.get("publication"),
                json.dumps(p.get("tags", [])),
                json.dumps(p.get("collections", [])),
                1 if p.get("has_obsidian_note") else 0,
                p.get("status", "unread"),
                float(p.get("priority_score", 0.0) or 0.0),
                float(p.get("manual_bonus", 0.0) or 0.0),
                1 if p.get("llm_analyzed") else 0,
                str(p["llm_analyzed_at"]) if p.get("llm_analyzed_at") else None,
                str(p.get("llm_source", "neither")),
                int(p.get("scite_total_citations", 0) or 0),
                now,
            )
            for p in papers
        ]
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO papers (
                    key, version, citekey, title, authors_json, author_short, year, doi,
                    publication, tags_json, collections_json, has_obsidian_note, status,
                    priority_score, manual_bonus, llm_analyzed, llm_analyzed_at, llm_source,
                    scite_total_citations, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    version = excluded.version,
                    citekey = excluded.citekey,
                    title = excluded.title,
                    authors_json = excluded.authors_json,
                    author_short = excluded.author_short,
                    year = excluded.year,
                    doi = excluded.doi,
                    publication = excluded.publication,
                    tags_json = excluded.tags_json,
                    collections_json = excluded.collections_json,
                    has_obsidian_note = excluded.has_obsidian_note,
                    status = excluded.status,
                    priority_score = excluded.priority_score,
                    manual_bonus = excluded.manual_bonus,
                    llm_analyzed = excluded.llm_analyzed,
                    llm_analyzed_at = excluded.llm_analyzed_at,
                    llm_source = excluded.llm_source,
                    scite_total_citations = excluded.scite_total_citations,
                    updated_at = excluded.updated_at;
                """,
                records,
            )

    def upsert_paper(self, paper: dict[str, Any]) -> None:
        self.upsert_papers([paper])

    def update_bonus(self, citekey: str, manual_bonus: float, priority_score: float) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                "UPDATE papers SET manual_bonus = ?, priority_score = ?, updated_at = ? WHERE citekey = ?",
                (manual_bonus, priority_score, now, citekey),
            )

    def update_status(self, citekey: str, status: str) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                "UPDATE papers SET status = ?, updated_at = ? WHERE citekey = ?",
                (status, now, citekey),
            )

    def list_collections(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT key, name, parent_key FROM collections ORDER BY name ASC").fetchall()
            return [
                {"key": r["key"], "name": r["name"], "parent_key": r["parent_key"]}
                for r in rows
            ]

    def replace_collections(self, collections: list[dict[str, Any]]) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM collections")
            conn.executemany(
                "INSERT INTO collections (key, name, parent_key) VALUES (?, ?, ?)",
                [(c["key"], c["name"], c.get("parent_key")) for c in collections],
            )

    @staticmethod
    def build_summary_record(paper: dict[str, Any], obs_meta: dict[str, Any] | None) -> dict[str, Any]:
        meta = obs_meta or {}
        analyzed_at = meta.get("llm_analyzed_at")
        return {
            **paper,
            "has_obsidian_note": obs_meta is not None,
            "status": meta.get("status", "unread"),
            "priority_score": float(meta.get("priority_score", 0.0) or 0.0),
            "manual_bonus": float(meta.get("manual_bonus", 0.0) or 0.0),
            "llm_analyzed": bool(meta.get("llm_analyzed", False)),
            "llm_analyzed_at": str(analyzed_at) if analyzed_at else None,
            "llm_source": str(meta.get("llm_source", "neither")),
            "scite_total_citations": int(meta.get("scite_total_citations", 0) or 0),
        }

    def rebuild_from_sources(self, zot: Any, obs: Any) -> int:
        """Full index rebuild from Zotero + Obsidian frontmatter."""
        obs_meta_by_citekey: dict[str, dict[str, Any]] = {}
        if obs.lit_dir.exists():
            for md_file in obs.lit_dir.glob("@*.md"):
                try:
                    post = frontmatter.loads(md_file.read_text(encoding="utf-8", errors="ignore"))
                    ck = post.metadata.get("citekey") or md_file.stem.lstrip("@")
                    obs_meta_by_citekey[ck] = post.metadata
                except Exception:
                    continue

        papers = zot.get_read_papers(limit=10000)
        records = [
            self.build_summary_record(p, obs_meta_by_citekey.get(p["citekey"]))
            for p in papers
        ]
        self.upsert_papers(records)

        cols = zot.get_collections()
        self.replace_collections(cols)
        return len(records)
