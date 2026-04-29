"""Supervisor agent: dispatches parallel research tasks with isolated contexts."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from agent_framework import Agent

from deep_research.client import get_chat_client
from deep_research.log import log
from deep_research.middleware import (
    caching,
    llm_call_logging,
    retry,
    tool_call_logging,
)
from deep_research.tools.provider import SearchProvider
from deep_research.tools.registry import get_providers
from deep_research.utils import extract_urls

import deep_research.tools as _  # noqa: F401 — trigger provider registration

MAX_CONCURRENCY = 3

BASE_RESEARCHER_PROMPT = """\
You are a thorough researcher. You are given a research topic to investigate.

Your final message MUST be a research summary that includes:
- Key findings and insights
- Specific facts, techniques, or data discovered
- Source URLs for citations (include the actual URLs you visited)

Be thorough but concise. Focus on factual, actionable information.
Write your summary as plain text (not JSON).
"""


async def dispatch_research(
    queries: list[str],
    base_query: str,
    source: str,
    round_num: int,
) -> list[dict]:
    """Dispatch research tasks in parallel with isolated agent contexts.

    Each researcher gets a fresh agent instance (no context pollution).
    Concurrency is limited to MAX_CONCURRENCY to avoid rate limits.
    Returns a list of finding dicts ready for merging into state.
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    tasks = [
        _research_with_limit(semaphore, topic, base_query, source, round_num, i, len(queries))
        for i, topic in enumerate(queries, 1)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    findings: list[dict] = []
    for result in results:
        if isinstance(result, Exception):
            log.error("Research task failed: %s", result)
            continue
        if isinstance(result, dict):
            findings.append(result)

    return findings


async def _research_with_limit(
    semaphore: asyncio.Semaphore,
    topic: str,
    base_query: str,
    source: str,
    round_num: int,
    index: int,
    total: int,
) -> dict:
    """Run a single research task with semaphore-limited concurrency."""
    async with semaphore:
        log.info("[%d/%d] Researching: %s", index, total, topic[:80])
        return await _research_one(topic, base_query, source, round_num)


async def _research_one(
    topic: str,
    query: str,
    source: str,
    round_num: int,
) -> dict:
    """Execute research for one topic using registered providers."""
    try:
        providers = get_providers(source)
        tasks = [_run_provider(topic, query, p) for p in providers]
        results = await asyncio.gather(*tasks)

        if len(results) == 1:
            summary = results[0]
        else:
            summary = "\n\n".join(
                f"[{p.name}] {r}" for p, r in zip(providers, results)
            )

        now = datetime.now(UTC).isoformat()
        urls = extract_urls(summary)
        sources = [{"url": u, "query": topic, "fetched_at": now} for u in urls]
        return {
            "topic": topic,
            "summary": summary,
            "round": round_num,
            "sources": sources,
            "error": None,
        }
    except Exception as e:
        log.error("Research failed for '%s': %s", topic[:60], e)
        return {
            "topic": topic,
            "summary": f"(failed: {e})",
            "round": round_num,
            "sources": [],
            "error": str(e),
        }


async def _run_provider(topic: str, query: str, provider: SearchProvider) -> str:
    """Run a single provider's research agent with its tools and instructions."""
    instructions = f"{BASE_RESEARCHER_PROMPT}\n\n{provider.instructions}"
    agent = Agent(
        client=get_chat_client(),
        name=f"{provider.name}-researcher",
        instructions=instructions,
        tools=provider.tools,
        middleware=[tool_call_logging, caching, retry, llm_call_logging],
    )
    prompt = (
        f"Research the following topic thoroughly:\n\n{topic}\n\n"
        f"Context — this is part of a larger research project on: {query}"
    )
    response = await agent.run(prompt)
    return response.text
