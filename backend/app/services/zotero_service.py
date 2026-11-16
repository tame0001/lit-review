"""
Zotero Service
--------------
Local-first Zotero service with seamless Cloud API fallback.
Uses httpx2 for high-performance, standardized HTTP requests.

When Zotero Desktop is open, queries http://localhost:23119 (< 5ms, offline, zero rate-limit).
If Zotero Desktop is closed, issues a clear status warning and automatically falls back
to the official cloud API (api.zotero.org) using encrypted keyring credentials.

Features Implemented:
1. Initialize Client & Dual-Mode Status Monitoring (via httpx2)
2. Fetch Read Papers & Metadata with Better BibTeX Citekey Resolution
3. Extract PDF Highlights & Annotations with Color Semantics & Deep-Links
4. Update Paper Metadata / Tags
"""

import io
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
import httpx2
from pypdf import PdfReader
from pyzotero import zotero
from ..config import settings


class ZoteroService:
    LOCAL_URL = "http://localhost:23119/api/users/0"
    COLOR_MAP = {
        "#ffd400": "finding",      # Yellow: Core findings / takeaways
        "#5fb236": "method",       # Green: Methodology, datasets, models
        "#ff6666": "limitation",   # Red/Pink: Limitations, weaknesses, gaps
        "#a28ae5": "quote",        # Purple: Verbatim quotes for citation
        "#2ea8e5": "context",      # Blue: Background / context
    }

    def __init__(
        self,
        library_id: str | None = None,
        api_key: str | None = None,
        library_type: str | None = None,
        prefer_local: bool = True,
        timeout: float = 15.0,
    ):
        self.library_id = library_id or settings.zotero_library_id
        self.api_key = api_key or settings.zotero_api_key
        self.library_type = library_type or settings.zotero_library_type
        self.prefer_local = prefer_local
        self.timeout = timeout

        # Shared httpx2 client for local requests
        self.http_client = httpx2.Client(
            headers={"User-Agent": "lit-review-backend/1.0"},
            timeout=self.timeout,
        )

        # Connection status tracking
        self.is_local_available: bool = False
        self.active_mode: str = "cloud"

        # Initialize cloud client as backup/foundation
        self.cloud_client: zotero.Zotero | None = None
        if self.library_id and self.api_key:
            self.cloud_client = zotero.Zotero(self.library_id, self.library_type, self.api_key)

        # Check local connection and emit status/warning
        self.refresh_connection_status()

    def refresh_connection_status(self) -> dict[str, Any]:
        """Probe localhost API via httpx2 to determine if Zotero Desktop is active."""
        if not self.prefer_local:
            self.is_local_available = False
            self.active_mode = "cloud"
            return {"mode": "cloud", "local_available": False}

        try:
            resp = self.http_client.get(f"{self.LOCAL_URL}/collections", timeout=1.0)
            if resp.status_code == 200:
                self.is_local_available = True
                self.active_mode = "local"
                print("✓ [ZoteroService] Connected to Zotero Localhost API (fast, offline-ready).")
                return {"mode": "local", "local_available": True}
        except Exception:
            pass

        self.is_local_available = False
        self.active_mode = "cloud"
        print("⚠️ [ZoteroService] WARNING: Localhost API unreachable (Zotero desktop closed?). Falling back to Cloud API.")
        return {"mode": "cloud", "local_available": False}

    # -------------------------------------------------------------------------
    # Internal HTTP Dispatcher via httpx2 (Local vs. Cloud)
    # -------------------------------------------------------------------------
    def _local_get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Execute a GET request against Zotero localhost server using httpx2."""
        url = f"{self.LOCAL_URL}/{endpoint}"
        resp = self.http_client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _local_get_paginated(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        max_items: int = 10000,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch all pages from Zotero localhost API in chunks so large libraries never time out."""
        results: list[dict[str, Any]] = []
        base_params = dict(params or {})
        start = 0

        while len(results) < max_items:
            batch_limit = min(page_size, max_items - len(results))
            page_params = {**base_params, "limit": batch_limit, "start": start}
            batch = self._local_get(endpoint, page_params)
            if not batch:
                break
            results.extend(batch)
            if len(batch) < batch_limit:
                break
            start += len(batch)

        return results

    def _get_items_raw(self, **kwargs) -> list[dict[str, Any]]:
        """Fetch items using local API if available, else cloud."""
        requested_limit = int(kwargs.get("limit", 10000))
        if self.is_local_available:
            try:
                params: dict[str, Any] = {}
                if "itemType" in kwargs:
                    params["itemType"] = kwargs["itemType"]
                if "tag" in kwargs:
                    params["tag"] = kwargs["tag"]
                return self._local_get_paginated("items", params, max_items=requested_limit)
            except Exception as e:
                print(f"Local query failed ({e}); falling back to cloud.")
                self.refresh_connection_status()

        if not self.cloud_client:
            raise RuntimeError("Cloud client unavailable: Zotero credentials missing in keyring.")
        if requested_limit > 100:
            cloud_kwargs = {k: v for k, v in kwargs.items() if k != "limit"}
            return self.cloud_client.everything(self.cloud_client.items(**cloud_kwargs))[:requested_limit]
        return self.cloud_client.items(**kwargs)

    def _get_collection_items_raw(self, collection_key: str, **kwargs) -> list[dict[str, Any]]:
        """Fetch collection items using local API if available, else cloud."""
        requested_limit = int(kwargs.get("limit", 10000))
        if self.is_local_available:
            try:
                params: dict[str, Any] = {}
                if "itemType" in kwargs:
                    params["itemType"] = kwargs["itemType"]
                return self._local_get_paginated(
                    f"collections/{collection_key}/items", params, max_items=requested_limit
                )
            except Exception:
                self.refresh_connection_status()

        if not self.cloud_client:
            raise RuntimeError("Cloud client unavailable: Zotero credentials missing in keyring.")
        if requested_limit > 100:
            cloud_kwargs = {k: v for k, v in kwargs.items() if k != "limit"}
            return self.cloud_client.everything(
                self.cloud_client.collection_items(collection_key, **cloud_kwargs)
            )[:requested_limit]
        return self.cloud_client.collection_items(collection_key, **kwargs)

    def _get_children_raw(self, item_key: str) -> list[dict[str, Any]]:
        """Fetch child items (attachments, notes, annotations)."""
        if self.is_local_available:
            try:
                return self._local_get(f"items/{item_key}/children")
            except Exception:
                self.refresh_connection_status()

        if not self.cloud_client:
            raise RuntimeError("Cloud client unavailable.")
        return self.cloud_client.children(item_key)

    # -------------------------------------------------------------------------
    # Feature 2 Helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def _extract_year(date_str: str | None) -> int | None:
        if not date_str:
            return None
        match = re.search(r"\b(19\d\d|20\d\d)\b", str(date_str))
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_authors(creators: list[dict[str, Any]] | None) -> list[str]:
        if not creators:
            return []
        authors = []
        for c in creators:
            if "name" in c:
                authors.append(c["name"])
            elif "firstName" in c and "lastName" in c:
                authors.append(f"{c['firstName']} {c['lastName']}".strip())
            elif "lastName" in c:
                authors.append(c["lastName"])
        return authors

    @staticmethod
    def _extract_first_author_lastname(creators: list[dict[str, Any]] | None) -> str:
        if not creators:
            return "unknown"
        first = creators[0]
        name = first.get("lastName") or first.get("name", "unknown")
        cleaned = re.sub(r"[^\w]", "", name.lower())
        return cleaned or "unknown"

    def _extract_citekey(self, data: dict[str, Any]) -> str:
        """Extract Better BibTeX citation key from 'extra' or generate fallback."""
        extra = data.get("extra", "")
        if extra:
            match = re.search(r"(?:Citation Key|bibtex):\s*([A-Za-z0-9_-]+)", extra, re.IGNORECASE)
            if match:
                return match.group(1)

        # Fallback to BBT formula: [auth:lower][TitleWordsCapitalized][year]
        author = self._extract_first_author_lastname(data.get("creators"))
        year = self._extract_year(data.get("date")) or ""
        title = data.get("title", "")
        
        # Standard Better BibTeX skip words list
        skip_words = {
            "a", "an", "the", "for", "towards", "on", "in", "of", "and", "to",
            "with", "using", "from", "by", "as", "at", "into", "through", "during"
        }
        words = [re.sub(r"[^\w]", "", w) for w in title.split()]
        sig_words = [w.capitalize() for w in words if w.lower() not in skip_words and len(w) > 1]
        title_part = "".join(sig_words[:3]) or "Paper"
        return f"{author}{title_part}{year}"

    def _parse_item(self, item: dict[str, Any]) -> dict[str, Any]:
        data = item.get("data", {})
        key = data.get("key", "")
        creators = data.get("creators", [])
        
        return {
            "key": key,
            "version": item.get("version"),
            "citekey": self._extract_citekey(data),
            "title": data.get("title", "Untitled"),
            "authors": self._extract_authors(creators),
            "author_short": item.get("meta", {}).get("creatorSummary"),
            "year": self._extract_year(data.get("date")),
            "date": data.get("date"),
            "doi": data.get("DOI"),
            "url": data.get("url"),
            "item_type": data.get("itemType"),
            "publication": data.get("publicationTitle"),
            "abstract": data.get("abstractNote"),
            "collections": data.get("collections", []),
            "tags": [t.get("tag") for t in data.get("tags", [])],
            "num_children": item.get("meta", {}).get("numChildren", 0),
        }

    # -------------------------------------------------------------------------
    # Public API Methods
    # -------------------------------------------------------------------------
    def get_collections(self) -> list[dict[str, Any]]:
        """List all collections in the library."""
        if self.is_local_available:
            try:
                raw_collections = self._local_get("collections")
                return [
                    {
                        "key": c["data"]["key"],
                        "name": c["data"]["name"],
                        "parent_key": c["data"].get("parentCollection") or None,
                    }
                    for c in raw_collections
                ]
            except Exception:
                self.refresh_connection_status()

        if self.cloud_client:
            raw_collections = self.cloud_client.collections()
            return [
                {
                    "key": c["data"]["key"],
                    "name": c["data"]["name"],
                    "parent_key": c["data"].get("parentCollection") or None,
                }
                for c in raw_collections
            ]
        return []

    def get_item_raw(self, item_key: str) -> dict[str, Any]:
        """Fetch raw item JSON by key (local-first with cloud fallback)."""
        if self.is_local_available:
            try:
                return self._local_get(f"items/{item_key}")
            except Exception:
                self.refresh_connection_status()

        if not self.cloud_client:
            raise RuntimeError("Cloud client unavailable: Zotero credentials missing in keyring.")
        return self.cloud_client.item(item_key)

    def get_paper_metadata(self, item_key: str) -> dict[str, Any]:
        """Fetch normalized metadata for a single paper by item key."""
        return self._parse_item(self.get_item_raw(item_key))

    def get_changes_since(self, since_version: int | None = None) -> tuple[list[dict[str, Any]], int]:
        """
        Fetch all library items (papers, attachments, annotations) modified since `since_version`.
        Handles pagination and returns (items, latest_library_version).
        """
        all_items: list[dict[str, Any]] = []
        latest_version = since_version or 0
        start = 0
        limit = 100

        if self.is_local_available:
            try:
                while True:
                    params: dict[str, Any] = {"limit": limit, "start": start}
                    if since_version is not None:
                        params["since"] = since_version

                    resp = self.http_client.get(f"{self.LOCAL_URL}/items", params=params)
                    resp.raise_for_status()

                    if "Last-Modified-Version" in resp.headers:
                        latest_version = int(resp.headers["Last-Modified-Version"])

                    batch = resp.json()
                    all_items.extend(batch)

                    total_results = int(resp.headers.get("Total-Results", len(all_items)))
                    start += len(batch)
                    if not batch or start >= total_results:
                        break

                return all_items, latest_version
            except Exception as e:
                print(f"Local delta query failed ({e}); falling back to cloud.")
                self.refresh_connection_status()

        if not self.cloud_client:
            raise RuntimeError("Cloud client unavailable: Zotero credentials missing in keyring.")

        kwargs: dict[str, Any] = {}
        if since_version is not None:
            kwargs["since"] = since_version
        all_items = self.cloud_client.everything(self.cloud_client.items(**kwargs))
        if hasattr(self.cloud_client, "request") and self.cloud_client.request is not None:
            lmv = self.cloud_client.request.headers.get("Last-Modified-Version")
            if lmv:
                latest_version = int(lmv)
        return all_items, latest_version

    def get_read_papers(
        self,
        collection_key: str | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Retrieve primary paper items (excluding standalone attachments/notes)."""
        kwargs = {
            "limit": limit,
            "itemType": "-attachment || note",
        }
        if tag:
            kwargs["tag"] = tag

        if collection_key:
            raw_items = self._get_collection_items_raw(collection_key, **kwargs)
        else:
            raw_items = self._get_items_raw(**kwargs)

        excluded_types = {"attachment", "note", "annotation"}
        return [
            self._parse_item(item)
            for item in raw_items
            if item.get("data", {}).get("itemType") not in excluded_types
        ]

    # -------------------------------------------------------------------------
    # Feature 3: PDF Highlights, Annotations & Full-Text Extraction
    # -------------------------------------------------------------------------
    def _get_pdf_attachments(self, item_key: str) -> list[dict[str, Any]]:
        """Find PDF child attachments for a given paper item key."""
        children = self._get_children_raw(item_key)
        pdf_attachments = [
            c for c in children
            if c.get("data", {}).get("itemType") == "attachment"
            and c.get("data", {}).get("contentType") == "application/pdf"
        ]
        if not pdf_attachments:
            pdf_attachments = [
                c for c in children
                if c.get("data", {}).get("itemType") == "attachment"
                and c.get("data", {}).get("filename", "").lower().endswith(".pdf")
            ]
        return pdf_attachments

    def get_pdf_full_text(self, item_key: str, max_chars: int = 150_000) -> str | None:
        """
        Extract plain full text from a paper's attached PDF (ignoring figures/tables).
        Returns None if no PDF attachment is found or readable.
        """
        pdf_attachments = self._get_pdf_attachments(item_key)
        if not pdf_attachments:
            return None

        pdf_key = pdf_attachments[0]["data"]["key"]
        pdf_bytes: bytes | None = None

        if self.is_local_available:
            try:
                resp = self.http_client.get(
                    f"{self.LOCAL_URL}/items/{pdf_key}/file",
                    follow_redirects=False,
                )
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location", "")
                    if location.startswith("file://"):
                        local_path = Path(unquote(urlparse(location).path))
                        if local_path.exists():
                            pdf_bytes = local_path.read_bytes()
                    elif location:
                        r2 = self.http_client.get(location)
                        if r2.status_code == 200:
                            pdf_bytes = r2.content
                elif resp.status_code == 200 and resp.content:
                    pdf_bytes = resp.content
            except Exception as e:
                print(f"Local PDF fetch failed for {pdf_key}: {e}")

        if pdf_bytes is None and self.cloud_client:
            try:
                pdf_bytes = self.cloud_client.file(pdf_key)
            except Exception as e:
                print(f"Cloud PDF fetch failed for {pdf_key}: {e}")

        if not pdf_bytes:
            return None

        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            pages_text: list[str] = []
            for idx, page in enumerate(reader.pages, start=1):
                txt = (page.extract_text() or "").strip()
                if txt:
                    pages_text.append(f"[Page {idx}]\n{txt}")
            full_text = "\n\n".join(pages_text)
            return full_text[:max_chars] if full_text else None
        except Exception as e:
            print(f"PDF text extraction failed for {pdf_key}: {e}")
            return None

    def get_pdf_annotations(self, item_key: str) -> list[dict[str, Any]]:
        """
        Extract highlights, marginal notes, and quotes attached to a paper's PDF.
        Maps colors to categories (finding, method, limitation, quote).
        Constructs deep links: zotero://open-pdf/library/items/<pdf_key>?page=<page>&annotation=<ann_key>
        """
        pdf_attachments = self._get_pdf_attachments(item_key)
        if not pdf_attachments:
            return []

        annotations_result = []

        for pdf in pdf_attachments:
            pdf_key = pdf["data"]["key"]
            raw_annots = []

            if self.is_local_available:
                try:
                    all_annots = self._local_get("items", {"itemType": "annotation", "limit": 10000})
                    raw_annots = [a for a in all_annots if a.get("data", {}).get("parentItem") == pdf_key]
                except Exception:
                    raw_annots = self._get_children_raw(pdf_key)
            else:
                raw_annots = self._get_children_raw(pdf_key)

            for a in raw_annots:
                data = a.get("data", {})
                if data.get("itemType") != "annotation":
                    continue

                ann_key = data.get("key", "")
                color_hex = (data.get("annotationColor") or "#ffd400").lower()
                category = self.COLOR_MAP.get(color_hex, "other")
                page_str = data.get("annotationPageLabel")
                page = int(page_str) if page_str and str(page_str).isdigit() else 1
                text = (data.get("annotationText") or "").strip()
                comment = (data.get("annotationComment") or "").strip()

                deep_link = (
                    f"zotero://open-pdf/library/items/{pdf_key}"
                    f"?page={page}&annotation={ann_key}"
                )

                annotations_result.append({
                    "key": ann_key,
                    "pdf_key": pdf_key,
                    "paper_key": item_key,
                    "text": text,
                    "comment": comment or None,
                    "color_hex": color_hex,
                    "category": category,
                    "page": page,
                    "deep_link": deep_link,
                })

        annotations_result.sort(key=lambda x: x["page"])
        return annotations_result

    # -------------------------------------------------------------------------
    # Feature 4: Tagging
    # -------------------------------------------------------------------------
    def add_tag_to_item(self, item_key: str, tag: str) -> bool:
        """Add a status or topic tag to a Zotero item."""
        if not self.cloud_client:
            print("Tagging requires cloud client with write permissions.")
            return False
        try:
            item = self.cloud_client.item(item_key)
            current_tags = [t["tag"] for t in item["data"].get("tags", [])]
            if tag not in current_tags:
                self.cloud_client.add_tags(item, tag)
                return True
            return True
        except Exception as e:
            print(f"Error adding tag to item {item_key}: {e}")
            return False
