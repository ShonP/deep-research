"""Supervisor agent: dispatches parallel research tasks with isolated contexts."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from deep_research.agents.github_research import github_research_topic
from deep_research.agents.research import research_topic
from deep_research.log import log
from deep_research.utils import extract_urls

MAX_CONCURRENCY = 3


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
    topic: str, query: str, source: str, round_num: int,
) -> dict:
    """Execute research for one topic. Each call creates fresh agent instances."""
    try:
        if source == "web":
            summary = await research_topic(topic, query)
        elif source == "github":
            summary = await github_research_topic(topic, query)
        else:
            web, gh = await asyncio.gather(
                research_topic(topic, query),
                github_research_topic(topic, query),
            )
            summary = f"[web] {web}\n\n[github] {gh}"

        now = datetime.now(timezone.utc).isoformat()
        urls = extract_urls(summary)
        sources = [{"url": u, "query": topic, "fetched_at": now} for u in urls]
        return {
            "topic": topic, "summary": summary, "round": round_num,
            "sources": sources, "error": None,
        }
    except Exception as e:
        log.error("Research failed for '%s': %s", topic[:60], e)
        return {
            "topic": topic, "summary": f"(failed: {e})", "round": round_num,
            "sources": [], "error": str(e),
        }
