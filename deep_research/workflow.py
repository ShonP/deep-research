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
    query: str | None = None,
    *,
    max_rounds: int = 3,
    output_path: str = "report.md",
    research_base_dir: str = "reports",
    source: str = "web",
    resume: str | None = None,
) -> None:
    """Run the full research pipeline synchronously.

    When *resume* is the path to an existing research directory that contains
    a ``checkpoint.json``, the pipeline picks up where it left off instead of
    starting from scratch.
    """
    load_env()
    run_id = new_run_id()

    if resume:
        # ---- Resume mode ----
        checkpoint = _load_checkpoint(resume)
        if not checkpoint:
            raise FileNotFoundError(f"No checkpoint.json found in {resume}")

        step = checkpoint["step"]
        if step == "done":
            log.info("Research already complete in %s", resume)
            return

        research_dir = resume
        attach_file_handler(research_dir)
        state = _reconstruct_state(checkpoint, research_dir)

        completed_topics: set[str] = set(checkpoint.get("completed_topics", []))
        total_topics: list[str] = checkpoint.get("total_topics", [])

        log.info("Resuming research: %s", state.query)
        log.info(
            "Resume from step '%s', round %d, %d topics completed",
            step,
            state.current_round,
            len(completed_topics),
        )
        log.info("Research artifacts: %s", research_dir)
    else:
        # ---- Normal mode ----
        if not query:
            raise ValueError("Query is required when not resuming")

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

        step = None
        completed_topics = set()
        total_topics = []

        source_label = {"web": "🌐 Web", "github": "🐙 GitHub", "both": "🌐+🐙 Web & GitHub"}
        log.info("Starting deep research: %s", state.query)
        log.info("Source: %s | Max rounds: %d | Run: %s", source_label.get(state.source, state.source), state.max_rounds, run_id)
        log.info("Research artifacts: %s", research_dir)

    try:
        # Step 1: Generate outline
        if step is None:
            _generate_outline(state)
            _save_outline(state)
            _save_checkpoint(state, "outline")

        # Step 2: Iterative research loop
        # Handle mid-round resume: finish the in-progress round first.
        skip_loop = False

        if step == "research":
            _research_topics(state, total_topics, completed=completed_topics)
            _save_findings(state)
            _save_sources(state)

            if state.current_round < state.max_rounds:
                has_gaps = _judge_completeness(state)
                _save_checkpoint(state, "judge")
                if not has_gaps:
                    log.info("Research is comprehensive, moving to report.")
                    skip_loop = True
                else:
                    log.info("Found %d gaps, continuing research...", len(state.gaps))
            else:
                log.info("Max rounds reached, moving to report.")
                skip_loop = True

        if step == "judge":
            if not state.gaps:
                log.info("Research is comprehensive (from checkpoint), moving to report.")
                skip_loop = True
            else:
                log.info("Resuming with %d gaps from previous round...", len(state.gaps))

        if not skip_loop and step != "report":
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
                    _save_checkpoint(state, "judge")
                    if not has_gaps:
                        log.info("Research is comprehensive, moving to report.")
                        break
                    log.info("Found %d gaps, continuing research...", len(state.gaps))
                else:
                    log.info("Max rounds reached, moving to report.")

        # Step 3: Generate report
        if step == "report":
            report_path = os.path.join(state.research_dir, "report.md")
            if os.path.exists(report_path):
                with open(report_path, encoding="utf-8") as f:
                    state.report = f.read()
                log.info("Report loaded from checkpoint (%d chars)", len(state.report))
            else:
                _compile_report(state)
        else:
            _compile_report(state)
            _save_checkpoint(state, "report")

        # Step 4: Save output
        _save_output(state)
        _cleanup_checkpoint(state)
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


def _research_topics(
    state: ResearchState, topics: list[str], completed: set[str] | None = None
) -> None:
    """Run the appropriate research agent on each topic."""
    all_completed: set[str] = set(completed) if completed else set()
    for i, topic in enumerate(topics, 1):
        if topic in all_completed:
            log.info("[%d/%d] Skipping (already completed): %s", i, len(topics), topic[:60])
            continue

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

        all_completed.add(topic)
        _save_checkpoint(
            state, "research",
            completed_topics=list(all_completed),
            total_topics=topics,
        )


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


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------


def _save_checkpoint(
    state: ResearchState,
    step: str,
    completed_topics: list[str] | None = None,
    total_topics: list[str] | None = None,
) -> None:
    """Persist a checkpoint so the pipeline can resume after interruption."""
    if not state.research_dir:
        return
    checkpoint = {
        "step": step,
        "query": state.query,
        "source": state.source,
        "max_rounds": state.max_rounds,
        "current_round": state.current_round,
        "output_path": state.output_path,
        "started_at": state.started_at,
        "completed_topics": completed_topics or [],
        "total_topics": total_topics or [],
        "outline_data": state.outline_data,
        "gaps": state.gaps,
    }
    save_json(os.path.join(state.research_dir, "checkpoint.json"), checkpoint)
    log.debug("Checkpoint saved: step=%s", step)


def _load_checkpoint(research_dir: str) -> dict | None:
    """Load a checkpoint from *research_dir*, or return ``None``."""
    path = os.path.join(research_dir, "checkpoint.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def _cleanup_checkpoint(state: ResearchState) -> None:
    """Remove checkpoint.json after successful completion."""
    if not state.research_dir:
        return
    path = os.path.join(state.research_dir, "checkpoint.json")
    if os.path.exists(path):
        os.remove(path)
        log.debug("Checkpoint cleaned up")


def _reconstruct_state(checkpoint: dict, research_dir: str) -> ResearchState:
    """Rebuild *ResearchState* from a checkpoint and saved artifact files."""
    state = ResearchState(
        query=checkpoint["query"],
        max_rounds=checkpoint.get("max_rounds", 3),
        current_round=checkpoint.get("current_round", 0),
        source=checkpoint.get("source", "web"),
        output_path=checkpoint.get("output_path", "report.md"),
        research_dir=research_dir,
        started_at=checkpoint.get("started_at", ""),
        outline_data=checkpoint.get("outline_data", {}),
        gaps=checkpoint.get("gaps", []),
    )

    # Rebuild outline from outline.json
    outline_path = os.path.join(research_dir, "outline.json")
    if os.path.exists(outline_path):
        with open(outline_path, encoding="utf-8") as f:
            outline_data = json.load(f)
        state.outline_data = outline_data
        for t in outline_data.get("topics", []):
            state.outline.append(
                ResearchTopic(
                    title=t["title"],
                    description=t.get("description", ""),
                    subtopics=t.get("subtopics", []),
                )
            )

    # Rebuild findings from findings.json
    findings_path = os.path.join(research_dir, "findings.json")
    if os.path.exists(findings_path):
        with open(findings_path, encoding="utf-8") as f:
            findings_data = json.load(f)
        for rnd in findings_data.get("rounds", []):
            round_num = rnd.get("round", 0)
            for t in rnd.get("topics", []):
                state.findings.append(
                    Finding(
                        topic=t["topic"],
                        summary=t["summary"],
                        round_number=round_num,
                    )
                )

    # Rebuild sources from sources.json
    sources_path = os.path.join(research_dir, "sources.json")
    if os.path.exists(sources_path):
        with open(sources_path, encoding="utf-8") as f:
            sources_data = json.load(f)
        for s in sources_data:
            state.sources.append(
                SourceRecord(
                    url=s["url"],
                    title=s.get("title", ""),
                    fetched_at=s.get("fetched_at", ""),
                    query=s.get("query", ""),
                )
            )

    return state
