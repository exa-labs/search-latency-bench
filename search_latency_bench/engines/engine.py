from abc import ABC, abstractmethod


class SearchEngine(ABC):
    @abstractmethod
    async def __call__(self, query: str, num_results: int) -> list[str]: ...
