from perplexity import AsyncPerplexity

from .engine import EngineResult, SearchEngine


def _parse_server_time_ms(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        raw = value.strip().lower()
        try:
            if raw.endswith("ms"):
                return float(raw[:-2].strip())
            if raw.endswith("s"):
                return float(raw[:-1].strip()) * 1000
            return float(raw)
        except ValueError:
            return None
    return None


class PerplexitySearchEngine(SearchEngine):
    def __init__(self, api_key: str | None = None) -> None:
        self.client = AsyncPerplexity(api_key=api_key)

    async def __call__(self, query: str, num_results: int) -> EngineResult:
        search_response = await self.client.search.create(
            query=query,
            max_results=num_results,
        )
        return EngineResult(
            [result.url for result in search_response.results],
            server_latency_ms=_parse_server_time_ms(search_response.server_time),
        )
