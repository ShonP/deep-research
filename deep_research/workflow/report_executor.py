"""Report executor: compresses findings and compiles the final report."""

from __future__ import annotations

from agent_framework._workflows._executor import Executor, handler
from agent_framework._workflows._workflow_context import WorkflowContext

from deep_research.agents.compressor import compress_findings
from deep_research.agents.report import generate_report
from deep_research.log import log


class ReportExecutor(Executor):
    """Compress findings, then compile into a markdown report."""

    @handler
    async def handle(self, state: dict, ctx: WorkflowContext[dict]) -> None:
        findings = state.get("findings", [])
        log.info("Compressing %d findings before report generation...", len(findings))

        compressed, extra_notes = await compress_findings(findings, state["query"])
        state["compressed_notes"] = extra_notes
        log.info(
            "Compressed: %d → %d findings, %d cross-cutting notes",
            len(findings),
            len(compressed),
            len(extra_notes),
        )

        findings_text = "\n\n".join(f"### {f['topic']}\n{f['summary']}" for f in compressed)
        notes = state.get("notes", []) + extra_notes
        notes_text = "\n".join(f"- {n}" for n in notes) if notes else "(none)"

        report = await generate_report(
            state["query"],
            findings_text,
            notes_text,
            state["source"],
        )
        state["report"] = report or "(report generation failed)"
        log.info("Report generated: %d chars", len(state["report"]))
        await ctx.send_message(state)
