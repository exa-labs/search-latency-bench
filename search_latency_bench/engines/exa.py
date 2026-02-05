import os
from enum import Enum

from exa_py import AsyncExa

from .engine import EngineResult, SearchEngine


class SearchType(str, Enum):
    AUTO = "auto"
    FAST = "fast"
    INSTANT = "instant"


class ExaSearchEngine(SearchEngine):
    def __init__(
        self,
        api_key: str | None = None,
        type: SearchType = SearchType.FAST,
        flags: list[str] | None = None,
    ) -> None:
        api_key = api_key or os.getenv("EXA_API_KEY")
        if api_key is None:
            raise ValueError("API key is required for Exa Search")
        self.client = AsyncExa(api_key=api_key)
        self.type = type
        self.flags = flags

    async def __call__(self, query: str, num_results: int) -> EngineResult:
        params: dict[str, object] = {
            "query": query,
            "num_results": num_results,
            "type": self.type,
        }
        if self.flags:
            params["flags"] = self.flags
        search_response = await self.client.search(**params)
        return EngineResult(
            [result.url for result in search_response.results],
            server_latency_ms=search_response.search_time,
        )
