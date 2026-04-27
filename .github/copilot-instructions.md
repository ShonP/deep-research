# Copilot Instructions for deep-research

## Project Overview
Multi-round iterative research agent powered by Microsoft Agent Framework (MAF).
Supports web search (DuckDuckGo), GitHub search (gh CLI), and combined modes.

## Tech Stack
- Python 3.12, uv package manager
- Microsoft Agent Framework (MAF) 1.2.0 — workflows, agents, middleware, checkpointing
- agent-framework-openai — OpenAIChatCompletionClient for Azure OpenAI
- Azure OpenAI: gpt-5.5 model via OPENAI_BASE_URL + AZURE_API_KEY env vars
- Click CLI

## Code Standards
- **Max 200 lines per file** — split into modules when needed
- Self-descriptive code — no comments explaining obvious things
- Type hints everywhere
- Prefix interfaces/protocols with `I` if using protocols
- Use `from __future__ import annotations` in every file
- Use Pydantic v2 for models, settings, and validation
- Use `pydantic-settings` for environment config (BaseSettings)
- Async functions where MAF requires it
- Use MAF native features: @tool, FunctionMiddleware, AgentMiddleware, FileCheckpointStorage, WorkflowBuilder, Executors
- Don't reinvent what MAF provides natively

## File Structure
```
deep_research/
  cli.py              # Click CLI (max 60 lines)
  client.py            # OpenAI client factory
  log.py              # Colored logger with file handler
  middleware.py        # FunctionMiddleware + AgentMiddleware implementations
  utils.py            # Slugify, URL extraction, file I/O helpers
  __init__.py
  models/
    state.py          # ResearchState, Finding, ResearchTopic dataclasses
    __init__.py
  agents/
    outline.py        # Outline generation agent
    research.py       # Web research agent
    github_research.py # GitHub research agent
    report.py         # Report compilation agent
    __init__.py
  tools/
    search.py         # DuckDuckGo web search (@tool)
    fetch.py          # Web page fetcher (@tool)
    github_search.py  # GitHub search via gh CLI (@tool)
    github_read.py    # GitHub file reader via gh CLI (@tool)
    __init__.py
  workflow/
    pipeline.py       # Main workflow builder + run_research()
    executors.py      # MAF Executors (Outline, Research, Report, Output)
    __init__.py
```

## Environment
- .env file with AZURE_API_KEY and OPENAI_BASE_URL (gitignored)
- Load env via python-dotenv at startup

## Testing
- Run: `uv run deep-research 'test query' --max-rounds 1 -o /tmp/test.md`
- Verify imports: `uv run python -c "from deep_research.workflow import run_research; print('OK')"`
