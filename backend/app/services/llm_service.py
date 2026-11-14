"""
LLM Service (Purdue GenAI Studio)
---------------------------------
Provides AI-assisted paper screening, prioritization, and research gap extraction
using Purdue RCAC GenAI Studio (https://genai.rcac.purdue.edu/api).
Uses httpx2 for standardized HTTP requests and keyring (settings.genai_api_key) for credentials.

Functionality / Feature List:
1. Initialize & Verify Purdue GenAI Client: [IMPLEMENTED]
   - Connect to https://genai.rcac.purdue.edu/api/models using keyring GENAI_API_KEY.
   - List available hosted models and verify account connectivity.

2. Unread Paper Relevance Scoring: [PENDING]
   - Given a paper's title + abstract and your active research topic,
     score relevance (0-50 pts) and provide a 1-sentence rationale.

3. Structured Extraction from Full-Text / Abstract: [PENDING]
   - Extract methodology, dataset/domain, and explicit limitations/future work
     using a large-context model (e.g. gemma4:26b-a4b or qwen3.8:27b).

4. Cross-Paper Research Gap Synthesis: [PENDING]
   - Synthesize recurring limitations across multiple papers into candidate research gaps.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import math
import re
import threading
from datetime import datetime
from typing import Any, Callable
import httpx2
from ..config import settings


class LLMService:
    BASE_URL = "https://genai.rcac.purdue.edu/api"

    def __init__(
        self,
        model: str = "qwen3.8:27b",
        api_key: str | None = None,
        timeout: float = 300.0,
        max_concurrency: int = 10,
    ):
        self.model = model
        self.api_key = api_key or settings.genai_api_key
        if not self.api_key:
            raise ValueError(
                "Missing GENAI_API_KEY: Store it in system keyring via "
                "'keyring set lit-review GENAI_API_KEY'."
            )

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate",
        }
        self.client = httpx2.Client(headers=self.headers, timeout=timeout)
        self.max_concurrency = max(1, min(10, max_concurrency))
        self._concurrency_sem = threading.BoundedSemaphore(self.max_concurrency)

    def verify_connection(self) -> dict[str, Any]:
        """
        Feature 1: Verify Purdue GenAI Studio connectivity and retrieve available models.
        """
        try:
            resp = self.client.get(f"{self.BASE_URL}/models")
            resp.raise_for_status()
            payload = resp.json()

            # OpenAI-compatible / OpenWebUI responses typically wrap models under "data"
            raw_models = payload.get("data", payload if isinstance(payload, list) else [])
            model_ids = [m.get("id") for m in raw_models if isinstance(m, dict) and m.get("id")]

            return {
                "status": "connected",
                "configured_model": self.model,
                "configured_model_available": self.model in model_ids,
                "available_models_count": len(model_ids),
                "available_models": model_ids,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
            }

    def _chat_json(self, prompt: str, temperature: float = 0.1) -> dict[str, Any]:
        """Send a concurrency-capped chat completion request and parse JSON."""
        body = {
            "model": self.model,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        with self._concurrency_sem:
            resp = self.client.post(f"{self.BASE_URL}/chat/completions", json=body)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()

        # Strip optional markdown code fences (```json ... ```)
        fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, re.DOTALL)
        if fenced:
            content = fenced.group(1)
        return json.loads(content)

    def run_parallel(
        self,
        items: list[Any],
        worker_fn: Callable[[Any], Any],
        max_workers: int | None = None,
    ) -> list[Any]:
        """
        Execute `worker_fn` across `items` in parallel, capped at `self.max_concurrency`
        (default <= 10).
        """
        if not items:
            return []
        workers = min(len(items), max_workers or self.max_concurrency, self.max_concurrency)
        results: list[Any] = [None] * len(items)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_idx = {executor.submit(worker_fn, item): idx for idx, item in enumerate(items)}
            for future in as_completed(future_to_idx):
                idx = future_to_idx[future]
                results[idx] = future.result()
        return results

    def score_paper_relevance(
        self,
        title: str,
        abstract: str,
        research_focuses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Feature 2: Score a paper's relevance to active research focuses (0-50 pts).
        Uses Title + Abstract for fast screening.
        Returns: {'relevance_score': float, 'matched_focus': str, 'rationale': str}
        """
        if not research_focuses:
            return {"relevance_score": 0.0, "matched_focus": "", "rationale": "No active research focuses."}

        focus_list = "\n".join(
            f"- {f.get('title')}: {f.get('description', '')}"
            for f in research_focuses
        )
        prompt = f"""Rate how relevant this academic paper is to ANY of the user's active research focuses.
Active Research Focuses:
{focus_list}

Paper Title: {title}
Paper Abstract: {abstract or 'No abstract provided.'}

Return ONLY a valid JSON object with these exact keys:
- "rating": integer from 0 to 5 (0 = completely unrelated, 1 = tangential, 3 = moderately relevant, 5 = directly addresses a research focus)
- "matched_focus": string (title of the best-matching research focus, or "None")
- "rationale": string (1 concise sentence explaining why this paper is or is not relevant)
"""
        result = self._chat_json(prompt, temperature=0.1)
        rating = max(0, min(5, int(result.get("rating", 0))))
        return {
            "relevance_score": float(rating * 10),
            "matched_focus": result.get("matched_focus", ""),
            "rationale": result.get("rationale", ""),
        }

    @staticmethod
    def calculate_priority_score(
        relevance_score: float,
        total_citations: int = 0,
        year: int | None = None,
        manual_bonus: float = 0.0,
    ) -> dict[str, float]:
        """
        Calculate total priority score (high-to-low ranking, no tiers):
        total = relevance (0-50) + citations (0-35) + recency (0-15) + manual_bonus
        """
        citation_score = min(35.0, round(11.5 * math.log10(max(0, total_citations) + 1), 1))

        recency_score = 0.0
        if year:
            age = max(0, datetime.now().year - year)
            if age <= 1:
                recency_score = 15.0
            elif age <= 3:
                recency_score = 10.0
            elif age <= 5:
                recency_score = 5.0

        total = round(relevance_score + citation_score + recency_score + manual_bonus, 1)
        return {
            "priority_score": total,
            "relevance_score": relevance_score,
            "citation_score": citation_score,
            "recency_score": recency_score,
            "manual_bonus": manual_bonus,
        }

    @staticmethod
    def _prepare_paper_text(text: str, max_chars: int = 35_000) -> str:
        """
        Strip trailing References/Bibliography and, for very long papers, preserve
        both the beginning (Abstract, Intro, Methods, Results) and end (Discussion, Limitations, Conclusion).
        """
        ref_match = re.search(r"\n\s*(?:References|Bibliography)\s*\n", text, re.IGNORECASE)
        body = text[:ref_match.start()] if ref_match else text
        if len(body) <= max_chars:
            return body
        head = int(max_chars * 0.7)
        tail = max_chars - head
        return f"{body[:head]}\n\n[... middle section truncated ...]\n\n{body[-tail:]}"

    def extract_structured_insights(
        self,
        title: str,
        text: str,
    ) -> dict[str, Any]:
        """
        Feature 3: Extract method of study, key findings, and limitations
        from full-text PDF (or abstract fallback).
        """
        prepared_text = self._prepare_paper_text(text)

        prompt = f"""Analyze the following academic paper and extract structured research insights.
Return ONLY a valid JSON object with these exact keys:
- "method_of_study": string (concise 1-3 sentence summary of study design, sample/dataset, and analytical methods)
- "key_findings": list of strings (3-5 clear, specific findings with quantitative results if present)
- "limitations": list of strings (2-4 explicit limitations, assumptions, or future research gaps noted by the authors)

Paper Title: {title}

Paper Text:
{prepared_text}
"""
        result = self._chat_json(prompt, temperature=0.1)
        return {
            "method_of_study": result.get("method_of_study", ""),
            "key_findings": result.get("key_findings", []),
            "limitations": result.get("limitations", []),
        }

    def analyze_paper_content(
        self,
        title: str,
        text: str,
        research_focuses: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Combined single-request analysis (full-text preferred, abstract fallback):
        scores relevance (0-50 pts) against active research focuses AND extracts
        method_of_study, key_findings, and limitations in one LLM call.
        """
        prepared_text = self._prepare_paper_text(text)
        focus_list = "\n".join(
            f"- {f.get('title')}: {f.get('description', '')}"
            for f in research_focuses
        ) or "- None provided"

        prompt = f"""Analyze the following academic paper: rate its relevance to the user's active research focuses AND extract structured research insights.

Active Research Focuses:
{focus_list}

Return ONLY a valid JSON object with these exact keys:
- "rating": integer from 0 to 5 (0 = completely unrelated to all focuses, 1 = tangential, 3 = moderately relevant, 5 = directly addresses a research focus)
- "matched_focus": string (title of the best-matching research focus, or "None")
- "rationale": string (1 concise sentence explaining why this paper is or is not relevant)
- "method_of_study": string (concise 1-3 sentence summary of study design, sample/dataset, and analytical methods)
- "key_findings": list of strings (3-5 clear, specific findings with quantitative results if present)
- "limitations": list of strings (2-4 explicit limitations, assumptions, or future research gaps noted by the authors)

Paper Title: {title}

Paper Text:
{prepared_text}
"""
        result = self._chat_json(prompt, temperature=0.1)
        rating = max(0, min(5, int(result.get("rating", 0)))) if research_focuses else 0
        return {
            "relevance_score": float(rating * 10),
            "matched_focus": result.get("matched_focus", ""),
            "rationale": result.get("rationale", ""),
            "method_of_study": result.get("method_of_study", ""),
            "key_findings": result.get("key_findings", []),
            "limitations": result.get("limitations", []),
        }

    def synthesize_research_gaps(
        self,
        topic: str,
        paper_limitations: list[dict[str, Any]],
    ) -> str:
        """
        Feature 4: Synthesize recurring limitations across multiple papers into candidate research gaps.
        """
        raise NotImplementedError("Feature 4: Cross-Paper Gap Synthesis not implemented")
