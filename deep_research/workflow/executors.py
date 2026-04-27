"""MAF Executors for the research pipeline."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from typing_extensions import Never

from agent_framework._agents import Agent
from agent_framework._workflows._executor import Executor, handler
from agent_framework._workflows._workflow_context import WorkflowContext

from deep_research.agents.github_research import github_research_topic
from deep_research.agents.outline import generate_outline
from deep_research.agents.report import generate_report
from deep_research.agents.research import research_topic
from deep_research.client import get_chat_client
from deep_research.log import log
from deep_research.utils import extract_urls, save_json, save_text


class StartExecutor(Executor):
    @handler
    async def handle(self, message: dict, ctx: WorkflowContext[dict]) -> None:
        query, config = message["query"], message.get("config", {})
        source = config.get("source", "web")
        log.info("Generating research outline...")
        topics = _parse_outline(await generate_outline(query, source))
        log.info("Outline created: %d topics", len(topics))
        rd = config.get("research_dir", "")
        if rd:
            save_json(os.path.join(rd, "outline.json"), {"topics": topics})
        await ctx.send_message({
            "query": query, "max_rounds": config.get("max_rounds", 3),
            "current_round": 0, "source": source,
            "output_path": config.get("output_path", "report.md"),
            "research_dir": rd, "started_at": config.get("started_at", ""),
            "topics": topics, "findings": [], "sources": [],
            "gaps": [], "notes": [], "research_complete": False, "report": "",
        })


class ResearchLoopExecutor(Executor):
    @handler
    async def handle(self, state: dict, ctx: WorkflowContext[dict]) -> None:
        state["current_round"] = state.get("current_round", 0) + 1
        round_num, query, source = state["current_round"], state["query"], state["source"]
        log.info("Research round %d/%d", round_num, state["max_rounds"])
        queries = _get_queries(state)
        if not queries:
            state["research_complete"] = True
            await ctx.send_message(state)
            return
        for i, topic in enumerate(queries, 1):
            log.info("[%d/%d] Researching: %s", i, len(queries), topic[:80])
            await _research_one(state, topic, query, source, round_num)
        _save_incremental(state)
        if round_num >= state["max_rounds"]:
            log.info("Max rounds reached.")
            state["research_complete"] = True
        else:
            complete, gaps = await _judge(query, state["findings"], source)
            state["research_complete"], state["gaps"] = complete, [] if complete else gaps
            log.info("Research %s.", "comprehensive" if complete else f"has {len(gaps)} gaps")
        await ctx.send_message(state)


class ReportExecutor(Executor):
    """Compile findings into a markdown report."""

    @handler
    async def handle(self, state: dict, ctx: WorkflowContext[dict]) -> None:
        findings = state.get("findings", [])
        log.info("Compiling report from %d findings...", len(findings))
        findings_text = "\n\n".join(
            f"### {f['topic']}\n{f['summary']}" for f in findings
        )
        notes = state.get("notes", [])
        notes_text = "\n".join(f"- {n}" for n in notes) if notes else "(none)"
        report = await generate_report(
            state["query"], findings_text, notes_text, state["source"],
        )
        state["report"] = report or "(report generation failed)"
        log.info("Report generated: %d chars", len(state["report"]))
        await ctx.send_message(state)


class OutputExecutor(Executor):
    """Save report and artifacts to disk."""

    @handler
    async def handle(self, state: dict, ctx: WorkflowContext[Never, str]) -> None:
        report = state.get("report", "")
        output_path = state.get("output_path", "report.md")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        save_text(output_path, report)
        log.info("Report written to %s", output_path)

        research_dir = state.get("research_dir", "")
        if research_dir:
            save_text(os.path.join(research_dir, "report.md"), report)
            meta = {
                "query": state["query"],
                "started_at": state.get("started_at", ""),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "max_rounds": state["max_rounds"],
                "source": state["source"],
                "topics_count": len(state.get("topics", [])),
                "findings_count": len(state.get("findings", [])),
                "sources_count": len(state.get("sources", [])),
            }
            save_json(os.path.join(research_dir, "meta.json"), meta)
            log.info("All artifacts saved to: %s", research_dir)

        await ctx.yield_output(report)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_outline(text: str) -> list[dict]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    try:
        return json.loads(text.strip()).get("topics", [])
    except (json.JSONDecodeError, KeyError):
        log.warning("Outline parsing failed, using fallback")
        return [{"title": "General research", "description": "Research the query", "subtopics": []}]


def _get_queries(state: dict) -> list[str]:
    if state["current_round"] == 1:
        queries: list[str] = []
        for t in state.get("topics", []):
            queries.append(f"{t['title']}: {t.get('description', '')}")
            for sub in t.get("subtopics", []):
                queries.append(f"{t['title']} — {sub}")
        return queries
    return [f"Fill knowledge gap: {g}" for g in state.get("gaps", [])]


async def _research_one(
    state: dict, topic: str, query: str, source: str, round_num: int,
) -> None:
    try:
        if source == "web":
            summary = await research_topic(topic, query)
        elif source == "github":
            summary = await github_research_topic(topic, query)
        else:
            web = await research_topic(topic, query)
            gh = await github_research_topic(topic, query)
            summary = f"[web] {web}\n\n[github] {gh}"
        state["findings"].append({"topic": topic, "summary": summary, "round": round_num})
        now = datetime.now(timezone.utc).isoformat()
        for url in extract_urls(summary):
            state["sources"].append({"url": url, "query": topic, "fetched_at": now})
    except Exception as e:
        log.error("Research failed for '%s': %s", topic[:60], e)
        state["findings"].append({"topic": topic, "summary": f"(failed: {e})", "round": round_num})


async def _judge(query: str, findings: list[dict], source: str) -> tuple[bool, list[str]]:
    findings_text = "\n\n".join(f"### {f['topic']}\n{f['summary']}" for f in findings)
    prompt = (
        f"Original research query: {query}\n\n"
        f"Research findings so far:\n{findings_text}\n\n"
        "Evaluate these findings. Are there significant knowledge gaps?\n"
        "Respond with ONLY valid JSON (no markdown fences):\n"
        '{"complete": true/false, "gaps": ["gap 1", ...]}\n'
    )
    agent = Agent(
        client=get_chat_client(), name="judge",
        instructions="You evaluate research completeness. Respond only with JSON.",
    )
    response = await agent.run(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    try:
        data = json.loads(text.strip())
        return data.get("complete", True), data.get("gaps", [])
    except (json.JSONDecodeError, KeyError):
        log.warning("Judge parsing failed, assuming complete")
        return True, []


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
