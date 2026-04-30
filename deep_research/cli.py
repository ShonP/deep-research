"""CLI entry point for deep-research."""

from __future__ import annotations

import click


class _ResearchGroup(click.Group):
    """Custom group that treats bare invocation (no subcommand) as the research command."""

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if args and args[0] in self.commands:
            return super().parse_args(ctx, args)
        if not args or args == ["--help"]:
            return super().parse_args(ctx, args)
        args = ["research", *args]
        return super().parse_args(ctx, args)


@click.group(cls=_ResearchGroup)
def main() -> None:
    """Deep Research — multi-round iterative research with AI agents."""


@main.command()
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
def research(
    query: str | None, max_rounds: int, output: str, research_dir: str, source: str, resume: str | None
) -> None:
    """Run deep research on a QUERY topic.

    Example:
        deep-research 'How to create compelling manga' --max-rounds 3 -o report.md
        deep-research 'React state management' --source github
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
