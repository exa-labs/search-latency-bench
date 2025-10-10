# Search Latency Bench

A performance benchmarking tool for evaluating response time characteristics across modern search APIs.

## Quick Start

```bash
cp .env.example .env
# Edit .env with your API keys
```

Credentials needed:
- `EXA_API_KEY` - Exa search API
- `BRAVE_API_KEY` - Brave search API
- `PPLX_API_KEY` - Perplexity search API
- `OPENAI_API_KEY` - For query generation (optional)

## Usage

### Basic Benchmarks

```bash
# Test a single API
uv run bench local --file queries.jsonl --api exa-auto

# Compare all APIs
uv run bench local --file queries.jsonl --api all

# Sample subset of queries
uv run bench local --file queries.jsonl --num-queries 50 --api all
```

### Performance Testing

```bash
# Parallel execution for higher throughput
uv run bench local --file queries.jsonl --api all --parallel --max-workers 20
```

### Query Generation

```bash
# Generate synthetic queries with GPT-5-mini
uv run bench gen --count 100 --api all --parallel
```

### Advanced Usage

```bash
uv run bench local \
  --file queries.jsonl \
  --api all \
  --num-queries 100 \
  --num-results 10 \
  --parallel \
  --max-workers 20 \
  --output results
```

### API Options

- `exa-auto` - Exa with auto mode
- `exa-fast` - Exa with fast/keyword mode
- `brave` - Brave Search
- `perplexity` - Perplexity Search
- `all` - Run all APIs sequentially

## Input Formats

Supports JSON and JSONL query files:

```json
["query 1", "query 2", "query 3"]
```

```jsonl
{"query": "query 1"}
{"query": "query 2"}
```

## Results

Benchmarks generate timestamped JSON files with detailed performance metrics:

```
results/
├── exa-auto_results_20250110_143052.json
├── exa-fast_results_20250110_143052.json
├── brave_results_20250110_143052.json
└── perplexity_results_20250110_143052.json
```

Each result file includes:
- **Latency percentiles** (P50, P90, P95, P99)
- **Aggregate statistics** (min, max, mean)
- **Individual query timings**
- **Success/failure counts**
- **Execution metadata**

## Programmatic Usage

```python
from search_latency_bench import ExaSearchEngine, run_benchmark
from search_latency_bench.engines.exa import SearchType

engine = ExaSearchEngine(type=SearchType.AUTO)
result = await run_benchmark(
    engine=engine,
    queries=["quantum computing", "climate change solutions"],
    num_results=10,
    api_name="exa-auto",
    parallel=True,
)

print(f"P50 latency: {result.summary.latency.p50:.1f}ms")
print(f"P95 latency: {result.summary.latency.p95:.1f}ms")
print(f"Success rate: {result.summary.successful_queries}/{result.summary.total_queries}")
```
