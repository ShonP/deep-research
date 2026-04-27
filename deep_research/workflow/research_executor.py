"""Research loop executor: orchestrates multi-round research with parallel execution."""
from __future__ import annotations

import os

from agent_framework._workflows._executor import Executor, handler
from agent_framework._workflows._workflow_context import WorkflowContext

from deep_research.agents.critic import evaluate_research
from deep_research.agents.query_refiner import refine_queries
from deep_research.agents.supervisor import dispatch_research
from deep_research.log import log
from deep_research.middleware import get_token_usage
from deep_research.utils import save_json

MAX_QUERIES_PER_ROUND = 5


class ResearchLoopExecutor(Executor):
    @handler
    async def handle(self, state: dict, ctx: WorkflowContext[dict]) -> None:
        state["current_round"] = state.get("current_round", 0) + 1
        round_num = state["current_round"]
        query, source = state["query"], state["source"]
        log.info("Research round %d/%d", round_num, state["max_rounds"])

        raw_queries = _get_queries(state)
        if not raw_queries:
            state["research_complete"] = True
            await ctx.send_message(state)
            return

        refined = await _refine_all(raw_queries, query)
        log.info("Refined %d raw queries → %d search queries", len(raw_queries), len(refined))

        results = await dispatch_research(refined, query, source, round_num)
        _merge_results(state, results)
        _save_incremental(state)

        if round_num >= state["max_rounds"]:
            log.info("Max rounds reached.")
            state["research_complete"] = True
        else:
            feedback = await evaluate_research(query, state["findings"], source)
            state["research_complete"] = feedback.complete
            state["gaps"] = [] if feedback.complete else feedback.gaps
            log.info(
                "Critic: score=%.1f, %s",
                feedback.quality_score,
                "complete" if feedback.complete else f"{len(feedback.gaps)} gaps",
            )

        usage = get_token_usage()
        state["total_tokens"] = usage.total_tokens
        state["prompt_tokens"] = usage.prompt_tokens
        state["completion_tokens"] = usage.completion_tokens
        await ctx.send_message(state)


def _get_queries(state: dict) -> list[str]:
    if state["current_round"] == 1:
        queries: list[str] = []
        for t in state.get("topics", []):
            queries.append(f"{t['title']}: {t.get('description', '')}")
            for sub in t.get("subtopics", []):
                queries.append(f"{t['title']} — {sub}")
        return queries
    return [f"Fill knowledge gap: {g}" for g in state.get("gaps", [])]


async def _refine_all(raw_queries: list[str], context: str) -> list[str]:
    """Refine queries but cap total to MAX_QUERIES_PER_ROUND."""
    refined: list[str] = []
    seen: set[str] = set()
    for q in raw_queries:
        if len(refined) >= MAX_QUERIES_PER_ROUND:
            break
        sub_queries = await refine_queries(q, context, max_queries=2)
        for sq in sub_queries:
            sq_lower = sq.lower().strip()
            if sq_lower not in seen and len(refined) < MAX_QUERIES_PER_ROUND:
                seen.add(sq_lower)
                refined.append(sq)
    return refined if refined else raw_queries[:MAX_QUERIES_PER_ROUND]


def _merge_results(state: dict, results: list[dict]) -> None:
    """Merge parallel research results into state."""
    for r in results:
        state["findings"].append({
            "topic": r["topic"], "summary": r["summary"], "round": r["round"],
        })
        state["raw_notes"].append(f"[round {r['round']}] {r['topic']}: {r['summary'][:200]}")
        for src in r.get("sources", []):
            state["sources"].append(src)


def _save_incremental(state: dict) -> None:
    research_dir = state.get("research_dir", "")
    if not research_dir:
        return
    rounds: dict[int, list[dict]] = {}
    for f in state.get("findings", []):
        rounds.setdefault(f.get("round", 0), []).append(f)
    save_json(
        os.path.join(research_dir, "findings.json"),
        {"rounds": [{"round": r, "topics": t} for r, t in sorted(rounds.items())]},
    )
    seen: set[str] = set()
    unique = []
    for s in state.get("sources", []):
        if s["url"] not in seen:
            seen.add(s["url"])
            unique.append(s)
    save_json(os.path.join(research_dir, "sources.json"), unique)
