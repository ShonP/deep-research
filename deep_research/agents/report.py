"""Report agent: compiles research findings into a structured markdown report."""
from __future__ import annotations

from deep_research.llm import chat


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


GITHUB_REPORT_PROMPT = """\
You are a technical report writer specializing in open-source software analysis.
You receive research findings from GitHub repository analysis and must compile
them into a structured markdown report.

Your report should include:
1. A title (# heading)
2. An executive summary of the landscape
3. **Repository Overview** — How 3-5 key repos solve this problem, with stars,
   language, and links
4. **Code Patterns & Architecture** — Specific implementation patterns found,
   with code snippets (use fenced code blocks)
5. **Comparison** — Pros/cons table or comparison of different approaches found
6. **Community Insights** — Key discussions, common issues, and solutions from
   GitHub issues
7. A "Sources" section with links to specific repos, files, and issues

Guidelines:
- Use markdown formatting (headings, tables, code blocks)
- Include direct links to repos, files, and issues
- Show actual code snippets when available
- Compare approaches rather than just listing them
- Focus on practical, actionable insights
"""


def generate_report(
    query: str,
    findings_text: str,
    notes_text: str,
    source: str = "web",
) -> str:
    """Compile research findings into a structured markdown report.

    Returns the report as markdown text.
    """
    system = GITHUB_REPORT_PROMPT if source in ("github", "both") else SYSTEM_PROMPT
    prompt = (
        f"# Research Query\n{query}\n\n"
        f"# Research Findings\n{findings_text}\n\n"
        f"# Additional Notes\n{notes_text}\n\n"
        "Compile these findings into a comprehensive, well-structured markdown report. "
        "Include a Sources section at the end with all referenced URLs."
    )
    return chat(system_prompt=system, user_message=prompt)

