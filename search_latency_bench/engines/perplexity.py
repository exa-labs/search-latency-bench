from perplexity import AsyncPerplexity

from .engine import SearchEngine


class PerplexitySearchEngine(SearchEngine):
    def __init__(self, api_key: str | None = None) -> None:
        self.client = AsyncPerplexity(api_key=api_key)

    async def __call__(self, query: str, num_results: int) -> list[str]:
        search_response = await self.client.search.create(
            query=query,
            max_results=num_results,
        )
        return [result.url for result in search_response.results]
