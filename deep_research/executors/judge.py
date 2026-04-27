"""ResearchLoopExecutor — runs outline → research → judge loop."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from agent_framework import Executor, handler

from deep_research.agents.outline import create_outline_agent
from deep_research.agents.research import create_research_agent
from deep_research.agents.github_research import create_github_research_agent
from deep_research.models.state import Finding, ResearchState, ResearchTopic, SourceRecord
from deep_research.utils import extract_urls, save_json


GITHUB_OUTLINE_INSTRUCTIONS = """\
You are a research planner specializing in open-source software discovery. Given a
research query, produce a structured outline of topics optimized for searching
GitHub repositories, code patterns, and issue discussions.

Respond with ONLY valid JSON (no markdown fences) in this format:
{
  "topics": [
    {
      "title": "Topic title",
      "description": "What to search for on GitHub — frame as code/repo search queries",
      "subtopics": ["specific pattern to find", "alternative approach to search"]
    }
  ]
}

Generate 3-4 topics. Each topic should have at most 1-2 subtopics (keep it focused).
Total research queries will be topics + subtopics, so aim for 8-10 total maximum.
Frame descriptions as things to search for in code and repos,
e.g. "Find repos implementing X", "Search for code patterns using Y library",
"Look for issues discussing Z trade-offs".
"""


class ResearchLoopExecutor(Executor):
    """Runs the iterative research loop: outline, research, judge, repeat."""

    def __init__(self) -> None:
        super().__init__(id="research_loop")

    @handler(input=ResearchState, output=ResearchState)
    async def run(self, state, ctx) -> None:
        # Step 1: Generate outline
        await self._generate_outline(state)
        self._save_outline(state)

        # Step 2: Iterative research loop
        while state.current_round < state.max_rounds:
            state.current_round += 1
            print(f"\n📖 Research round {state.current_round}/{state.max_rounds}")

            topics_to_research = self._get_topics_for_round(state)
            if not topics_to_research:
                print("   No topics to research, finishing.")
                break

            await self._research_topics(state, topics_to_research)
            self._save_findings(state)
            self._save_sources(state)

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
        if state.source in ("github", "both"):
            # Override instructions for GitHub-optimized outline
            from agent_framework.github import GitHubCopilotAgent
            agent = GitHubCopilotAgent(
                name="OutlineAgent",
                instructions=GITHUB_OUTLINE_INSTRUCTIONS,
            )
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
            state.outline_data = data
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
            state.outline_data = {
                "topics": [
                    {
                        "title": state.query,
                        "description": f"General research on: {state.query}",
                        "subtopics": [],
                    }
                ]
            }

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
        """Run the research agent(s) on each topic based on source mode."""
        for i, topic in enumerate(topics, 1):
            print(f"   🔍 [{i}/{len(topics)}] Researching: {topic[:80]}...")
            prompt = (
                f"Research the following topic thoroughly:\n\n{topic}\n\n"
                f"Context — this is part of a larger research project on: {state.query}"
            )

            if state.source == "web":
                await self._run_agent(state, topic, prompt, create_research_agent)
            elif state.source == "github":
                await self._run_agent(state, topic, prompt, create_github_research_agent)
            else:  # both
                await self._run_agent(state, topic, prompt, create_research_agent, label="web")
                await self._run_agent(state, topic, prompt, create_github_research_agent, label="github")

    async def _run_agent(
        self,
        state: ResearchState,
        topic: str,
        prompt: str,
        agent_factory,
        label: str = "",
    ) -> None:
        """Run a single research agent and record findings."""
        if label:
            print(f"      [{label}]")
        try:
            agent = agent_factory()
            result = await agent.run(prompt, options={"timeout": 300})
            summary = result.text or "(no response)"
            finding = Finding(
                topic=topic if not label else f"[{label}] {topic}",
                summary=summary,
                round_number=state.current_round,
            )
            state.findings.append(finding)

            urls = extract_urls(summary)
            now = datetime.now(timezone.utc).isoformat()
            for url in urls:
                state.sources.append(
                    SourceRecord(url=url, title="", fetched_at=now, query=topic)
                )
        except Exception as e:
            print(f"   ⚠️  Research failed for topic: {e}")
            state.findings.append(
                Finding(
                    topic=topic,
                    summary=f"(research failed: {e})",
                    round_number=state.current_round,
                )
            )

    async def _judge_completeness(self, state: ResearchState) -> bool:
        """Evaluate whether research is complete or has gaps."""
        from agent_framework.github import GitHubCopilotAgent

        findings_text = "\n\n".join(
            f"### {f.topic}\n{f.summary}" for f in state.findings
        )

        if state.source in ("github", "both"):
            eval_criteria = (
                "Evaluate whether we found enough real-world implementations.\n"
                "Consider: Did we find diverse repos? Do we have actual code snippets?\n"
                "Are architecture patterns clear? Did we find relevant discussions?"
            )
        else:
            eval_criteria = (
                "Evaluate these findings. Are there significant knowledge gaps?"
            )

        prompt = (
            f"Original research query: {state.query}\n\n"
            f"Research findings so far:\n{findings_text}\n\n"
            f"{eval_criteria}\n"
            "Respond with ONLY valid JSON (no markdown fences):\n"
            '{"complete": true/false, "gaps": ["gap description 1", ...]}\n'
            "Set complete=true if findings are comprehensive. "
            "Set complete=false and list specific gaps if important areas are missing."
        )
        agent = GitHubCopilotAgent(
            name="JudgeAgent",
            instructions="You evaluate research completeness. Respond only with JSON.",
        )
        result = await agent.run(prompt, options={'timeout': 300})
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

    def _save_outline(self, state: ResearchState) -> None:
        """Save the outline data to outline.json."""
        if not state.research_dir:
            return
        save_json(
            os.path.join(state.research_dir, "outline.json"),
            state.outline_data,
        )

    def _save_findings(self, state: ResearchState) -> None:
        """Save accumulated findings grouped by round to findings.json."""
        if not state.research_dir:
            return
        rounds: dict[int, list[dict]] = {}
        for f in state.findings:
            rnd = f.round_number
            if rnd not in rounds:
                rounds[rnd] = []
            sources = extract_urls(f.summary)
            rounds[rnd].append({
                "topic": f.topic,
                "summary": f.summary,
                "sources": sources,
            })
        data = {
            "rounds": [
                {"round": rnd, "topics": topics}
                for rnd, topics in sorted(rounds.items())
            ]
        }
        save_json(os.path.join(state.research_dir, "findings.json"), data)

    def _save_sources(self, state: ResearchState) -> None:
        """Save all collected sources to sources.json."""
        if not state.research_dir:
            return
        # Deduplicate by URL while preserving order
        seen: set[str] = set()
        unique: list[dict] = []
        for s in state.sources:
            if s.url not in seen:
                seen.add(s.url)
                unique.append({
                    "url": s.url,
                    "title": s.title,
                    "fetched_at": s.fetched_at,
                    "query": s.query,
                })
        save_json(os.path.join(state.research_dir, "sources.json"), unique)
