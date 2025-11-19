import asyncio
import time
from datetime import datetime, timezone
from statistics import mean, quantiles
from typing import Literal

from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

from .engines import SearchEngine
from .types import BenchmarkResult, BenchmarkSummary, LatencyStats, SearchResult


class BenchmarkProgress:
    def __init__(self) -> None:
        self.failed_count = 0


async def process_single_query(
    engine: SearchEngine,
    query: str,
    num_results: int,
    api_name: str,
    benchmark_progress: BenchmarkProgress | None = None,
) -> SearchResult:
    start_time = time.time()

    try:
        urls = await engine(query, num_results)
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        return SearchResult(
            success=True,
            api=api_name,
            query=query,
            latency_ms=latency_ms,
            result_urls=urls,
            status_code=200,
            timestamp=datetime.now(timezone.utc),
        )

    except Exception as e:
        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        if benchmark_progress:
            benchmark_progress.failed_count += 1

        return SearchResult(
            success=False,
            api=api_name,
            query=query,
            latency_ms=latency_ms,
            error=str(e),
            timestamp=datetime.now(timezone.utc),
        )


async def process_batch_parallel(
    engine: SearchEngine,
    queries: list[str],
    num_results: int,
    api_name: str,
    max_workers: int = 20,
    progress: Progress | None = None,
    task_id: TaskID | None = None,
    benchmark_progress: BenchmarkProgress | None = None,
) -> list[SearchResult]:
    semaphore = asyncio.Semaphore(max_workers)

    async def bounded_process(query: str) -> SearchResult:
        async with semaphore:
            result = await process_single_query(engine, query, num_results, api_name, benchmark_progress)
            if progress and task_id is not None:
                failed_text = (
                    f" ({benchmark_progress.failed_count} failed)"
                    if benchmark_progress and benchmark_progress.failed_count > 0
                    else ""
                )
                progress.update(task_id, advance=1, description=f"Processing {len(queries)} queries{failed_text}")
            return result

    return list(await asyncio.gather(*[bounded_process(q) for q in queries]))


async def process_batch(
    engine: SearchEngine,
    queries: list[str],
    num_results: int,
    api_name: str,
    parallel: bool = True,
    max_workers: int = 20,
    progress: Progress | None = None,
    task_id: TaskID | None = None,
    benchmark_progress: BenchmarkProgress | None = None,
) -> list[SearchResult]:
    if parallel and len(queries) > 1:
        return await process_batch_parallel(
            engine, queries, num_results, api_name, max_workers, progress, task_id, benchmark_progress
        )

    results = []
    for query in queries:
        result = await process_single_query(engine, query, num_results, api_name, benchmark_progress)
        results.append(result)
        if progress and task_id is not None:
            failed_text = (
                f" ({benchmark_progress.failed_count} failed)"
                if benchmark_progress and benchmark_progress.failed_count > 0
                else ""
            )
            progress.update(task_id, advance=1, description=f"Processing {len(queries)} queries{failed_text}")
        if len(queries) > 1:
            await asyncio.sleep(0.1)

    return results


def calculate_summary_stats(results: list[SearchResult]) -> BenchmarkSummary:
    successful = [r for r in results if r.success]

    if not successful:
        return BenchmarkSummary(
            total_queries=len(results),
            successful_queries=0,
            failed_queries=len(results),
        )

    latency_times = [r.latency_ms for r in successful]

    summary = BenchmarkSummary(
        total_queries=len(results),
        successful_queries=len(successful),
        failed_queries=len(results) - len(successful),
    )

    if latency_times:
        if len(latency_times) == 1:
            single_value = latency_times[0]
            summary.latency = LatencyStats(
                min=single_value,
                p50=single_value,
                p90=single_value,
                p95=single_value,
                p99=single_value,
                max=single_value,
                mean=single_value,
            )
        else:
            q = quantiles(latency_times, n=100, method="inclusive")
            summary.latency = LatencyStats(
                min=min(latency_times),
                p50=q[49],
                p90=q[89],
                p95=q[94],
                p99=q[98],
                max=max(latency_times),
                mean=mean(latency_times),
            )

    return summary


async def run_benchmark(
    engine: SearchEngine,
    queries: list[str],
    num_results: int,
    api_name: Literal["exa-auto", "exa-fast", "brave", "perplexity", "parallel"],
    parallel: bool = True,
    max_workers: int = 20,
) -> BenchmarkResult:
    start_time = time.time()
    benchmark_progress = BenchmarkProgress()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task(f"Processing {len(queries)} queries", total=len(queries))
        results = await process_batch(
            engine,
            queries,
            num_results,
            api_name,
            parallel=parallel,
            max_workers=max_workers,
            progress=progress,
            task_id=task,
            benchmark_progress=benchmark_progress,
        )

    total_time = time.time() - start_time

    summary = calculate_summary_stats(results)

    return BenchmarkResult(
        api=api_name,
        execution_mode="parallel" if parallel else "sequential",
        max_workers=max_workers if parallel else 1,
        queries_count=len(queries),
        total_execution_time_ms=total_time * 1000,
        timestamp=datetime.now(timezone.utc),
        summary=summary,
        results=results,
    )
