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
def main(query: str, max_rounds: int, output: str) -> None:
    """Run deep research on a QUERY topic.

    Performs multi-round iterative web research using AI agents and
    produces a structured markdown report with citations.

    Example:
        deep-research 'How to create compelling manga' --max-rounds 3 -o report.md
    """
    from deep_research.workflow import run_research

    run_research(query, max_rounds=max_rounds, output_path=output)


if __name__ == "__main__":
    main()
