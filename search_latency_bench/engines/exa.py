import os
from enum import Enum

from exa_py import AsyncExa

from .engine import SearchEngine


class SearchType(str, Enum):
    AUTO = "auto"
    FAST = "fast"


class ExaSearchEngine(SearchEngine):
    def __init__(
        self,
        api_key: str | None = None,
        type: SearchType = SearchType.FAST,
    ) -> None:
        api_key = api_key or os.getenv("EXA_API_KEY")
        if api_key is None:
            raise ValueError("API key is required for Exa Search")
        self.client = AsyncExa(api_key=api_key)
        self.type = type

    async def __call__(self, query: str, num_results: int) -> list[str]:
        search_response = await self.client.search(
            query=query,
            num_results=num_results,
            type=self.type,
        )
        return [result.url for result in search_response.results]
