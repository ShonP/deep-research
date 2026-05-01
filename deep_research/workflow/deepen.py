"""Deepen workflow: takes an existing report, finds gaps, researches them, and merges."""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

from deep_research.agents.gap_analyzer import analyze_gaps, gaps_to_topics
from deep_research.log import attach_file_handler, detach_file_handler, log, new_run_id
from deep_research.middleware import reset_token_usage
from deep_research.utils import create_research_dir, save_json
from deep_research.workflow.pipeline_steps import do_report, do_research_round


def _extract_title(report_text: str) -> str:
    """Extract the query/title from a report's first # heading."""
    match = re.search(r"^#\s+(.+)$", report_text, re.MULTILINE)
    return match.group(1).strip() if match else "Research report"


def _deepened_path(original_path: str) -> str:
    """Derive output path: foo.md → foo-deepened.md."""
    p = Path(original_path)
    return str(p.with_stem(f"{p.stem}-deepened"))


async def run_deepen_async(
    report_path: str,
    *,
    max_rounds: int = 2,
    source: str = "web",
    extra_providers: list[str] | None = None,
    research_base_dir: str = "reports",
) -> None:
    """Read an existing report, identify gaps, research them, and merge."""
    run_id = new_run_id()
    reset_token_usage()

    report_text = Path(report_path).read_text(encoding="utf-8")
    query = _extract_title(report_text)

    research_dir = create_research_dir(f"deepen-{query}", research_base_dir)
    attach_file_handler(research_dir)

    if extra_providers:
        from deep_research.tools.registry import register_extra_providers
        register_extra_providers(extra_providers)

    try:
        log.info("Deepening report: %s", report_path)
        log.info("Extracted query: %s | Max rounds: %d | Run: %s", query, max_rounds, run_id)

        log.info("Step 1: Analyzing gaps in existing report...")
        gaps = await analyze_gaps(report_text)

        if not gaps:
            log.info("No substantive gaps found — report is already comprehensive.")
            return

        log.info("Found %d gaps to investigate:", len(gaps))
        for g in gaps:
            log.info("  • %s — %s", g.topic, g.question)

        topics = gaps_to_topics(gaps)
        save_json(os.path.join(research_dir, "gaps.json"), [g.model_dump() for g in gaps])
        save_json(os.path.join(research_dir, "outline.json"), {"topics": [t.model_dump() for t in topics]})

        state = {
            "query": query,
            "source": source,
            "research_dir": research_dir,
            "topics": [t.model_dump() for t in topics],
            "findings": [],
            "sources": [],
            "gaps": [],
            "notes": [],
            "raw_notes": [],
            "compressed_notes": [],
            "research_complete": False,
            "report": "",
            "base_report_summary": report_text[:3000],
        }

        log.info("Step 2: Researching gaps...")
        round_num = 0
        while not state.get("research_complete", False):
            round_num += 1
            state = await do_research_round(state, round_num, max_rounds)

        log.info("Step 3: Generating deepened report sections...")
        state = await do_report(state)
        new_content = state.get("report", "")

        merged = _merge_reports(report_text, new_content, gaps)
        output_path = _deepened_path(report_path)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        Path(output_path).write_text(merged, encoding="utf-8")

        log.info("Deepened report saved: %s", output_path)
        log.info("Original preserved: %s", report_path)

    except Exception:
        log.exception("Deepen pipeline failed")
        raise
    finally:
        detach_file_handler()


def _merge_reports(original: str, new_sections: str, gaps: list) -> str:
    """Merge original report with new deepened research."""
    gap_summary = "\n".join(f"- **{g.topic}**: {g.question}" for g in gaps)
    separator = (
        "\n\n---\n\n"
        "## Deepened Research\n\n"
        "The following sections were added by re-analyzing the original report "
        "and researching identified gaps.\n\n"
        f"### Gaps Investigated\n\n{gap_summary}\n\n"
    )
    return f"{original.rstrip()}{separator}{new_sections.strip()}\n"


def run_deepen(
    report_path: str,
    *,
    max_rounds: int = 2,
    source: str = "web",
    extra_providers: list[str] | None = None,
    research_base_dir: str = "reports",
) -> None:
    """Synchronous wrapper for the deepen pipeline."""
    asyncio.run(
        run_deepen_async(
            report_path,
            max_rounds=max_rounds,
            source=source,
            extra_providers=extra_providers,
            research_base_dir=research_base_dir,
        )
    )
