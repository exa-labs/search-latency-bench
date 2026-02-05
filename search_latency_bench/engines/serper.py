import asyncio
import os

import httpx

from .engine import EngineResult, SearchEngine


class SerperSearchEngine(SearchEngine):
    def __init__(self, api_key: str | None = None) -> None:
        api_key = api_key or os.getenv("SERPER_API_KEY")
        if api_key is None:
            raise ValueError("API key is required for Serper Search")
        self.api_key = api_key
        self._headers = {
            "X-API-KEY": api_key,
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
            "https://google.serper.dev/search",
            json={
                "q": query,
                "num": num_results,
            },
        )

        if response.status_code == 422:
            return []

        if response.status_code != 200:
            raise Exception(f"Serper search failed for '{query}': HTTP {response.status_code}")

        data = response.json()
        results = data.get("organic", [])
        return EngineResult([result.get("link", "") for result in results])

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
