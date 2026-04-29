"""Critic agent: evaluates research quality and identifies gaps."""

from __future__ import annotations

from agent_framework._agents import Agent

from deep_research.client import get_chat_client
from deep_research.middleware import llm_call_logging
from deep_research.models.state import CriticFeedback

SYSTEM_PROMPT = """\
You are a research quality evaluator. You assess whether research findings
are comprehensive, diverse, and well-supported.

Check:
1. Are findings diverse (multiple perspectives, not just one source)?
2. Do we have actual code examples, data, or concrete evidence?
3. Are the sources reliable and varied?
4. Are there significant knowledge gaps remaining?

Rules:
- quality_score: 0.0 = useless, 0.5 = adequate, 1.0 = excellent
- complete: true only if quality_score >= 0.7 AND no critical gaps
- gaps: specific knowledge gaps that need filling (max 3)
- suggestions: actionable improvements for next round
"""


async def evaluate_research(
    query: str,
    findings: list[dict],
    source: str = "web",
) -> CriticFeedback:
    """Evaluate research quality and return structured feedback."""
    findings_text = "\n\n".join(f"### {f['topic']}\n{f['summary']}" for f in findings)
    agent = Agent(
        client=get_chat_client(),
        name="research-critic",
        instructions=SYSTEM_PROMPT,
        middleware=[llm_call_logging],
    )
    prompt = (
        f"Original research query: {query}\n"
        f"Research source type: {source}\n\n"
        f"Research findings:\n{findings_text}\n\n"
        "Evaluate the quality and completeness of these findings."
    )
    response = await agent.run(prompt, options={"response_format": CriticFeedback})
    if response.value:
        feedback = response.value
        feedback.gaps = feedback.gaps[:3]
        return feedback
    return CriticFeedback(complete=True, quality_score=0.5)
