"""
Centralized Configuration & Keyring Reader
------------------------------------------
Reads credentials directly from the Linux system keyring (service: 'lit-review')
managed by standard Linux CLI tools (such as secret-tool or keyring CLI).
"""

import os
import keyring
from pathlib import Path

KEYRING_SERVICE_NAME = "lit-review"


class Settings:
    def __init__(self):
        self.obsidian_vault_path: str = os.environ.get(
            "OBSIDIAN_VAULT_PATH",
            str(Path.home() / "Dropbox" / "Obsidian" / "Academic")
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
