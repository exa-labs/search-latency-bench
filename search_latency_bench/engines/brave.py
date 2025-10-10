import asyncio
import os

import httpx

from .engine import SearchEngine


class BraveSearchEngine(SearchEngine):
    def __init__(self, api_key: str | None = None) -> None:
        api_key = api_key or os.getenv("BRAVE_API_KEY")
        if api_key is None:
            raise ValueError("API key is required for Brave Search")
        self.api_key = api_key
        self._headers = {
            "X-Subscription-Token": api_key,
            "Accept": "application/json",
        }
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(headers=self._headers, timeout=30.0)
        return self._client

    async def __call__(self, query: str, num_results: int) -> list[str]:
        response = await self.client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={
                "q": query,
                "count": num_results,
            },
        )

        if response.status_code == 422:
            return []

        if response.status_code != 200:
            raise Exception(f"Brave search failed for '{query}': HTTP {response.status_code}")

        data = response.json()
        results = data.get("web", {}).get("results", [])
        return [result.get("url", "") for result in results]

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
