"""
Obsidian Service
----------------
This service manages reading, creating, and updating Markdown literature notes 
and concept notes within the Dropbox-synced Obsidian vault (~/Dropbox/Obsidian/Academic).

Functionality / Feature List:
1. Vault Path & Directory Management:
   - Verify and manage folder structure:
     * `01-Literature/`: Atomic notes for each paper (`@citekey.md`).
     * `02-Concepts/`: Topic and method hub notes (`[[Hyperspectral]]`, `[[Transformer]]`).
     * `03-Research-Gaps/`: Dynamic Dataview tables and synthesis boards.
     * `04-Manuscripts/`: Notes and outlines linked to Quarto drafts.

2. Generate / Update Literature Note (`@citekey.md`):
   - Format standardized YAML frontmatter (citekey, title, authors, year, doi, tags, scite metrics).
   - Generate structured Markdown sections:
     * `## 💡 Quick Finding`: 1-2 sentence takeaway for citing in Quarto.
     * `## 📌 Highlighted Quotes`: Verbatim quotes with direct PDF page deep-links.
     * `## 🔬 Methodology & Setup`: Methods and datasets with `[[wikilinks]]`.
     * `## ⚠️ Limitations & Research Gaps`: Known weaknesses or open questions.
   - Non-destructive updates: Merge new Zotero highlights without overwriting manual notes already written by the user.

3. Concept & Wikilink Extraction:
   - Identify or create linked concept notes (`[[Concept]]`) referenced across literature notes.
   - Maintain bidirectional backlinks between literature notes and concept hubs.

4. Query / Search Existing Notes:
   - Scan existing literature notes to extract quotes, findings, or limitations for the FastAPI backend / frontend.
"""

from pathlib import Path
from typing import Any


class ObsidianService:
    def __init__(self, vault_path: str = "/home/tam/Dropbox/Obsidian/Academic"):
        self.vault_path = Path(vault_path)
        self.lit_dir = self.vault_path / "01-Literature"
        self.concepts_dir = self.vault_path / "02-Concepts"
        self.gaps_dir = self.vault_path / "03-Research-Gaps"

    def ensure_directories(self) -> None:
        """Create standard vault folders if they do not exist."""
        raise NotImplementedError("Feature 1: Vault Path & Directory Management not implemented")

    def note_exists(self, citekey: str) -> bool:
        """Check if a note for @citekey already exists in 01-Literature/."""
        raise NotImplementedError("Feature 1: Check note existence not implemented")

    def create_or_update_literature_note(
        self,
        paper_metadata: dict[str, Any],
        annotations: list[dict[str, Any]],
        quick_finding: str | None = None,
        methods: list[str] | None = None,
        limitations: list[str] | None = None,
    ) -> Path:
        """
        Write or update an atomic literature note (@citekey.md) with YAML frontmatter,
        quotes, deep-links, and structured sections.
        """
        raise NotImplementedError("Feature 2: Generate / Update Literature Note not implemented")

    def get_all_literature_notes(self) -> list[dict[str, Any]]:
        """Scan all @citekey.md notes and parse frontmatter + content for search."""
        raise NotImplementedError("Feature 4: Query / Search Existing Notes not implemented")
