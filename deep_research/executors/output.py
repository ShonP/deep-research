"""OutputExecutor — compiles report and writes to file."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from agent_framework import Executor, handler

from deep_research.agents.report import create_report_agent
from deep_research.models.state import ResearchState
from deep_research.utils import save_json, save_text


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
        agent = create_report_agent(source=state.source)
        result = await agent.run(prompt, options={'timeout': 300})
        state.report = result.text or "(report generation failed)"
        print(f"   Report generated ({len(state.report)} characters)")
        await ctx.send_message(state)


class OutputExecutor(Executor):
    """Writes the final report and metadata to files."""

    def __init__(self) -> None:
        super().__init__(id="output")

    @handler(input=ResearchState, workflow_output=ResearchState)
    async def run(self, state, ctx) -> None:
        # Write to the -o output path
        path = state.output_path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        save_text(path, state.report)
        print(f"\n✅ Report written to {path}")

        # Save artifacts to the research directory
        if state.research_dir:
            report_path = os.path.join(state.research_dir, "report.md")
            save_text(report_path, state.report)

            finished_at = datetime.now(timezone.utc).isoformat()
            meta = {
                "query": state.query,
                "started_at": state.started_at,
                "finished_at": finished_at,
                "max_rounds": state.max_rounds,
                "topics_count": len(state.outline),
                "findings_count": len(state.findings),
            }
            save_json(os.path.join(state.research_dir, "meta.json"), meta)

            print(f"   All artifacts saved to: {state.research_dir}")

        await ctx.yield_output(state)
