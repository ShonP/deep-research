"""Output executor: saves report and artifacts to disk."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Never

from agent_framework._workflows._executor import Executor, handler
from agent_framework._workflows._workflow_context import WorkflowContext

from deep_research.log import log
from deep_research.middleware import get_token_usage
from deep_research.utils import save_json, save_text

COST_PER_1K_INPUT = 0.005
COST_PER_1K_OUTPUT = 0.015


class OutputExecutor(Executor):
    """Save report and artifacts to disk, log token usage."""

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
            usage = get_token_usage()
            meta = {
                "query": state["query"],
                "started_at": state.get("started_at", ""),
                "finished_at": datetime.now(UTC).isoformat(),
                "max_rounds": state["max_rounds"],
                "source": state["source"],
                "topics_count": len(state.get("topics", [])),
                "findings_count": len(state.get("findings", [])),
                "sources_count": len(state.get("sources", [])),
                "token_usage": usage.to_dict(),
            }
            save_json(os.path.join(research_dir, "meta.json"), meta)
            log.info("All artifacts saved to: %s", research_dir)

        _log_token_summary()
        await ctx.yield_output(report)


def _log_token_summary() -> None:
    usage = get_token_usage()
    if usage.total_tokens == 0:
        return
    est_cost = (usage.prompt_tokens / 1000) * COST_PER_1K_INPUT + (usage.completion_tokens / 1000) * COST_PER_1K_OUTPUT
    log.info(
        "Token usage — prompt: %d, completion: %d, total: %d, est. cost: $%.4f",
        usage.prompt_tokens,
        usage.completion_tokens,
        usage.total_tokens,
        est_cost,
    )
