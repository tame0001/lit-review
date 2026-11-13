"""
Scite.ai Service
----------------
This service handles integration with the Scite.ai API to provide citation 
context and research impact metrics.
Uses httpx2 for standardized HTTP client requests.

Credentials are securely retrieved via the system keyring (backend/app/config.py).

Feature List:
1. Fetch Citation Tallies: Get supporting, mentioning, and contrasting citation counts for a given DOI.
2. Get Contrasting Snippets: Extract specific text snippets where other authors have 
   disputed or contrasted a paper's findings (critical for research gap identification).
3. Batch Processing: Ability to process lists of DOIs for triage prioritization.
4. Caching: Cache API responses locally to minimize redundant requests and respect rate limits.
"""

from typing import Any
import httpx2
from ..config import settings


class SciteService:
    BASE_URL = "https://api.scite.ai"

    def __init__(self, api_key: str | None = None, timeout: float = 15.0):
        self.api_key = api_key or settings.scite_api_key
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        self.timeout = timeout
        self.client = httpx2.Client(headers=self.headers, timeout=self.timeout)

    def get_tallies(self, doi: str) -> dict[str, int]:
        """
        Feature 1: Fetch citation tallies (supporting, contrasting, mentioning).
        Works with or without an API key (public tallies endpoint).
        """
        if not doi:
            return {"supporting": 0, "contrasting": 0, "mentioning": 0}

        try:
            resp = self.client.get(f"{self.BASE_URL}/tallies/{doi}")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "supporting": data.get("supporting", 0),
                    "contrasting": data.get("contrasting", 0),
                    "mentioning": data.get("mentioning", 0),
                    "total": data.get("total", 0),
                }
        except Exception as e:
            print(f"Scite tallies request failed for DOI {doi}: {e}")

        return {"supporting": 0, "contrasting": 0, "mentioning": 0, "total": 0}

    def get_contrasting_snippets(self, doi: str) -> list[dict[str, Any]]:
        """
        Feature 2: Extract text snippets where other authors disputed or contrasted this paper.
        Requires Scite subscription / API access.
        """
        if not doi:
            return []

        try:
            resp = self.client.get(f"{self.BASE_URL}/citations/{doi}?classification=contrasting")
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {
                        "citing_doi": c.get("source", {}).get("doi"),
                        "snippet": c.get("snippet"),
                        "citing_title": c.get("source", {}).get("title"),
                    }
                    for c in data.get("citations", [])
                ]
        except Exception as e:
            print(f"Scite contrasting snippets request failed for DOI {doi}: {e}")

        return []
