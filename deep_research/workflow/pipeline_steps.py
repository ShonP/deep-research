"""Helper functions for pipeline steps — extracted from executor logic."""

from __future__ import annotations

import os
from datetime import UTC, datetime

from deep_research.agents.compressor import compress_findings
from deep_research.agents.critic import evaluate_research
from deep_research.agents.outline import generate_outline
from deep_research.agents.query_refiner import refine_queries
from deep_research.agents.report import generate_report
from deep_research.agents.supervisor import dispatch_research
from deep_research.log import log
from deep_research.middleware import get_token_usage, reset_token_usage
from deep_research.utils import save_json, save_text

MAX_QUERIES_PER_ROUND = 5
COST_PER_1K_INPUT = 0.005
COST_PER_1K_OUTPUT = 0.015


async def do_outline(query: str, source: str, research_dir: str) -> dict:
    """Generate outline and return initial state dict."""
    reset_token_usage()
    research_topics = await generate_outline(query, source)
    topics = [t.model_dump() for t in research_topics]
    log.info("Outline created: %d topics", len(topics))
    if research_dir:
        save_json(os.path.join(research_dir, "outline.json"), {"topics": topics})
    return {
        "query": query,
        "source": source,
        "research_dir": research_dir,
        "topics": topics,
        "findings": [],
        "sources": [],
        "gaps": [],
        "notes": [],
        "raw_notes": [],
        "compressed_notes": [],
        "research_complete": False,
        "report": "",
    }


async def do_research_round(state: dict, round_num: int, max_rounds: int) -> dict:
    """Execute one research round. Returns a new state dict."""
    state = {**state, "findings": list(state["findings"]), "sources": list(state["sources"]),
             "raw_notes": list(state["raw_notes"])}
    query, source = state["query"], state["source"]
    log.info("Research round %d/%d", round_num, max_rounds)

    raw_queries = _get_queries(state, round_num)
    if not raw_queries:
        return {**state, "research_complete": True}

    refined = await _refine_all(raw_queries, query)
    log.info("Refined %d raw queries → %d search queries", len(raw_queries), len(refined))

    results = await dispatch_research(refined, query, source, round_num)
    _merge_results(state, results)
    _save_incremental(state)

    if round_num >= max_rounds:
        log.info("Max rounds reached.")
        return {**state, "research_complete": True}

    feedback = await evaluate_research(query, state["findings"], source)
    gaps = [] if feedback.complete else feedback.gaps
    log.info(
        "Critic: score=%.1f, %s",
        feedback.quality_score,
        "complete" if feedback.complete else f"{len(gaps)} gaps",
    )
    return {**state, "research_complete": feedback.complete, "gaps": gaps}


async def do_report(state: dict) -> dict:
    """Compress findings and generate final report. Returns new state dict."""
    findings = state.get("findings", [])
    log.info("Compressing %d findings before report generation...", len(findings))

    compressed, extra_notes = await compress_findings(findings, state["query"])
    log.info("Compressed: %d → %d findings, %d cross-cutting notes", len(findings), len(compressed), len(extra_notes))

    findings_text = "\n\n".join(f"### {f['topic']}\n{f['summary']}" for f in compressed)
    notes = state.get("notes", []) + extra_notes
    notes_text = "\n".join(f"- {n}" for n in notes) if notes else "(none)"

    report = await generate_report(state["query"], findings_text, notes_text, state["source"])
    return {**state, "report": report or "(report generation failed)", "compressed_notes": extra_notes}


def do_output(state: dict, output_path: str) -> str:
    """Save report and artifacts to disk. Returns the report text."""
    report = state.get("report", "")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    save_text(output_path, report)
    log.info("Report written to %s", output_path)

    research_dir = state.get("research_dir", "")
    if research_dir:
        save_text(os.path.join(research_dir, "report.md"), report)
        usage = get_token_usage()
        meta = {
            "query": state["query"],
            "started_at": state.get("started_at", ""),
            "finished_at": datetime.now(UTC).isoformat(),
            "source": state["source"],
            "topics_count": len(state.get("topics", [])),
            "findings_count": len(state.get("findings", [])),
            "sources_count": len(state.get("sources", [])),
            "token_usage": usage.to_dict(),
        }
        save_json(os.path.join(research_dir, "meta.json"), meta)
        log.info("All artifacts saved to: %s", research_dir)

    _log_token_summary()
    return report


def _get_queries(state: dict, round_num: int) -> list[str]:
    if round_num == 1:
        queries: list[str] = []
        for t in state.get("topics", []):
            queries.append(f"{t['title']}: {t.get('description', '')}")
            for sub in t.get("subtopics", []):
                queries.append(f"{t['title']} — {sub}")
        return queries
    return [f"Fill knowledge gap: {g}" for g in state.get("gaps", [])]


async def _refine_all(raw_queries: list[str], context: str) -> list[str]:
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
    for r in results:
        state["findings"].append({"topic": r["topic"], "summary": r["summary"], "round": r["round"]})
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


def _log_token_summary() -> None:
    usage = get_token_usage()
    if usage.total_tokens == 0:
        return
    est_cost = (usage.prompt_tokens / 1000) * COST_PER_1K_INPUT + (usage.completion_tokens / 1000) * COST_PER_1K_OUTPUT
    log.info(
        "Token usage — prompt: %d, completion: %d, total: %d, est. cost: $%.4f",
        usage.prompt_tokens, usage.completion_tokens, usage.total_tokens, est_cost,
    )
