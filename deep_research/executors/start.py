"""StartExecutor — receives the research query and creates initial state."""
from __future__ import annotations

from agent_framework import Executor, handler

from deep_research.models.state import ResearchState


class StartExecutor(Executor):
    """Entry point: wraps the CLI input into a ResearchState."""

    def __init__(self, query: str, max_rounds: int = 3, output_path: str = "report.md"):
        super().__init__(id="start")
        self._query = query
        self._max_rounds = max_rounds
        self._output_path = output_path

    @handler(input=str, output=ResearchState)
    async def run(self, message, ctx) -> None:
        state = ResearchState(
            query=self._query,
            max_rounds=self._max_rounds,
            output_path=self._output_path,
        )
        print(f"🔬 Starting deep research: {state.query}")
        print(f"   Max rounds: {state.max_rounds}")
        await ctx.send_message(state)
