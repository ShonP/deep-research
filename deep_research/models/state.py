"""Data models for the research workflow state."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ResearchTopic:
    """A single topic/subtopic from the research outline."""

    title: str
    description: str
    subtopics: list[str] = field(default_factory=list)


@dataclass
class Source:
    """A structured source with metadata."""

    url: str
    title: str = ""
    snippet: str = ""
    relevance_score: float = 0.0
    accessed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "url": self.url, "title": self.title, "snippet": self.snippet,
            "relevance_score": self.relevance_score, "accessed_at": self.accessed_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Source:
        return cls(
            url=d.get("url", ""), title=d.get("title", ""),
            snippet=d.get("snippet", ""), relevance_score=d.get("relevance_score", 0.0),
            accessed_at=d.get("accessed_at", ""),
        )

    @classmethod
    def from_url(cls, url: str, query: str = "") -> Source:
        return cls(url=url, accessed_at=datetime.now(timezone.utc).isoformat())


@dataclass
class Citation:
    """A structured citation linking a claim to a source."""

    claim: str
    source_url: str
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {"claim": self.claim, "source_url": self.source_url, "confidence": self.confidence}

    @classmethod
    def from_dict(cls, d: dict) -> Citation:
        return cls(
            claim=d.get("claim", ""), source_url=d.get("source_url", ""),
            confidence=d.get("confidence", 0.0),
        )


@dataclass
class Finding:
    """A research finding with structured source attribution."""

    topic: str
    summary: str
    round_number: int = 0
    sources: list[Source] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "topic": self.topic, "summary": self.summary, "round": self.round_number,
            "sources": [s.to_dict() for s in self.sources],
            "citations": [c.to_dict() for c in self.citations],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Finding:
        return cls(
            topic=d.get("topic", ""), summary=d.get("summary", ""),
            round_number=d.get("round", 0),
            sources=[Source.from_dict(s) for s in d.get("sources", [])],
            citations=[Citation.from_dict(c) for c in d.get("citations", [])],
        )


@dataclass
class CriticFeedback:
    """Structured feedback from the critic agent."""

    quality_score: float = 0.0
    gaps: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    complete: bool = False

    def to_dict(self) -> dict:
        return {
            "quality_score": self.quality_score, "gaps": self.gaps,
            "suggestions": self.suggestions, "complete": self.complete,
        }


@dataclass
class SourceRecord:
    """A URL encountered during research (legacy compat)."""

    url: str
    title: str = ""
    fetched_at: str = ""
    query: str = ""


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
    source: str = "web"
    report: str = ""
    output_path: str = "report.md"
    research_dir: str = ""
    started_at: str = ""
    sources: list[SourceRecord] = field(default_factory=list)
    outline_data: dict = field(default_factory=dict)
    raw_notes: list[str] = field(default_factory=list)
    compressed_notes: list[str] = field(default_factory=list)
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
