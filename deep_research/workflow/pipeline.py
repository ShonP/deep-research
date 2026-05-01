"""Functional workflow pipeline for the research agent.

Uses @workflow/@step decorators with FileCheckpointStorage for resumable execution.
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime

from agent_framework import FileCheckpointStorage, step, workflow

from deep_research.log import attach_file_handler, detach_file_handler, log, new_run_id
from deep_research.utils import create_research_dir
from deep_research.workflow.pipeline_steps import do_outline, do_output, do_report, do_research_round


@step
async def step_outline(query: str, source: str, research_dir: str) -> dict:
    log.info("Step 1: Generating research outline...")
    return await do_outline(query, source, research_dir)


@step
async def step_research(state: dict, round_num: int, max_rounds: int) -> dict:
    log.info("Step 2: Research round %d/%d", round_num, max_rounds)
    return await do_research_round(state, round_num, max_rounds)


@step
async def step_report(state: dict) -> dict:
    log.info("Step 3: Generating report...")
    return await do_report(state)


@step
async def step_output(state: dict, output_path: str) -> str:
    log.info("Step 4: Saving output...")
    return do_output(state, output_path)


@workflow(name="deep_research")
async def research_workflow(input_data: dict) -> str:
    query = input_data["query"]
    source = input_data.get("source", "web")
    max_rounds = input_data.get("max_rounds", 3)
    output_path = input_data.get("output_path", "report.md")
    research_dir = input_data.get("research_dir", "")

    state = await step_outline(query, source, research_dir)

    round_num = 0
    while not state.get("research_complete", False):
        round_num += 1
        state = await step_research(state, round_num, max_rounds)

    state = await step_report(state)
    return await step_output(state, output_path)


async def run_research_async(
    query: str | None = None,
    *,
    max_rounds: int = 3,
    output_path: str = "report.md",
    research_base_dir: str = "reports",
    source: str = "web",
    resume: str | None = None,
    extra_providers: list[str] | None = None,
) -> None:
    """Run the full research pipeline asynchronously."""
    run_id = new_run_id()

    if resume:
        raise NotImplementedError("Resume not yet supported")

    if not query:
        raise ValueError("Query is required when not resuming")

    research_dir = create_research_dir(query, research_base_dir)
    attach_file_handler(research_dir)

    # Register extra providers if requested
    if extra_providers:
        from deep_research.tools.registry import register_extra_providers
        register_extra_providers(extra_providers)

    try:
        source_label = {"web": "🌐 Web", "github": "🐙 GitHub", "both": "🌐+🐙 Web & GitHub"}
        log.info("Starting deep research: %s", query)
        log.info(
            "Source: %s | Max rounds: %d | Run: %s",
            source_label.get(source, source),
            max_rounds,
            run_id,
        )
        log.info("Research artifacts: %s", research_dir)

        checkpoint_dir = os.path.join(research_dir, ".checkpoints")
        os.makedirs(checkpoint_dir, exist_ok=True)
        storage = FileCheckpointStorage(checkpoint_dir)

        result = await research_workflow.run(
            {
                "query": query,
                "max_rounds": max_rounds,
                "source": source,
                "output_path": output_path,
                "research_dir": research_dir,
                "started_at": datetime.now(UTC).isoformat(),
            },
            checkpoint_storage=storage,
        )

        if result.text:
            log.info("Research complete! Report: %d chars", len(result.text))
        else:
            log.warning("No outputs from workflow")
    except Exception:
        log.exception("Research pipeline failed")
        raise
    finally:
        detach_file_handler()


def run_research(
    query: str | None = None,
    *,
    max_rounds: int = 3,
    output_path: str = "report.md",
    research_base_dir: str = "reports",
    source: str = "web",
    resume: str | None = None,
    extra_providers: list[str] | None = None,
) -> None:
    """Synchronous wrapper for the async research pipeline."""
    asyncio.run(
        run_research_async(
            query,
            max_rounds=max_rounds,
            output_path=output_path,
            research_base_dir=research_base_dir,
            source=source,
            resume=resume,
            extra_providers=extra_providers,
        )
    )
