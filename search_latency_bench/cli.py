import asyncio
import json
from pathlib import Path
from typing import Literal

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .benchmark import run_benchmark
from .engines import (
    BraveSearchEngine,
    ExaSearchEngine,
    ParallelSearchEngine,
    PerplexitySearchEngine,
    SerperSearchEngine,
    SearchDepth,
    TavilySearchEngine,
)
from .querygen import generate_queries
from .types import BenchmarkResult

app = typer.Typer()
console = Console()


def load_queries(file_path: str, num_queries: int | None = None) -> list[str]:
    path = Path(file_path)
    queries = []

    with open(path) as f:
        if path.suffix == ".jsonl":
            for line in f:
                try:
                    data = json.loads(line.strip())
                    query = data.get("query", "").strip()
                    if query:
                        queries.append(query)
                except json.JSONDecodeError:
                    continue
        elif path.suffix == ".json":
            data = json.load(f)
            if isinstance(data, list):
                queries = [q if isinstance(q, str) else q.get("query", "") for q in data]

    if num_queries:
        import random

        queries = random.sample(queries, min(num_queries, len(queries)))

    return queries


def extract_query_from_example(example: dict) -> str:
    preferred_fields = ("query", "question", "prompt", "instruction", "text")
    for field in preferred_fields:
        value = example.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for value in example.values():
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def randomize_queries(queries: list[str], seed: int | None = None) -> list[str]:
    rng = random.Random(seed)
    current_year = datetime.now().year
    year_re = re.compile(r"\b(19\d{2}|20\d{2})\b")
    num_re = re.compile(r"\b\d+\b")

    def replace_year(match: re.Match[str]) -> str:
        return str(rng.randint(1990, current_year))

    def replace_num(match: re.Match[str]) -> str:
        token = match.group(0)
        try:
            value = int(token)
        except ValueError:
            return token
        if len(token) == 4 and 1900 <= value <= current_year:
            return token
        if len(token) == 1:
            return str(rng.randint(0, 9))
        return "".join(str(rng.randint(0, 9)) for _ in range(len(token)))

    randomized = []
    for query in queries:
        updated = year_re.sub(replace_year, query)
        updated = num_re.sub(replace_num, updated)
        if updated == query:
            updated = f"{updated} {rng.randint(1990, current_year)}"
        randomized.append(updated)
    return randomized


def print_summary(result: BenchmarkResult) -> None:
    console.print(f"\n[bold cyan]{result.api.upper()} Results[/bold cyan]")
    console.print(f"Successful: {result.summary.successful_queries}/{result.summary.total_queries}")
    console.print(f"Total time: {result.total_execution_time_ms:.0f}ms")

    if result.summary.latency:
        table = Table(title="Latency")
        table.add_column("Metric", style="cyan")
        table.add_column("Value (ms)", style="green")

        stats = result.summary.latency
        table.add_row("Min", f"{stats.min:.1f}")
        table.add_row("P50", f"{stats.p50:.1f}")
        table.add_row("P90", f"{stats.p90:.1f}")
        table.add_row("P95", f"{stats.p95:.1f}")
        table.add_row("P99", f"{stats.p99:.1f}")
        table.add_row("Max", f"{stats.max:.1f}")
        table.add_row("Mean", f"{stats.mean:.1f}")

        console.print(table)


def print_combined_summary(results: list[BenchmarkResult]) -> None:
    table = Table(title="Latency (ms)")
    table.add_column("Metric", style="cyan")
    for result in results:
        table.add_column(result.api.upper(), style="green")

    metrics = ["Min", "P50", "P90", "P95", "P99", "Max", "Mean"]
    metric_keys = ["min", "p50", "p90", "p95", "p99", "max", "mean"]

    for metric, key in zip(metrics, metric_keys):
        row = [metric]
        for result in results:
            if result.summary.latency:
                value = getattr(result.summary.latency, key)
                row.append(f"{value:.1f}")
            else:
                row.append("N/A")
        table.add_row(*row)

    console.print("\n")
    console.print(table)


async def run_benchmark_for_apis(
    queries: list[str],
    api: str,
    num_results: int,
    parallel: bool,
    max_workers: int,
    output: str,
) -> None:
    output_dir = Path(output)
    output_dir.mkdir(exist_ok=True)

    if api == "all":
        apis_to_test: list[
            Literal[
                "exa-auto",
                "exa-fast",
                "brave",
                "perplexity",
                "parallel",
                "tavily",
                "tavily-ultra-fast",
                "serper",
            ]
        ] = [
            "exa-auto",
            "exa-fast",
            "brave",
            "perplexity",
            "parallel",
            "tavily",
            "tavily-ultra-fast",
            "serper",
        ]  # type: ignore[assignment]
    else:
        apis_to_test = [api]  # type: ignore[assignment]

    async def run_single_api(api_name: str) -> BenchmarkResult | None:
        console.print(f"\n[bold yellow]Running benchmark for {api_name.upper()}[/bold yellow]")

        try:
            match api_name:
                case "exa-auto":
                    from .engines.exa import SearchType

                    engine = ExaSearchEngine(type=SearchType.AUTO)
                case "exa-fast":
                    from .engines.exa import SearchType

                    engine = ExaSearchEngine(type=SearchType.FAST)
                case "exa-instant":
                    from .engines.exa import SearchType

                    engine = ExaSearchEngine(type=SearchType.INSTANT)
                case "brave":
                    engine = BraveSearchEngine()
                case "perplexity":
                    engine = PerplexitySearchEngine()
                case "parallel":
                    engine = ParallelSearchEngine()
                case "tavily":
                    engine = TavilySearchEngine(search_depth=SearchDepth.BASIC)
                case "tavily-ultra-fast":
                    engine = TavilySearchEngine(search_depth=SearchDepth.ULTRA_FAST)
                case "serper":
                    engine = SerperSearchEngine()
                case _:
                    raise ValueError(f"Unknown API: {api_name}")

            result = await run_benchmark(
                engine=engine,
                queries=queries,
                num_results=num_results,
                api_name=api_name,  # type: ignore[arg-type]
                parallel=parallel,
                max_workers=max_workers,
            )

            timestamp = result.timestamp.strftime("%Y%m%d_%H%M%S")
            result_file = output_dir / f"{api_name}_results_{timestamp}.json"
            with open(result_file, "w") as f:
                json.dump(result.model_dump(mode="json"), f, indent=2, default=str)
            console.print(f"[green]Saved results to {result_file}[/green]")

            return result
        except Exception as e:
            console.print(f"[red]Error running {api_name}: {e}[/red]")
            return None

    results: list[BenchmarkResult] = []

    for api_name in apis_to_test:
        result = await run_single_api(api_name)
        if result:
            results.append(result)

    if len(results) > 1:
        print_combined_summary(results)
    elif len(results) == 1:
        print_summary(results[0])

    console.print("\n[bold green]Benchmark complete![/bold green]")


@app.command()
def local(
    file: str = typer.Option(..., help="Path to queries file (.json or .jsonl)"),
    api: str = typer.Option(
        "all",
        help="API to test (exa-auto/exa-fast/exa-instant/brave/perplexity/parallel/tavily/serper/all)",
    ),
    num_queries: int | None = typer.Option(None, help="Number of queries to sample"),
    num_results: int = typer.Option(10, help="Number of results per query"),
    parallel: bool = typer.Option(False, help="Run queries in parallel"),
    max_workers: int = typer.Option(20, help="Max parallel workers"),
    output: str = typer.Option("results", help="Output directory"),
) -> None:
    load_dotenv()

    queries = load_queries(file, num_queries)
    console.print(f"[bold]Loaded {len(queries)} queries[/bold]")

    asyncio.run(
        run_benchmark_for_apis(
            queries=queries,
            api=api,
            num_results=num_results,
            parallel=parallel,
            max_workers=max_workers,
            output=output,
        )
    )


@app.command()
def gen(
    count: int = typer.Option(..., help="Number of queries to generate"),
    api: str = typer.Option(
        "all",
        help="API to test (exa-auto/exa-fast/exa-instant/brave/perplexity/parallel/tavily/serper/all)",
    ),
    num_results: int = typer.Option(10, help="Number of results per query"),
    parallel: bool = typer.Option(False, help="Run queries in parallel"),
    max_workers: int = typer.Option(20, help="Max parallel workers"),
    output: str = typer.Option("results", help="Output directory"),
    save_queries: str | None = typer.Option(None, help="Save generated queries to a JSON file"),
) -> None:
    load_dotenv()

    console.print(f"[bold]Generating {count} queries using GPT-5-mini...[/bold]")
    queries = asyncio.run(generate_queries(count))
    console.print(f"[bold]Generated {len(queries)} queries[/bold]")

    if save_queries:
        save_path = Path(save_queries)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w") as f:
            json.dump(queries, f, indent=2)
        console.print(f"[green]Saved queries to {save_path}[/green]")

    asyncio.run(
        run_benchmark_for_apis(
            queries=queries,
            api=api,
            num_results=num_results,
            parallel=parallel,
            max_workers=max_workers,
            output=output,
        )
    )


@app.command()
def seal0(
    api: str = typer.Option(
        "all",
        help="API to test (exa-auto/exa-fast/exa-instant/brave/perplexity/parallel/tavily/serper/all)",
    ),
    num_queries: int | None = typer.Option(None, help="Number of queries to sample"),
    num_results: int = typer.Option(10, help="Number of results per query"),
    parallel: bool = typer.Option(False, help="Run queries in parallel"),
    max_workers: int = typer.Option(20, help="Max parallel workers"),
    output: str = typer.Option("results", help="Output directory"),
    randomize: bool = typer.Option(
        True,
        "--randomize/--no-randomize",
        help="Randomize dates/numbers to reduce cache hits",
    ),
    seed: int | None = typer.Option(None, help="Random seed for query randomization"),
) -> None:
    load_dotenv()

    from datasets import load_dataset

    console.print("[bold]Loading vtllms/sealqa (seal_0)...[/bold]")
    dataset_obj = load_dataset("vtllms/sealqa", "seal_0", split="test", streaming=True)

    queries = []
    for example in dataset_obj:
        query = extract_query_from_example(example)
        if query:
            queries.append(query)
        if num_queries and len(queries) >= num_queries:
            break

    if randomize:
        queries = randomize_queries(queries, seed=seed)
        console.print("[bold]Randomized queries to reduce cache hits[/bold]")

    console.print(f"[bold]Loaded {len(queries)} queries from seal_0[/bold]")

    asyncio.run(
        run_benchmark_for_apis(
            queries=queries,
            api=api,
            num_results=num_results,
            parallel=parallel,
            max_workers=max_workers,
            output=output,
        )
    )


@app.command()
def dataset(
    name: str = typer.Option(..., help="HuggingFace dataset name (e.g., microsoft/ms_marco)"),
    config: str | None = typer.Option(None, help="Dataset configuration"),
    split: str = typer.Option("train", help="Dataset split"),
    query_field: str = typer.Option("query", help="Field name containing queries"),
    api: str = typer.Option(
        "all",
        help="API to test (exa-auto/exa-fast/exa-instant/brave/perplexity/tavily/serper/all)",
    ),
    num_queries: int | None = typer.Option(None, help="Number of queries to sample"),
    num_results: int = typer.Option(10, help="Number of results per query"),
    parallel: bool = typer.Option(False, help="Run queries in parallel"),
    max_workers: int = typer.Option(20, help="Max parallel workers"),
    output: str = typer.Option("results", help="Output directory"),
    save_queries: str | None = typer.Option(None, help="Save loaded queries to a JSON file"),
) -> None:
    load_dotenv()

    from datasets import load_dataset

    console.print(f"[bold]Loading dataset {name}...[/bold]")

    if config:
        dataset_obj = load_dataset(name, config, split=split, streaming=True)
    else:
        dataset_obj = load_dataset(name, split=split, streaming=True)

    queries = []
    for example in dataset_obj:
        if query_field in example:
            queries.append(example[query_field])
        if num_queries and len(queries) >= num_queries:
            break

    console.print(f"[bold]Loaded {len(queries)} queries from {name}[/bold]")

    if save_queries:
        save_path = Path(save_queries)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w") as f:
            json.dump(queries, f, indent=2)
        console.print(f"[green]Saved queries to {save_path}[/green]")

    asyncio.run(
        run_benchmark_for_apis(
            queries=queries,
            api=api,
            num_results=num_results,
            parallel=parallel,
            max_workers=max_workers,
            output=output,
        )
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
