"""ResearchLoopExecutor — runs outline → research → judge loop."""
from __future__ import annotations

import json

from agent_framework import Executor, handler

from deep_research.agents.outline import create_outline_agent
from deep_research.agents.research import create_research_agent
from deep_research.models.state import Finding, ResearchState, ResearchTopic


class ResearchLoopExecutor(Executor):
    """Runs the iterative research loop: outline, research, judge, repeat."""

    def __init__(self) -> None:
        super().__init__(id="research_loop")

    @handler(input=ResearchState, output=ResearchState)
    async def run(self, state, ctx) -> None:
        # Step 1: Generate outline
        await self._generate_outline(state)

        # Step 2: Iterative research loop
        while state.current_round < state.max_rounds:
            state.current_round += 1
            print(f"\n📖 Research round {state.current_round}/{state.max_rounds}")

            topics_to_research = self._get_topics_for_round(state)
            if not topics_to_research:
                print("   No topics to research, finishing.")
                break

            await self._research_topics(state, topics_to_research)

            # Judge completeness (skip on last possible round)
            if state.current_round < state.max_rounds:
                has_gaps = await self._judge_completeness(state)
                if not has_gaps:
                    print("   ✅ Research is comprehensive, moving to report.")
                    break
                print(f"   🔄 Found {len(state.gaps)} gaps, continuing research...")
            else:
                print("   ⏹️  Max rounds reached, moving to report.")

        await ctx.send_message(state)

    async def _generate_outline(self, state: ResearchState) -> None:
        """Use the OutlineAgent to create a research outline."""
        print("\n📋 Generating research outline...")
        agent = create_outline_agent()
        result = await agent.run(
            f"Create a research outline for: {state.query}"
        )
        text = result.text or ""
        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
            topics = data.get("topics", [])
            for t in topics:
                state.outline.append(
                    ResearchTopic(
                        title=t["title"],
                        description=t.get("description", ""),
                        subtopics=t.get("subtopics", []),
                    )
                )
            print(f"   Created outline with {len(state.outline)} topics")
            for topic in state.outline:
                print(f"   • {topic.title}")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"   ⚠️  Outline parsing failed ({e}), creating fallback")
            state.outline.append(
                ResearchTopic(
                    title=state.query,
                    description=f"General research on: {state.query}",
                )
            )

    def _get_topics_for_round(self, state: ResearchState) -> list[str]:
        """Determine which topics to research this round."""
        if state.current_round == 1:
            # First round: research all outline topics
            topics = []
            for t in state.outline:
                topics.append(f"{t.title}: {t.description}")
                for sub in t.subtopics:
                    topics.append(f"{t.title} — {sub}")
            return topics
        else:
            # Subsequent rounds: research identified gaps
            return [f"Fill knowledge gap: {gap}" for gap in state.gaps]

    async def _research_topics(self, state: ResearchState, topics: list[str]) -> None:
        """Run the ResearchAgent on each topic."""
        for i, topic in enumerate(topics, 1):
            print(f"   🔍 [{i}/{len(topics)}] Researching: {topic[:80]}...")
            agent = create_research_agent()
            prompt = (
                f"Research the following topic thoroughly:\n\n{topic}\n\n"
                f"Context — this is part of a larger research project on: {state.query}"
            )
            try:
                result = await agent.run(prompt)
                summary = result.text or "(no response)"
                # Extract findings
                state.findings.append(
                    Finding(
                        topic=topic,
                        summary=summary,
                    )
                )
            except Exception as e:
                print(f"   ⚠️  Research failed for topic: {e}")
                state.findings.append(
                    Finding(topic=topic, summary=f"(research failed: {e})")
                )

    async def _judge_completeness(self, state: ResearchState) -> bool:
        """Evaluate whether research is complete or has gaps."""
        from agent_framework.github import GitHubCopilotAgent

        findings_text = "\n\n".join(
            f"### {f.topic}\n{f.summary}" for f in state.findings
        )
        prompt = (
            f"Original research query: {state.query}\n\n"
            f"Research findings so far:\n{findings_text}\n\n"
            "Evaluate these findings. Are there significant knowledge gaps?\n"
            "Respond with ONLY valid JSON (no markdown fences):\n"
            '{"complete": true/false, "gaps": ["gap description 1", ...]}\n'
            "Set complete=true if findings are comprehensive. "
            "Set complete=false and list specific gaps if important areas are missing."
        )
        agent = GitHubCopilotAgent(
            name="JudgeAgent",
            instructions="You evaluate research completeness. Respond only with JSON.",
        )
        result = await agent.run(prompt)
        text = (result.text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
            if data.get("complete", True):
                state.gaps = []
                return False
            state.gaps = data.get("gaps", [])
            return len(state.gaps) > 0
        except (json.JSONDecodeError, KeyError):
            # If parsing fails, assume complete
            state.gaps = []
            return False
