"""StartExecutor — receives the research query and creates initial state."""
from __future__ import annotations

from datetime import datetime, timezone

from agent_framework import Executor, handler

from deep_research.models.state import ResearchState
from deep_research.utils import create_research_dir


class StartExecutor(Executor):
    """Entry point: wraps the CLI input into a ResearchState."""

    def __init__(
        self,
        query: str,
        max_rounds: int = 3,
        output_path: str = "report.md",
        research_base_dir: str = "reports",
    ):
        super().__init__(id="start")
        self._query = query
        self._max_rounds = max_rounds
        self._output_path = output_path
        self._research_base_dir = research_base_dir

    @handler(input=str, output=ResearchState)
    async def run(self, message, ctx) -> None:
        research_dir = create_research_dir(self._query, self._research_base_dir)
        started_at = datetime.now(timezone.utc).isoformat()

        state = ResearchState(
            query=self._query,
            max_rounds=self._max_rounds,
            output_path=self._output_path,
            research_dir=research_dir,
            started_at=started_at,
        )
        print(f"🔬 Starting deep research: {state.query}")
        print(f"   Max rounds: {state.max_rounds}")
        print(f"   Research artifacts: {research_dir}")
        await ctx.send_message(state)
