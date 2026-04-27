"""Research pipeline — replaces the MAF Workflow with a simple sequential pipeline."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from deep_research.agents.outline import generate_outline
from deep_research.agents.research import research_topic
from deep_research.agents.github_research import github_research_topic
from deep_research.agents.report import generate_report
from deep_research.llm import chat
from deep_research.log import log, new_run_id, attach_file_handler, detach_file_handler
from deep_research.models.state import Finding, ResearchState, ResearchTopic, SourceRecord
from deep_research.utils import create_research_dir, extract_urls, load_env, save_json, save_text


def run_research(
    query: str,
    *,
    max_rounds: int = 3,
    output_path: str = "report.md",
    research_base_dir: str = "reports",
    source: str = "web",
) -> None:
    """Run the full research pipeline synchronously."""
    load_env()
    run_id = new_run_id()

    research_dir = create_research_dir(query, research_base_dir)
    attach_file_handler(research_dir)
    started_at = datetime.now(timezone.utc).isoformat()

    state = ResearchState(
        query=query,
        max_rounds=max_rounds,
        source=source,
        output_path=output_path,
        research_dir=research_dir,
        started_at=started_at,
    )

    source_label = {"web": "🌐 Web", "github": "🐙 GitHub", "both": "🌐+🐙 Web & GitHub"}
    log.info("Starting deep research: %s", state.query)
    log.info("Source: %s | Max rounds: %d | Run: %s", source_label.get(state.source, state.source), state.max_rounds, run_id)
    log.info("Research artifacts: %s", research_dir)

    try:
        # Step 1: Generate outline
        _generate_outline(state)
        _save_outline(state)

        # Step 2: Iterative research loop
        while state.current_round < state.max_rounds:
            state.current_round += 1
            log.info("Research round %d/%d", state.current_round, state.max_rounds)

            topics = _get_topics_for_round(state)
            if not topics:
                log.info("No topics to research, finishing.")
                break

            _research_topics(state, topics)
            _save_findings(state)
            _save_sources(state)

            # Judge completeness (skip on last round)
            if state.current_round < state.max_rounds:
                has_gaps = _judge_completeness(state)
                if not has_gaps:
                    log.info("Research is comprehensive, moving to report.")
                    break
                log.info("Found %d gaps, continuing research...", len(state.gaps))
            else:
                log.info("Max rounds reached, moving to report.")

        # Step 3: Generate report
        _compile_report(state)

        # Step 4: Save output
        _save_output(state)
    except Exception:
        log.exception("Research pipeline failed")
        raise
    finally:
        detach_file_handler()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_outline(state: ResearchState) -> None:
    """Use the outline agent to create a research outline."""
    log.info("Generating research outline...")
    text = generate_outline(state.query, state.source)

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
        log.info("Outline created: %d topics", len(state.outline))
        for topic in state.outline:
            subs = len(topic.subtopics)
            log.debug("  • %s (%d subtopics)", topic.title, subs)
    except (json.JSONDecodeError, KeyError) as e:
        log.warning("Outline parsing failed (%s), using fallback", e)
        log.debug("Raw outline response: %s", text[:500])
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


def _get_topics_for_round(state: ResearchState) -> list[str]:
    """Determine which topics to research this round."""
    if state.current_round == 1:
        topics = []
        for t in state.outline:
            topics.append(f"{t.title}: {t.description}")
            for sub in t.subtopics:
                topics.append(f"{t.title} — {sub}")
        log.debug("Round 1: %d research queries from outline", len(topics))
        return topics
    else:
        log.debug("Round %d: %d gap-fill queries", state.current_round, len(state.gaps))
        return [f"Fill knowledge gap: {gap}" for gap in state.gaps]


def _research_topics(state: ResearchState, topics: list[str]) -> None:
    """Run the appropriate research agent on each topic."""
    for i, topic in enumerate(topics, 1):
        log.info("[%d/%d] Researching: %s", i, len(topics), topic[:80])

        if state.source == "web":
            _run_research(state, topic, "web")
        elif state.source == "github":
            _run_research(state, topic, "github")
        else:  # both
            _run_research(state, topic, "web", label="web")
            _run_research(state, topic, "github", label="github")

        # Save incrementally after each topic
        _save_findings(state)
        _save_sources(state)


def _run_research(
    state: ResearchState,
    topic: str,
    mode: str,
    label: str = "",
) -> None:
    """Run a single research call and record findings."""
    ctx = f"[{label}] " if label else ""
    log.debug("%sStarting %s research for: %s", ctx, mode, topic[:60])
    try:
        if mode == "web":
            summary = research_topic(topic, state.query)
        else:
            summary = github_research_topic(topic, state.query)

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
        log.debug("%sFinished research, %d chars, %d URLs found", ctx, len(summary), len(urls))
    except Exception as e:
        log.error("Research failed for topic '%s': %s", topic[:60], e)
        state.findings.append(
            Finding(
                topic=topic,
                summary=f"(research failed: {e})",
                round_number=state.current_round,
            )
        )


def _judge_completeness(state: ResearchState) -> bool:
    """Evaluate whether research is complete or has gaps."""
    log.debug("Judging research completeness...")
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
    text = chat(
        system_prompt="You evaluate research completeness. Respond only with JSON.",
        user_message=prompt,
        reasoning_effort="low",
    )

    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        data = json.loads(text)
        if data.get("complete", True):
            state.gaps = []
            log.debug("Judge: research complete")
            return False
        state.gaps = data.get("gaps", [])
        log.debug("Judge: %d gaps found: %s", len(state.gaps), state.gaps)
        return len(state.gaps) > 0
    except (json.JSONDecodeError, KeyError) as e:
        log.warning("Judge response parsing failed (%s), assuming complete", e)
        state.gaps = []
        return False


def _compile_report(state: ResearchState) -> None:
    """Compile all findings into a final report."""
    log.info("Compiling research report from %d findings...", len(state.findings))
    findings_text = "\n\n".join(
        f"### {f.topic}\n{f.summary}" for f in state.findings
    )
    notes_text = "\n".join(f"- {n}" for n in state.notes) if state.notes else "(none)"

    state.report = generate_report(
        query=state.query,
        findings_text=findings_text,
        notes_text=notes_text,
        source=state.source,
    )
    if not state.report:
        state.report = "(report generation failed)"
        log.error("Report generation returned empty")
    else:
        log.info("Report generated: %d characters", len(state.report))


def _save_output(state: ResearchState) -> None:
    """Write the final report and metadata to files."""
    path = state.output_path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    save_text(path, state.report)
    log.info("Report written to %s", path)

    if state.research_dir:
        report_path = os.path.join(state.research_dir, "report.md")
        save_text(report_path, state.report)

        finished_at = datetime.now(timezone.utc).isoformat()
        meta = {
            "query": state.query,
            "started_at": state.started_at,
            "finished_at": finished_at,
            "max_rounds": state.max_rounds,
            "source": state.source,
            "topics_count": len(state.outline),
            "findings_count": len(state.findings),
            "sources_count": len(state.sources),
        }
        save_json(os.path.join(state.research_dir, "meta.json"), meta)
        log.info("All artifacts saved to: %s", state.research_dir)


def _save_outline(state: ResearchState) -> None:
    if not state.research_dir:
        return
    save_json(os.path.join(state.research_dir, "outline.json"), state.outline_data)
    log.debug("Saved outline.json")


def _save_findings(state: ResearchState) -> None:
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
    log.debug("Saved findings.json (%d findings)", len(state.findings))


def _save_sources(state: ResearchState) -> None:
    if not state.research_dir:
        return
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
    log.debug("Saved sources.json (%d unique sources)", len(unique))
