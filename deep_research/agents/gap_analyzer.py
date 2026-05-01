"""Gap analyzer agent: identifies research gaps in an existing report."""

from __future__ import annotations

from agent_framework import Agent

from deep_research.client import get_chat_client
from deep_research.middleware import llm_call_logging
from deep_research.models.state import GapAnalysisResponse, ResearchGap, ResearchTopic

SYSTEM_PROMPT = """\
You are a research gap analyst. Given an existing research report, identify the most
important gaps that need deeper investigation.

Analyze the report for:
1. Questions that remain unanswered or are only partially addressed
2. Topics that are mentioned but lack sufficient depth or evidence
3. Areas with weak, missing, or outdated sources
4. Important subtopics that were omitted entirely
5. Claims made without supporting data or citations

Rules:
- Return 3-5 gaps maximum (the most impactful ones)
- Each gap must have a specific, actionable research question
- Prioritize gaps that would most improve the report's value
- Don't flag cosmetic issues — focus on substantive knowledge gaps
"""


async def analyze_gaps(report_text: str) -> list[ResearchGap]:
    """Analyze a report and return identified research gaps."""
    agent = Agent(
        client=get_chat_client(),
        name="gap-analyzer",
        instructions=SYSTEM_PROMPT,
        middleware=[llm_call_logging],
    )
    prompt = (
        "Analyze this research report and identify the most important gaps:\n\n"
        f"{report_text[:12000]}\n\n"
        "Return a structured list of gaps with topic, question, and reason."
    )
    response = await agent.run(prompt, options={"response_format": GapAnalysisResponse})
    if response.value:
        return response.value.gaps
    return []


def gaps_to_topics(gaps: list[ResearchGap]) -> list[ResearchTopic]:
    """Convert research gaps into ResearchTopic objects for the research pipeline."""
    return [
        ResearchTopic(
            title=gap.topic,
            description=f"{gap.question} (Gap: {gap.reason})",
            subtopics=[gap.question],
        )
        for gap in gaps
    ]
