"""Report agent: compiles research findings into a structured markdown report."""
from __future__ import annotations

from agent_framework import Agent
from agent_framework.github import GitHubCopilotAgent


SYSTEM_PROMPT = """\
You are a research report writer. You receive a collection of research findings
on a topic and must compile them into a well-structured markdown report.

Your report should include:
1. A title (# heading)
2. An executive summary
3. Organized sections covering each major topic area
4. Key findings and insights in each section
5. A "Sources" section at the end listing all cited URLs

Guidelines:
- Use markdown formatting (headings, bullet points, bold for emphasis)
- Cite sources inline where relevant, e.g. [Source Title](url)
- Synthesize and organize — don't just list findings sequentially
- Remove duplicate information across findings
- Aim for a comprehensive yet readable report
"""


def create_report_agent() -> Agent:
    """Create the report-compilation agent."""
    return GitHubCopilotAgent(
        name="ReportAgent",
        instructions=SYSTEM_PROMPT,
    )
