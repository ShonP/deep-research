"""Workflow builder and entry point for the research pipeline."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime

from agent_framework._workflows._checkpoint import FileCheckpointStorage
from agent_framework._workflows._edge import Case, Default
from agent_framework._workflows._workflow_builder import WorkflowBuilder

from deep_research.log import attach_file_handler, detach_file_handler, log, new_run_id
from deep_research.utils import create_research_dir, load_env
from deep_research.workflow.output_executor import OutputExecutor
from deep_research.workflow.report_executor import ReportExecutor
from deep_research.workflow.research_executor import ResearchLoopExecutor
from deep_research.workflow.start_executor import StartExecutor


def build_workflow(checkpoint_dir: str | None = None):
    """Build the research workflow graph."""
    start = StartExecutor(id="start")
    research = ResearchLoopExecutor(id="research")
    report = ReportExecutor(id="report")
    output = OutputExecutor(id="output")

    storage = FileCheckpointStorage(checkpoint_dir) if checkpoint_dir else None

    workflow = (
        WorkflowBuilder(
            start_executor=start,
            name="deep-research",
            checkpoint_storage=storage,
            max_iterations=50,
        )
        .add_edge(start, research)
        .add_switch_case_edge_group(
            research,
            [
                Case(
                    condition=lambda state: state.get("research_complete", False),
                    target=report,
                ),
                Default(target=research),
            ],
        )
        .add_edge(report, output)
        .build()
    )
    return workflow


async def run_research_async(
    query: str | None = None,
    *,
    max_rounds: int = 3,
    output_path: str = "report.md",
    research_base_dir: str = "reports",
    source: str = "web",
    resume: str | None = None,
) -> None:
    """Run the full research pipeline asynchronously."""
    load_env()
    run_id = new_run_id()

    if resume:
        raise NotImplementedError("Resume not yet supported in MAF workflow mode")

    if not query:
        raise ValueError("Query is required when not resuming")

    research_dir = create_research_dir(query, research_base_dir)
    attach_file_handler(research_dir)

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
        workflow = build_workflow(checkpoint_dir)

        result = await workflow.run(
            {
                "query": query,
                "config": {
                    "max_rounds": max_rounds,
                    "source": source,
                    "output_path": output_path,
                    "research_dir": research_dir,
                    "started_at": datetime.now(UTC).isoformat(),
                },
            }
        )

        outputs = result.get_outputs()
        if outputs:
            log.info("Research complete! Report: %d chars", len(outputs[0]))
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
        )
    )
