"""Report agent: compiles research findings into a structured markdown report."""
from __future__ import annotations

from agent_framework._agents import Agent

from deep_research.client import get_chat_client
from deep_research.middleware import llm_call_logging

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
- Cite sources inline where relevant
- Synthesize and organize — don't just list findings sequentially
- Remove duplicate information across findings
"""

GITHUB_REPORT_PROMPT = """\
You are a technical report writer specializing in open-source software analysis.

Your report should include:
1. A title (# heading)
2. An executive summary
3. Repository Overview — How 3-5 key repos solve the problem
4. Code Patterns & Architecture — with code snippets
5. Comparison — Pros/cons of different approaches
6. Community Insights — from GitHub issues
7. Sources section with links to repos, files, and issues

Include direct links, actual code snippets, and compare approaches.
"""


async def generate_report(
    query: str, findings_text: str, notes_text: str, source: str = "web"
) -> str:
    system = GITHUB_REPORT_PROMPT if source in ("github", "both") else SYSTEM_PROMPT
    agent = Agent(
        client=get_chat_client(),
        name="report-writer",
        instructions=system,
        middleware=[llm_call_logging],
    )
    prompt = (
        f"# Research Query\n{query}\n\n"
        f"# Research Findings\n{findings_text}\n\n"
        f"# Additional Notes\n{notes_text}\n\n"
        "Compile into a comprehensive markdown report with Sources section."
    )
    response = await agent.run(prompt)
    return response.text
