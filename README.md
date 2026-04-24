# Deep Research Agent

Multi-round iterative web research powered by [Microsoft Agent Framework (MAF)](https://github.com/microsoft/agent-framework).

## How it works

```
StartExecutor → OutlineAgent → ResearchLoopExecutor → ReportAgent → OutputExecutor
                                   ↑       |
                                   └───────┘ (loop if gaps, max N rounds)
```

1. **OutlineAgent** generates a structured research plan from your query
2. **ResearchAgent** searches the web (DuckDuckGo) and reads pages (trafilatura) for each topic
3. **JudgeAgent** evaluates completeness — if gaps are found, it loops back for more research
4. **ReportAgent** compiles everything into a structured markdown report with citations

## Setup

```bash
uv sync
```

Authentication is handled automatically via the GitHub Copilot SDK — no API keys needed.

## Usage

```bash
uv run deep-research 'How to create compelling manga' --max-rounds 3 -o report.md
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--max-rounds` | 3 | Maximum research iterations |
| `-o, --output` | report.md | Output file path |

## Project Structure

```
deep_research/
  cli.py              # Click CLI entry point
  workflow.py          # MAF WorkflowBuilder definition
  models/state.py      # ResearchState, Finding, ResearchTopic dataclasses
  agents/
    outline.py         # Outline generation agent
    research.py        # Web research agent (with tools)
    report.py          # Report compilation agent
  executors/
    start.py           # StartExecutor — creates initial state
    judge.py           # ResearchLoopExecutor — outline + research + judge loop
    output.py          # ReportExecutor + OutputExecutor — compile and write report
  tools/
    search.py          # web_search — DuckDuckGo search
    fetch.py           # web_fetch — httpx + trafilatura page extraction
```
