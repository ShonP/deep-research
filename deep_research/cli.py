"""CLI entry point for deep-research."""
from __future__ import annotations

import click


@click.command()
@click.argument("query", required=False, default=None)
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
@click.option(
    "--resume",
    default=None,
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Resume from a previous research directory (path to the research dir).",
)
def main(query: str | None, max_rounds: int, output: str, research_dir: str, source: str, resume: str | None) -> None:
    """Run deep research on a QUERY topic.

    Performs multi-round iterative research using AI agents and
    produces a structured markdown report with citations.

    Example:
        deep-research 'How to create compelling manga' --max-rounds 3 -o report.md
        deep-research 'React state management' --source github
        deep-research --resume reports/2025-01-15-my-topic
    """
    if not query and not resume:
        raise click.UsageError("Either QUERY argument or --resume option is required.")
    if query and resume:
        raise click.UsageError("Cannot specify both QUERY and --resume.")

    from deep_research.workflow import run_research

    run_research(
        query,
        max_rounds=max_rounds,
        output_path=output,
        research_base_dir=research_dir,
        source=source,
        resume=resume,
    )


if __name__ == "__main__":
    main()
