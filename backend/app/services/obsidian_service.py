"""
Obsidian Service
----------------
Manages reading, creating, and updating Markdown literature notes 
and concept notes within the linked Obsidian vault (./obsidian).

Folders Managed:
- `01-Literature/`: Atomic notes for each paper (`@citekey.md`).
- `02-Concepts/`: Topic and method hub notes (`[[Hyperspectral]]`, `[[Transformer]]`).
- `03-Research-Gaps/`: Dynamic Dataview tables and synthesis boards.

Features Implemented:
1. Directory Management: ensure_directories()
2. Literature Note Generator & Non-Destructive Updater: create_or_update_literature_note()
   - YAML Frontmatter with Better BibTeX citekey and Scite tallies
   - 4-Color categorized highlights with clickable zotero://open-pdf/... deep links
   - Methodologies with [[wikilinks]]
   - Limitations and Scite.ai contrasting evidence
   - Non-destructive preservation of '## 📝 My Personal Reading Notes'
3. Note Querying & Search: get_literature_note(), list_all_notes()
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import frontmatter
from ..config import settings


class ObsidianService:
    PERSONAL_NOTES_HEADER = "## 📝 My Personal Reading Notes"

    def __init__(self, vault_path: str | Path | None = None):
        self.vault_path = Path(vault_path) if vault_path else Path(settings.obsidian_vault_path)
        self.lit_dir = self.vault_path / "01-Literature"
        self.concepts_dir = self.vault_path / "02-Concepts"
        self.gaps_dir = self.vault_path / "03-Research-Gaps"

    def ensure_directories(self) -> dict[str, bool]:
        """Create standard vault folders (01 to 03) if they do not exist."""
        created = {}
        for directory in (self.lit_dir, self.concepts_dir, self.gaps_dir):
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)
                created[directory.name] = True
            else:
                created[directory.name] = False
        return created

    def note_exists(self, citekey: str) -> bool:
        """Check if an atomic note for @citekey exists in 01-Literature/."""
        return (self.lit_dir / f"@{citekey}.md").exists()

    def is_llm_analyzed(self, citekey: str) -> bool:
        """Return True if @citekey.md exists and already has `llm_analyzed: true`."""
        file_path = self.lit_dir / f"@{citekey}.md"
        if not file_path.exists():
            return False
        try:
            post = frontmatter.loads(file_path.read_text(errors="ignore"))
            return bool(post.metadata.get("llm_analyzed", False))
        except Exception:
            return False

    def _extract_existing_personal_notes(self, file_path: Path) -> str | None:
        """
        Extract user's manual notes under '## 📝 My Personal Reading Notes'
        to ensure they are never overwritten during re-sync.
        Strips the default placeholder comment if present.
        """
        if not file_path.exists():
            return None

        try:
            content = file_path.read_text(errors="ignore")
            if self.PERSONAL_NOTES_HEADER in content:
                parts = content.split(self.PERSONAL_NOTES_HEADER, 1)
                personal_text = parts[1].strip()
                # Remove default HTML placeholder comment
                cleaned = re.sub(r"<!--.*?-->", "", personal_text, flags=re.DOTALL).strip()
                if cleaned:
                    return cleaned
        except Exception as e:
            print(f"Warning: Could not read existing personal notes from {file_path}: {e}")
        return None

    @staticmethod
    def _format_annotation_entry(a: dict[str, Any], badge: str) -> str:
        """Format a single Zotero highlight/annotation with page deep-link and optional comment."""
        page = a.get("page", 1)
        link = a.get("deep_link", "")
        text = (a.get("text") or "").replace("\n", " ").strip()
        comment = a.get("comment")

        entry = f"- {badge} *\"{text}\"* ([p. {page}]({link}))"
        if comment:
            entry += f"\n  > **Note:** {comment}"
        return entry

    def create_or_update_literature_note(
        self,
        paper_metadata: dict[str, Any],
        annotations: list[dict[str, Any]] | None = None,
        quick_finding: str | None = None,
        methods: list[str] | None = None,
        topics: list[str] | None = None,
        limitations: list[str] | None = None,
        scite_metrics: dict[str, int] | None = None,
        contrasting_snippets: list[dict[str, Any]] | None = None,
        llm_insights: dict[str, Any] | None = None,
        llm_source: str | None = None,
        priority_scores: dict[str, float] | None = None,
    ) -> Path:
        """
        Write or non-destructively update an atomic literature note (@citekey.md).
        Tracks whether the paper was read by the user (`status`) and whether/how
        it was analyzed by the LLM (`llm_analyzed`, `llm_analyzed_at`, `llm_source`).
        """
        self.ensure_directories()

        citekey = paper_metadata.get("citekey", "unknown")
        file_path = self.lit_dir / f"@{citekey}.md"
        annotations = annotations or []
        methods = methods or []
        topics = topics or []
        limitations = limitations or []
        scite_metrics = scite_metrics or {"supporting": 0, "contrasting": 0, "mentioning": 0}
        contrasting_snippets = contrasting_snippets or []

        # Preserve existing user handwritten notes if file already exists
        existing_personal_notes = self._extract_existing_personal_notes(file_path)

        # Preserve existing LLM status/section if re-syncing highlights without re-running LLM
        existing_llm_section: str | None = None
        existing_llm_meta: dict[str, Any] = {}
        if file_path.exists():
            try:
                existing_post = frontmatter.loads(file_path.read_text(errors="ignore"))
                existing_llm_meta = {
                    "llm_analyzed": existing_post.metadata.get("llm_analyzed", False),
                    "llm_analyzed_at": existing_post.metadata.get("llm_analyzed_at"),
                    "llm_source": existing_post.metadata.get("llm_source", "neither"),
                    "priority_score": existing_post.metadata.get("priority_score", 0.0),
                    "manual_bonus": existing_post.metadata.get("manual_bonus", 0.0),
                    "status_override": existing_post.metadata.get("status_override"),
                }
                llm_match = re.search(
                    r"(## 🤖 LLM Analysis.*?)(?=\n## |\Z)",
                    existing_post.content,
                    re.DOTALL,
                )
                if llm_match:
                    existing_llm_section = llm_match.group(1).strip()
            except Exception:
                pass

        # ---------------------------------------------------------------------
        # 1. Frontmatter Metadata (Zotero tags as single source of truth)
        # ---------------------------------------------------------------------
        raw_zotero_tags = paper_metadata.get("tags", [])
        tags = [
            re.sub(r"\s+", "-", t.strip())
            for t in raw_zotero_tags
            if isinstance(t, str) and t.strip()
        ]

        if llm_insights is not None:
            llm_analyzed = True
            llm_analyzed_at = datetime.now().strftime("%Y-%m-%d")
            resolved_llm_source = llm_source or "abstract"
        else:
            llm_analyzed = existing_llm_meta.get("llm_analyzed", False)
            llm_analyzed_at = existing_llm_meta.get("llm_analyzed_at")
            resolved_llm_source = llm_source or existing_llm_meta.get("llm_source", "neither")

        resolved_priority = (
            priority_scores.get("priority_score", 0.0)
            if priority_scores is not None
            else existing_llm_meta.get("priority_score", 0.0)
        )
        resolved_bonus = (
            priority_scores.get("manual_bonus", 0.0)
            if priority_scores is not None
            else existing_llm_meta.get("manual_bonus", 0.0)
        )

        status_override = existing_llm_meta.get("status_override")
        resolved_status = (
            status_override
            if status_override in ("read", "unread")
            else ("read" if annotations else "unread")
        )

        meta = {
            "citekey": citekey,
            "title": paper_metadata.get("title", "Untitled"),
            "authors": paper_metadata.get("authors", []),
            "year": paper_metadata.get("year"),
            "doi": paper_metadata.get("doi"),
            "status": resolved_status,
            **({"status_override": status_override} if status_override in ("read", "unread") else {}),
            "priority_score": resolved_priority,
            "manual_bonus": resolved_bonus,
            "llm_analyzed": llm_analyzed,
            "llm_analyzed_at": llm_analyzed_at,
            "llm_source": resolved_llm_source,
            "tags": tags,
            "scite_supporting": scite_metrics.get("supporting", 0),
            "scite_contrasting": scite_metrics.get("contrasting", 0),
            "scite_mentioning": scite_metrics.get("mentioning", 0),
            "scite_total_citations": scite_metrics.get("total", scite_metrics.get("total_citations", 0)),
        }

        # ---------------------------------------------------------------------
        # 2. Section Partitioning of Annotations
        # ---------------------------------------------------------------------
        method_annots = [a for a in annotations if a.get("category") == "method"]
        finding_annots = [a for a in annotations if a.get("category") == "finding"]
        quote_annots = [a for a in annotations if a.get("category") == "quote"]
        context_annots = [a for a in annotations if a.get("category") == "context"]
        limitation_annots = [a for a in annotations if a.get("category") == "limitation"]
        other_annots = [a for a in annotations if a.get("category") == "other"]

        # ---------------------------------------------------------------------
        # 3. Construct Markdown Body (Starts directly with Abstract)
        # ---------------------------------------------------------------------
        body_sections: list[str] = []

        # Abstract Callout (if available)
        abstract = paper_metadata.get("abstract")
        if abstract:
            clean_abstract = "\n> ".join(abstract.strip().splitlines())
            body_sections.append(f"> [!ABSTRACT]\n> {clean_abstract}\n")

        def append_highlight_section(title: str, items: list[dict[str, Any]], badge: str, empty_msg: str) -> None:
            body_sections.append(title)
            if items:
                for item in items:
                    body_sections.append(self._format_annotation_entry(item, badge))
                body_sections.append("")
            else:
                body_sections.append(f"*{empty_msg}*\n")

        # 1. Methods
        body_sections.append("## 🔬 Methods")
        if methods:
            body_sections.append(f"- **Tags/Models**: {', '.join(f'[[{m}]]' for m in methods)}")
        if method_annots:
            for item in method_annots:
                body_sections.append(self._format_annotation_entry(item, "🟢"))
            body_sections.append("")
        elif not methods:
            body_sections.append("*No methodology highlights recorded.*\n")
        else:
            body_sections.append("")

        # 2. Key Findings
        append_highlight_section(
            "## 💡 Key Findings",
            finding_annots,
            "🟡",
            "No key finding highlights recorded."
        )

        # 3. Quotes
        append_highlight_section(
            "## 📌 Quotes",
            quote_annots,
            "🟣",
            "No quote highlights recorded."
        )

        # 4. Context
        append_highlight_section(
            "## 📖 Context",
            context_annots,
            "🔵",
            "No context highlights recorded."
        )

        # 5. Limitations
        body_sections.append("## ⚠️ Limitations & Research Gaps")
        if limitations or limitation_annots:
            for lim in limitations:
                prefix = "- " if not lim.startswith("- ") else ""
                body_sections.append(f"{prefix}{lim}")
            for item in limitation_annots:
                body_sections.append(self._format_annotation_entry(item, "🔴"))
            body_sections.append("")
        else:
            body_sections.append("*No explicit limitations noted yet.*\n")

        # Other uncategorized highlights (only if present)
        if other_annots:
            append_highlight_section("## ⚪ Other Highlights", other_annots, "⚪", "")

        # Scite.ai Contrasting Evidence
        if contrasting_snippets:
            body_sections.append("## ⚖️ Scite.ai Contrasting Evidence (Contested Claims)")
            for s in contrasting_snippets:
                c_doi = s.get("citing_doi", "")
                c_title = s.get("citing_title") or f"DOI: {c_doi}"
                snippet = s.get("snippet", "").replace("\n", " ").strip()
                body_sections.append(f"- **Disputed by {c_title}:**\n  > \"{snippet}\"")
            body_sections.append("")

        # LLM Structured Analysis (separated from user highlights)
        if llm_insights is not None:
            body_sections.append(f"## 🤖 LLM Analysis (Source: {resolved_llm_source})")
            method_study = llm_insights.get("method_of_study")
            if method_study:
                body_sections.append(f"- **Method of Study:** {method_study}")
            kf = llm_insights.get("key_findings", [])
            if kf:
                body_sections.append("- **Key Findings:**")
                for item in kf:
                    body_sections.append(f"  - {item}")
            lims = llm_insights.get("limitations", [])
            if lims:
                body_sections.append("- **Limitations:**")
                for item in lims:
                    body_sections.append(f"  - {item}")
            body_sections.append("")
        elif existing_llm_section:
            body_sections.append(existing_llm_section + "\n")

        # Protected User Notes Section
        body_sections.append(self.PERSONAL_NOTES_HEADER)
        if existing_personal_notes:
            body_sections.append(existing_personal_notes)
        else:
            body_sections.append(
                "<!-- You can write your personal thoughts, meeting notes, or project ideas here.\n"
                "     The sync script will NEVER overwrite this section when updating! -->\n"
            )

        # ---------------------------------------------------------------------
        # 4. Write Frontmatter & Content to File
        # ---------------------------------------------------------------------
        full_content = "\n".join(body_sections)
        post = frontmatter.Post(full_content, **meta)
        
        file_path.write_bytes(frontmatter.dumps(post).encode("utf-8"))
        return file_path

    # -------------------------------------------------------------------------
    # Note Querying & Search
    # -------------------------------------------------------------------------
    def get_literature_note(self, citekey: str) -> dict[str, Any] | None:
        """Read and parse an existing literature note."""
        file_path = self.lit_dir / f"@{citekey}.md"
        if not file_path.exists():
            return None

        post = frontmatter.loads(file_path.read_text(errors="ignore"))
        return {
            "citekey": post.metadata.get("citekey", citekey),
            "metadata": post.metadata,
            "content": post.content,
            "path": str(file_path),
        }

    def list_all_notes(self) -> list[dict[str, Any]]:
        """List all @citekey.md notes currently stored in 01-Literature/."""
        if not self.lit_dir.exists():
            return []

        notes = []
        for p in self.lit_dir.glob("@*.md"):
            try:
                post = frontmatter.loads(p.read_text(errors="ignore"))
                notes.append({
                    "citekey": post.metadata.get("citekey", p.stem.lstrip("@")),
                    "title": post.metadata.get("title", p.stem),
                    "year": post.metadata.get("year"),
                    "status": post.metadata.get("status", "unread"),
                    "scite_contrasting": post.metadata.get("scite_contrasting", 0),
                    "path": str(p),
                })
            except Exception:
                continue

        notes.sort(key=lambda x: str(x.get("year") or ""), reverse=True)
        return notes
