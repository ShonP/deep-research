"""Start executor: generates the research outline."""

from __future__ import annotations

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
        research_topics = await generate_outline(query, source)
        topics = [t.model_dump() for t in research_topics]
        log.info("Outline created: %d topics", len(topics))
        rd = config.get("research_dir", "")
        if rd:
            save_json(os.path.join(rd, "outline.json"), {"topics": topics})
        await ctx.send_message(
            {
                "query": query,
                "max_rounds": config.get("max_rounds", 3),
                "current_round": 0,
                "source": source,
                "output_path": config.get("output_path", "report.md"),
                "research_dir": rd,
                "started_at": config.get("started_at", ""),
                "topics": topics,
                "findings": [],
                "sources": [],
                "gaps": [],
                "notes": [],
                "raw_notes": [],
                "compressed_notes": [],
                "research_complete": False,
                "report": "",
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            }
        )
