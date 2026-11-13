"""
Centralized Configuration & Keyring Reader
------------------------------------------
Reads credentials directly from the Linux system keyring (service: 'lit-review')
managed by standard Linux CLI tools (such as secret-tool or keyring CLI).

Zero secrets or personal cloud directories stored in repository files.
"""

import os
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
