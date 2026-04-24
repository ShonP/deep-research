"""OutputExecutor — compiles report and writes to file."""
from __future__ import annotations

import os

from agent_framework import Executor, handler

from deep_research.agents.report import create_report_agent
from deep_research.models.state import ResearchState


class ReportExecutor(Executor):
    """Compiles all findings into a structured markdown report."""

    def __init__(self) -> None:
        super().__init__(id="report")

    @handler(input=ResearchState, output=ResearchState)
    async def run(self, state, ctx) -> None:
        print("\n📝 Compiling research report...")
        findings_text = "\n\n".join(
            f"### {f.topic}\n{f.summary}" for f in state.findings
        )
        notes_text = "\n".join(f"- {n}" for n in state.notes) if state.notes else "(none)"

        prompt = (
            f"# Research Query\n{state.query}\n\n"
            f"# Research Findings\n{findings_text}\n\n"
            f"# Additional Notes\n{notes_text}\n\n"
            "Compile these findings into a comprehensive, well-structured markdown report. "
            "Include a Sources section at the end with all referenced URLs."
        )
        agent = create_report_agent()
        result = await agent.run(prompt)
        state.report = result.text or "(report generation failed)"
        print(f"   Report generated ({len(state.report)} characters)")
        await ctx.send_message(state)


class OutputExecutor(Executor):
    """Writes the final report to a file."""

    def __init__(self) -> None:
        super().__init__(id="output")

    @handler(input=ResearchState, workflow_output=ResearchState)
    async def run(self, state, ctx) -> None:
        path = state.output_path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(state.report)
        print(f"\n✅ Report written to {path}")
        await ctx.yield_output(state)
