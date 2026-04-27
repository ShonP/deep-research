"""Start executor: generates the research outline."""
from __future__ import annotations

import json
import os

from agent_framework._workflows._executor import Executor, handler
from agent_framework._workflows._workflow_context import WorkflowContext

from deep_research.agents.outline import generate_outline
from deep_research.log import log
from deep_research.middleware import reset_token_usage
from deep_research.utils import save_json


class StartExecutor(Executor):
    @handler
    async def handle(self, message: dict, ctx: WorkflowContext[dict]) -> None:
        reset_token_usage()
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
            "gaps": [], "notes": [], "raw_notes": [], "compressed_notes": [],
            "research_complete": False, "report": "",
            "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0,
        })


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
