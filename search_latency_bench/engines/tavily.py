import asyncio
import os
from enum import Enum

import httpx

from .engine import EngineResult, SearchEngine


def _parse_response_time_ms(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) * 1000
    if isinstance(value, str):
        raw = value.strip().lower()
        try:
            if raw.endswith("ms"):
                return float(raw[:-2].strip())
            if raw.endswith("s"):
                return float(raw[:-1].strip()) * 1000
            return float(raw) * 1000
        except ValueError:
            return None
    return None


class SearchDepth(str, Enum):
    BASIC = "basic"
    FAST = "fast"
    ULTRA_FAST = "ultra-fast"
    ADVANCED = "advanced"


class TavilySearchEngine(SearchEngine):
    def __init__(
        self,
        api_key: str | None = None,
        search_depth: SearchDepth = SearchDepth.BASIC,
    ) -> None:
        api_key = api_key or os.getenv("TAVILY_API_KEY")
        if api_key is None:
            raise ValueError("API key is required for Tavily Search")
        self.api_key = api_key
        self.search_depth = search_depth
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(headers=self._headers, timeout=30.0)
        return self._client

    async def __call__(self, query: str, num_results: int) -> EngineResult:
        response = await self.client.post(
            "https://api.tavily.com/search",
            json={
                "query": query,
                "max_results": num_results,
                "search_depth": self.search_depth,
            },
        )

        if response.status_code == 422:
            return []

        if response.status_code != 200:
            raise Exception(f"Tavily search failed for '{query}': HTTP {response.status_code}")

        data = response.json()
        results = data.get("results", [])
        return EngineResult(
            [result.get("url", "") for result in results],
            server_latency_ms=_parse_response_time_ms(data.get("response_time")),
        )

    def __del__(self) -> None:
        if self._client and not self._client.is_closed:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._client.aclose())
            except RuntimeError:
                try:
                    asyncio.run(self._client.aclose())
                except Exception:
                    self._client = None
