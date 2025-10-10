from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    success: bool
    api: str
    query: str
    latency_ms: float
    result_urls: list[str] = Field(default_factory=list)
    status_code: int | None = None
    error: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class APIConfig(BaseModel):
    api_key: str
    base_url: str | None = None


class LatencyStats(BaseModel):
    min: float
    p50: float
    p90: float
    p95: float
    p99: float
    max: float
    mean: float


class BenchmarkSummary(BaseModel):
    total_queries: int
    successful_queries: int
    failed_queries: int
    latency: LatencyStats | None = None
    by_search_type: dict[str, dict[str, Any]] = Field(default_factory=dict)


class BenchmarkResult(BaseModel):
    api: str
    execution_mode: Literal["parallel", "sequential"]
    max_workers: int
    queries_count: int
    total_execution_time_ms: float
    timestamp: datetime
    summary: BenchmarkSummary
    results: list[SearchResult]
