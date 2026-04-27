"""CLI entry point for deep-research."""
from __future__ import annotations

import click


@click.command()
@click.argument("query")
@click.option(
    "--max-rounds",
    default=3,
    type=int,
    show_default=True,
    help="Maximum number of research iterations.",
)
@click.option(
    "--output",
    "-o",
    default="report.md",
    show_default=True,
    help="Output file path for the research report.",
)
@click.option(
    "--research-dir",
    default="reports",
    show_default=True,
    help="Base directory for research artifacts.",
)
@click.option(
    "--source",
    type=click.Choice(["web", "github", "both"]),
    default="web",
    show_default=True,
    help="Research source: web search, GitHub search, or both.",
)
def main(query: str, max_rounds: int, output: str, research_dir: str, source: str) -> None:
    """Run deep research on a QUERY topic.

    Performs multi-round iterative research using AI agents and
    produces a structured markdown report with citations.

    Example:
        deep-research 'How to create compelling manga' --max-rounds 3 -o report.md
        deep-research 'React state management' --source github
    """
    from deep_research.workflow import run_research

    run_research(
        query,
        max_rounds=max_rounds,
        output_path=output,
        research_base_dir=research_dir,
        source=source,
    )


if __name__ == "__main__":
    main()
