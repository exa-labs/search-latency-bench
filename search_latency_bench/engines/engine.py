from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EngineResult:
    result_urls: list[str]
    server_latency_ms: float | None = None


class SearchEngine(ABC):
    @abstractmethod
    async def __call__(self, query: str, num_results: int) -> EngineResult: ...
