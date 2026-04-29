# Deep Research Agent

Multi-round iterative research agent powered by [Microsoft Agent Framework (MAF)](https://github.com/microsoft/agent-framework).
Supports web search, GitHub search, and combined modes with pluggable search providers.

## How it works

```
Query → OutlineAgent → ResearchLoop → CompressorAgent → ReportAgent → Output
                          ↑    |
                          └────┘  CriticAgent evaluates gaps, loops up to N rounds
```

1. **Outline Agent** — generates a structured research plan (3 topics max) using MAF structured outputs
2. **Query Refiner** — optimizes each topic into targeted search queries
3. **Supervisor** — dispatches research in parallel across registered search providers
4. **Critic Agent** — evaluates completeness and identifies knowledge gaps; loops if needed
5. **Compressor Agent** — deduplicates and merges findings, preserving citations
6. **Report Agent** — compiles everything into a structured markdown report with sources

All agents returning structured data use MAF native `response_format` with Pydantic models — no manual JSON parsing.

## Setup

```bash
uv sync
```

Create a `.env` file with your Azure OpenAI credentials:

```env
AZURE_API_KEY=your-key-here
OPENAI_BASE_URL=https://your-endpoint.openai.azure.com/v1
```

Optional search provider keys:

```env
TAVILY_API_KEY=...       # Tavily web search (preferred)
SEARXNG_URL=...          # Self-hosted SearXNG instance
```

## Usage

```bash
# Web research (default)
uv run deep-research 'How to create deep research' --max-rounds 3 -o report.md

# GitHub-focused research
uv run deep-research 'React state management libraries' --source github

# Combined web + GitHub research
uv run deep-research 'Building RAG pipelines' --source both

# Custom output location
uv run deep-research 'Rust async patterns' -o reports/rust-async.md --research-dir reports
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--max-rounds` | `3` | Maximum research iterations |
| `-o, --output` | `report.md` | Output file path |
| `--source` | `web` | Research source: `web`, `github`, or `both` |
| `--research-dir` | `reports` | Base directory for research artifacts |

## Architecture

### Search Providers

Research sources are pluggable via the `SearchProvider` protocol. Each provider supplies its own tools and instructions:

```python
from deep_research.tools.provider import SearchProvider

class MyProvider:
    name = "my-source"
    instructions = "How to use these tools..."
    tools = [my_search_tool, my_read_tool]

# Register it
from deep_research.tools.registry import register
register(MyProvider())
```

Built-in providers:
- **`WebSearchProvider`** — Tavily → DuckDuckGo → SearXNG fallback chain + page fetching
- **`GitHubSearchProvider`** — GitHub repos/code/issues search via `gh` CLI

### Structured Outputs

Agents that return structured data use MAF's `response_format` with Pydantic models:
- `OutlineResponse` — research topics with subtopics
- `CompressedFindings` — deduplicated findings with sources
- `CriticFeedback` — quality score, gaps, and completion status
- `RefinedQueries` — optimized search queries

### Middleware

All agent calls go through configurable middleware:
- **Token tracking** — cumulative prompt/completion token counts
- **Tool call logging** — timing and result sizes
- **Caching** — deduplicates identical tool calls
- **Retry** — automatic retry with exponential backoff

## Project Structure

```
deep_research/
  cli.py                # Click CLI entry point
  client.py             # OpenAI client factory
  config.py             # Pydantic settings from .env
  log.py                # Colored logger with file handler
  middleware.py          # Token tracking, caching, retry, logging
  utils.py              # Slugify, URL extraction, file I/O
  models/
    state.py            # Pydantic models: ResearchState, Finding, OutlineResponse, etc.
  agents/
    outline.py          # Outline generation (structured output)
    query_refiner.py    # Search query optimization (structured output)
    supervisor.py       # Parallel research dispatch via provider registry
    critic.py           # Research quality evaluation (structured output)
    compressor.py       # Findings deduplication (structured output)
    report.py           # Final report compilation
  tools/
    provider.py         # SearchProvider protocol + built-in implementations
    registry.py         # Provider registry (register/get_providers)
    search.py           # Web search: Tavily → DuckDuckGo → SearXNG
    fetch.py            # Web page fetcher (httpx + trafilatura)
    github_search.py    # GitHub search via gh CLI
    github_read.py      # GitHub file reader via gh CLI
  workflow/
    pipeline.py         # MAF WorkflowBuilder + run_research()
    start_executor.py   # Generates outline, initializes state
    research_executor.py # Multi-round research loop
    report_executor.py  # Compress + compile report
    output_executor.py  # Save report and artifacts to disk
```

## Tech Stack

- Python 3.12, [uv](https://docs.astral.sh/uv/) package manager
- [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) 1.2.0+
- Azure OpenAI (gpt-5.5)
- Pydantic v2 for models and settings
