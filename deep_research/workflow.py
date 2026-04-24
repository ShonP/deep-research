"""MAF Workflow for the deep-research pipeline."""
from __future__ import annotations

import asyncio

from agent_framework import WorkflowBuilder

from deep_research.executors.start import StartExecutor
from deep_research.executors.judge import ResearchLoopExecutor
from deep_research.executors.output import OutputExecutor, ReportExecutor


def build_research_workflow(
    query: str,
    max_rounds: int = 3,
    output_path: str = "report.md",
    research_base_dir: str = "reports",
):
    """Build and return a MAF Workflow for deep research."""
    start = StartExecutor(
        query=query,
        max_rounds=max_rounds,
        output_path=output_path,
        research_base_dir=research_base_dir,
    )
    research_loop = ResearchLoopExecutor()
    report = ReportExecutor()
    output = OutputExecutor()

    builder = WorkflowBuilder(start_executor=start, output_executors=[output])
    builder.add_edge(start, research_loop)
    builder.add_edge(research_loop, report)
    builder.add_edge(report, output)
    return builder.build()


def run_research(
    query: str,
    *,
    max_rounds: int = 3,
    output_path: str = "report.md",
    research_base_dir: str = "reports",
) -> None:
    """Synchronous entrypoint: build workflow and run to completion."""
    workflow = build_research_workflow(query, max_rounds, output_path, research_base_dir)

    async def _drive() -> None:
        # Start message is just a trigger string
        async for event in workflow.run("start", stream=True):
            pass

    asyncio.run(_drive())
