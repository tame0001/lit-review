"""
Zotero Service
--------------
This service interfaces with the Zotero API (and/or local Zotero SQLite database)
to extract metadata, PDF attachments, annotations, and colored highlights.

Credentials are securely retrieved via the system keyring (backend/app/config.py).

Functionality / Feature List:
1. Initialize Client: [IMPLEMENTED]
   - Connect to Zotero API using library_id, api_key from system keyring, and library_type (user/personal library).
   - Verify connection status.

2. Fetch Read Papers: [PENDING]
   - Retrieve items marked as 'read' or items belonging to a specific collection.
   - Extract core bibliographic metadata: citekey, title, authors, year, DOI, abstract, and URL.

3. Extract PDF Highlights & Annotations: [PENDING]
   - Retrieve all annotations (highlights, marginal notes, comments) attached to a paper's PDF.
   - Group highlights by color semantics:
     * Yellow (#ffd400): Core findings / claims
     * Green (#5fb236): Methodology, datasets, models, sample sizes
     * Red/Pink (#ff6666): Limitations, weaknesses, unresolved questions
     * Purple (#a28ae5): Direct verbatim quotes for citation
   - Preserve page numbers and build deep-links (`zotero://open-pdf/library/items/<key>?page=<page>&annotation=<annKey>`).

4. Update Paper Metadata / Tags: [PENDING]
   - Add or update tags in Zotero (e.g. status tags: `!p1-must-read`, `status/read`, `status/cite-only`).
"""

from typing import Any
from pyzotero import zotero
from ..config import settings


class ZoteroService:
    def __init__(
        self,
        library_id: str | None = None,
        api_key: str | None = None,
        library_type: str | None = None,
    ):
        """
        Feature 1: Initialize Zotero Client.
        Retrieves credentials from system keyring (via settings) by default,
        with optional override parameters.
        """
        self.library_id = library_id or settings.zotero_library_id
        self.api_key = api_key or settings.zotero_api_key
        self.library_type = library_type or settings.zotero_library_type

        if not self.library_id or not self.api_key:
            raise ValueError(
                "Missing Zotero credentials: ZOTERO_LIBRARY_ID and ZOTERO_API_KEY must be "
                "stored in system keyring (service: 'lit-review') or provided as arguments."
            )

        self.client = zotero.Zotero(self.library_id, self.library_type, self.api_key)

    def verify_connection(self) -> dict[str, Any]:
        """
        Verify credentials by querying basic key permissions.
        Returns a dictionary with status and library details if successful.
        """
        try:
            # Query key permissions to verify read access without pulling large data
            key_info = self.client.key_info()
            return {
                "status": "connected",
                "library_id": self.library_id,
                "library_type": self.library_type,
                "user_id": key_info.get("userID"),
                "permissions": key_info.get("access", {}),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
            }

    async def get_paper_metadata(self, item_key: str) -> dict[str, Any]:
        """Fetch core metadata (title, authors, year, citekey, DOI) for a single paper."""
        raise NotImplementedError("Feature 2: Fetch Paper Metadata not implemented")

    async def get_read_papers(self, collection_key: str | None = None) -> list[dict[str, Any]]:
        """Retrieve papers that have annotations or are marked as read."""
        raise NotImplementedError("Feature 2: Fetch Read Papers not implemented")

    async def get_pdf_annotations(self, item_key: str) -> list[dict[str, Any]]:
        """
        Extract highlights and notes from the PDF attachment of a paper.
        Returns list of quotes with: text, color, page, deep-link, and user comment.
        """
        raise NotImplementedError("Feature 3: Extract PDF Highlights & Annotations not implemented")

    async def add_tag_to_item(self, item_key: str, tag: str) -> bool:
        """Add a status or topic tag to a Zotero item."""
        raise NotImplementedError("Feature 4: Update Paper Metadata / Tags not implemented")
