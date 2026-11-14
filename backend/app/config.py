"""
Centralized Configuration & Keyring Reader
------------------------------------------
Reads credentials directly from the Linux system keyring (service: 'lit-review')
managed by standard Linux CLI tools (such as secret-tool or keyring CLI).

Zero secrets or personal cloud directories stored in repository files.
"""

import os
import re
import json
from datetime import datetime, timezone
from typing import Any
import keyring
from pathlib import Path

KEYRING_SERVICE_NAME = "lit-review"

# Determine repository root directory (where the 'obsidian' symlink lives)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings:
    def __init__(self):
        # Default to the 'obsidian' symlink in the repository root
        default_vault_path = REPO_ROOT / "obsidian"
        self.obsidian_vault_path: str = os.environ.get(
            "OBSIDIAN_VAULT_PATH",
            str(default_vault_path)
        )
        self.zotero_library_type: str = os.environ.get("ZOTERO_LIBRARY_TYPE", "user")
        self.research_focus_path: Path = REPO_ROOT / "research_focus.json"

    def get_research_focuses(self, active_only: bool = False) -> dict[str, Any]:
        """Read all research focuses from research_focus.json."""
        data: dict[str, Any] = {"focuses": [], "updated_at": ""}
        if self.research_focus_path.exists():
            try:
                data = json.loads(self.research_focus_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        focuses = data.get("focuses", [])
        if active_only:
            focuses = [f for f in focuses if f.get("active", True)]
        return {"focuses": focuses, "updated_at": data.get("updated_at", "")}

    def _save_research_focuses(self, focuses: list[dict[str, Any]]) -> dict[str, Any]:
        data = {
            "focuses": focuses,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self.research_focus_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return data

    def add_research_focus(self, title: str, description: str = "") -> dict[str, Any]:
        """Add (or update) an active research focus by slugified ID."""
        focus_id = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "topic"
        focuses = self.get_research_focuses()["focuses"]

        new_entry = {
            "id": focus_id,
            "title": title.strip(),
            "description": description.strip(),
            "active": True,
        }
        # Replace if ID already exists, else append
        updated = [f for f in focuses if f.get("id") != focus_id]
        updated.append(new_entry)
        return self._save_research_focuses(updated)

    def remove_research_focus(self, focus_id: str) -> dict[str, Any]:
        """Remove a completed research focus by ID."""
        focuses = self.get_research_focuses()["focuses"]
        remaining = [f for f in focuses if f.get("id") != focus_id]
        return self._save_research_focuses(remaining)

    @property
    def zotero_api_key(self) -> str | None:
        return keyring.get_password(KEYRING_SERVICE_NAME, "ZOTERO_API_KEY")

    @property
    def zotero_library_id(self) -> str | None:
        return keyring.get_password(KEYRING_SERVICE_NAME, "ZOTERO_LIBRARY_ID")

    @property
    def scite_api_key(self) -> str | None:
        return keyring.get_password(KEYRING_SERVICE_NAME, "SCITE_API_KEY")

    @property
    def genai_api_key(self) -> str | None:
        return keyring.get_password(KEYRING_SERVICE_NAME, "GENAI_API_KEY")


settings = Settings()
