"""Data models for the research workflow state."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ResearchTopic:
    """A single topic/subtopic from the research outline."""

    title: str
    description: str
    subtopics: list[str] = field(default_factory=list)


@dataclass
class Finding:
    """A research finding with source attribution."""

    topic: str
    summary: str
    source_url: str = ""
    source_title: str = ""


@dataclass
class ResearchState:
    """Mutable state flowing through the research workflow."""

    query: str
    max_rounds: int = 3
    current_round: int = 0
    outline: list[ResearchTopic] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    report: str = ""
    output_path: str = "report.md"
