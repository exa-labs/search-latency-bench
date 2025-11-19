import os

from parallel import AsyncParallel

from .engine import SearchEngine


class ParallelSearchEngine(SearchEngine):
    def __init__(self, api_key: str | None = None) -> None:
        api_key = api_key or os.getenv("PARALLEL_API_KEY")
        if api_key is None:
            raise ValueError("API key is required for Parallel Search")
        self.client = AsyncParallel(api_key=api_key)

    async def __call__(self, query: str, num_results: int) -> list[str]:
        search_response = await self.client.beta.search(
            search_queries=[query],
            max_results=num_results,
            mode="one-shot",
        )
        return [result.url for result in search_response.results]
