# Structured Outputs + Search Provider Abstraction

Three related refactors to improve type safety, scalability, and extensibility.

## Problem

1. **Manual JSON parsing in agents** — outline, compressor, critic, and query_refiner all
   instruct the LLM to "respond with ONLY valid JSON" then manually strip markdown fences
   and parse with `json.loads()`. MAF supports native structured outputs that guarantee
   valid typed responses.

2. **Supervisor if/elif doesn't scale** — `_research_one` in `supervisor.py` hard-codes
   `if source == "web" / elif source == "github" / else both`. Adding a new source means
   editing the conditional chain.

3. **No search provider abstraction** — web search (Tavily/DDG/SearXNG) and GitHub search
   are separate tool files with no shared contract. Adding a new research source requires
   touching multiple files.

## Approach

### 1. MAF Structured Outputs

Use `agent.run(prompt, options={"response_format": PydanticModel})` for all agents that
return structured data. The model provides `response.value` as a typed Pydantic instance.

#### New Pydantic models (`models/state.py`)

```python
class OutlineResponse(BaseModel):
    """Structured outline output from the outline agent."""
    topics: list[ResearchTopic]

class CompressedFinding(BaseModel):
    """A single compressed finding."""
    topic: str
    summary: str
    key_sources: list[str] = Field(default_factory=list)

class CompressedFindings(BaseModel):
    """Structured output from the compressor agent."""
    compressed: list[CompressedFinding]
    notes: list[str] = Field(default_factory=list)

class RefinedQueries(BaseModel):
    """Structured output from the query refiner agent."""
    queries: list[str]
```

`CriticFeedback` already exists and is used as-is.

#### Affected files

- **`agents/outline.py`** — Remove JSON-in-prompt instructions. Use
  `agent.run(prompt, options={"response_format": OutlineResponse})`.
  Return `response.value.topics` directly. Remove raw JSON return.

- **`agents/compressor.py`** — Remove JSON-in-prompt instructions, `_parse_compressed`.
  Use `response_format=CompressedFindings`. Return `(response.value.compressed, response.value.notes)`.

- **`agents/critic.py`** — Remove JSON-in-prompt instructions, `_parse_feedback`.
  Use `response_format=CriticFeedback`. Return `response.value` directly.

- **`agents/query_refiner.py`** — Remove JSON-in-prompt instructions, `_parse_queries`.
  Use `response_format=RefinedQueries`. Return `response.value.queries`.

#### Prompt changes

System prompts shrink: remove all "Respond with ONLY valid JSON" blocks and format
specifications. Keep the behavioral instructions (rules, priorities, etc.).

### 2. Search Provider Protocol

New file: **`tools/provider.py`**

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable

@runtime_checkable
class SearchProvider(Protocol):
    @property
    def name(self) -> str:
        """Unique identifier for this provider (e.g. 'web', 'github')."""
        ...

    @property
    def tools(self) -> list:
        """MAF @tool-decorated functions this provider offers."""
        ...

    @property
    def instructions(self) -> str:
        """Provider-specific instructions appended to the researcher system prompt."""
        ...
```

#### Concrete implementations

**`WebSearchProvider`** (in `tools/provider.py` or its own file):
- `name = "web"`
- `tools = [web_search, fetch_page]`
- `instructions` = the current web-researcher system prompt additions

**`GitHubSearchProvider`** (in `tools/provider.py` or its own file):
- `name = "github"`
- `tools = [github_search, github_read]`
- `instructions` = the current github-researcher system prompt additions

### 3. Provider Registry + Scalable Supervisor

New file: **`tools/registry.py`**

```python
from __future__ import annotations

from deep_research.tools.provider import SearchProvider

_PROVIDERS: dict[str, SearchProvider] = {}

def register(provider: SearchProvider) -> None:
    _PROVIDERS[provider.name] = provider

def get_providers(source: str) -> list[SearchProvider]:
    if source in _PROVIDERS:
        return [_PROVIDERS[source]]
    # "both" or "all" → return all registered providers
    return list(_PROVIDERS.values())
```

Providers self-register at module load in `tools/__init__.py`:

```python
from deep_research.tools.registry import register
from deep_research.tools.provider import WebSearchProvider, GitHubSearchProvider

register(WebSearchProvider())
register(GitHubSearchProvider())
```

#### Supervisor changes (`agents/supervisor.py`)

`_research_one` becomes:

```python
async def _research_one(topic, query, source, round_num):
    providers = get_providers(source)
    tasks = [_run_provider(topic, query, p) for p in providers]
    results = await asyncio.gather(*tasks)
    summary = "\n\n".join(f"[{p.name}] {r}" for p, r in zip(providers, results))
    ...
```

No if/elif. Adding a new source = implement `SearchProvider` + `register()`.

#### Research agents consolidated

The current `agents/research.py` and `agents/github_research.py` are replaced by a
single `_run_provider` function in the supervisor that:
1. Reads the provider's `tools` and `instructions`
2. Creates an `Agent` with a base researcher prompt + provider instructions
3. Runs the agent and returns the text summary

Old files `agents/research.py` and `agents/github_research.py` are deleted.

## File changes summary

| File | Action |
|------|--------|
| `models/state.py` | Add `OutlineResponse`, `CompressedFinding`, `CompressedFindings`, `RefinedQueries` |
| `agents/outline.py` | Use structured output, simplify prompt |
| `agents/compressor.py` | Use structured output, remove `_parse_compressed` |
| `agents/critic.py` | Use structured output, remove `_parse_feedback` |
| `agents/query_refiner.py` | Use structured output, remove `_parse_queries` |
| `tools/provider.py` | New — `SearchProvider` protocol + concrete implementations |
| `tools/registry.py` | New — provider registry |
| `tools/__init__.py` | Register default providers |
| `agents/supervisor.py` | Use registry, single `_run_provider`, remove if/elif |
| `agents/research.py` | Delete (absorbed into supervisor) |
| `agents/github_research.py` | Delete (absorbed into supervisor) |
| `workflow/research_executor.py` | Update imports (no functional change) |

## Out of scope

- Changing the web search tool internals (Tavily/DDG/SearXNG fallback chain stays)
- Changing the workflow graph structure
- Adding new search providers (just enabling them)
