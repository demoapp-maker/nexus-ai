"""Real-time web search and bounded public-page fetching."""

from __future__ import annotations

import re
from typing import Dict
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from logic.security import validate_public_http_url


class WebSearchTool:
    """Fetch public web data without exposing the backend network."""

    def __init__(self) -> None:
        self.duckduckgo_url = "https://html.duckduckgo.com/html/"
        self.headers = {
            "User-Agent": "NexusAI/1.0 (+https://nexus-ai.local)",
            "Accept": "text/html,application/xhtml+xml",
        }
        self.max_response_bytes = 2_000_000
        self.max_redirects = 3

    async def search(self, query: str, num_results: int = 5) -> Dict:
        query = (query or "").strip()[:500]
        if not query:
            return {"error": "Search query cannot be empty"}
        num_results = max(1, min(int(num_results or 5), 10))

        try:
            timeout = httpx.Timeout(10.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
                response = await client.post(
                    self.duckduckgo_url,
                    data={"q": query},
                    headers=self.headers,
                )
                if response.status_code != 200:
                    return {"error": f"Search failed with status {response.status_code}"}

                soup = BeautifulSoup(response.text, "html.parser")
                results = []
                for result_body in soup.select(".result")[:num_results]:
                    title_node = result_body.select_one(".result__a, .result__title a")
                    snippet_node = result_body.select_one(".result__snippet")
                    link = title_node.get("href", "") if title_node else ""
                    results.append(
                        {
                            "title": title_node.get_text(" ", strip=True) if title_node else "",
                            "url": link,
                            "snippet": snippet_node.get_text(" ", strip=True) if snippet_node else "",
                        }
                    )

                return {
                    "query": query,
                    "results_count": len(results),
                    "results": results,
                    "timestamp": "real-time",
                }
        except Exception as exc:
            return {"error": f"Search error: {exc}"}

    async def _safe_get(self, url: str) -> tuple[str, httpx.Response | None, bytes]:
        current_url = validate_public_http_url(url)
        timeout = httpx.Timeout(15.0, connect=5.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            for _ in range(self.max_redirects + 1):
                # Validate every hop, not just the original URL.
                current_url = validate_public_http_url(current_url)
                async with client.stream("GET", current_url, headers=self.headers) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            return current_url, response, b""
                        current_url = urljoin(current_url, location)
                        continue

                    if response.status_code != 200:
                        return current_url, response, b""

                    content_length = response.headers.get("content-length")
                    if content_length and int(content_length) > self.max_response_bytes:
                        raise ValueError("Fetched page exceeds the response size limit")

                    chunks = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > self.max_response_bytes:
                            raise ValueError("Fetched page exceeds the response size limit")
                        chunks.append(chunk)
                    return current_url, response, b"".join(chunks)

        raise ValueError("Too many redirects")

    async def fetch_url_content(self, url: str) -> Dict:
        """Fetch and extract bounded content from a public URL."""
        try:
            final_url, response, body = await self._safe_get(url)
            if response is None or response.status_code != 200:
                status = response.status_code if response is not None else "unknown"
                return {"error": f"Failed to fetch URL: {status}"}

            content_type = response.headers.get("content-type", "").lower()
            if content_type and not any(
                allowed in content_type for allowed in ("text/", "application/xhtml", "application/xml")
            ):
                return {"error": "The target did not return a text document"}

            soup = BeautifulSoup(body, "html.parser")
            for element in soup(["script", "style", "nav", "footer", "header", "form"]):
                element.decompose()

            title = soup.find("title")
            title_text = title.get_text(" ", strip=True) if title else ""
            main_content = soup.find("article") or soup.find("main") or soup.find("body")
            text_content = (
                main_content.get_text(separator="\n", strip=True) if main_content else ""
            )
            text_content = text_content[:3_000]
            meta_desc = soup.find("meta", attrs={"name": "description"})
            description = meta_desc.get("content", "") if meta_desc else ""

            return {
                "url": final_url,
                "title": title_text,
                "description": description[:500],
                "content": text_content[:2_000],
                "word_count": len(text_content.split()),
            }
        except Exception as exc:
            return {"error": f"Fetch error: {exc}"}

    async def get_people_also_ask(self, query: str) -> Dict:
        """Return question-like snippets; this is not a Google PAA API."""
        try:
            search_result = await self.search(f"{query} questions", num_results=5)
            questions = []
            for result in search_result.get("results", []):
                questions.extend(re.findall(r"[^.!?]*\?", result.get("snippet", "")))
            return {
                "query": query,
                "questions": list(dict.fromkeys(q.strip() for q in questions))[:5],
                "source": "question-like phrases extracted from search snippets",
            }
        except Exception as exc:
            return {"error": f"Question extraction failed: {exc}"}

    async def get_related_searches(self, query: str) -> Dict:
        try:
            search_result = await self.search(f"related: {query}", num_results=5)
            related_terms = []
            for result in search_result.get("results", []):
                title = result.get("title", "")
                clean_title = title.replace(query, "").strip(" -|:")
                if len(clean_title) > 5:
                    related_terms.append(clean_title)
            return {
                "query": query,
                "related_searches": list(dict.fromkeys(related_terms))[:8],
            }
        except Exception as exc:
            return {"error": f"Related search extraction failed: {exc}"}


web_search_tool = WebSearchTool()
