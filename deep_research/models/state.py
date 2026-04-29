"""Data models for the research workflow state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ResearchTopic(BaseModel):
    """A single topic/subtopic from the research outline."""

    title: str
    description: str
    subtopics: list[str] = Field(default_factory=list)


class Source(BaseModel):
    """A structured source with metadata."""

    url: str
    title: str = ""
    snippet: str = ""
    relevance_score: float = 0.0
    accessed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Source:
        return cls.model_validate(d)

    @classmethod
    def from_url(cls, url: str, query: str = "") -> Source:
        return cls(url=url, accessed_at=datetime.now(UTC).isoformat())


class Citation(BaseModel):
    """A structured citation linking a claim to a source."""

    claim: str
    source_url: str
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Citation:
        return cls.model_validate(d)


class Finding(BaseModel):
    """A research finding with structured source attribution."""

    topic: str
    summary: str
    round_number: int = Field(default=0, alias="round")
    sources: list[Source] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)

    model_config = {"populate_by_name": True}

    def to_dict(self) -> dict[str, Any]:
        data = self.model_dump()
        data["round"] = data.pop("round_number")
        return data

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Finding:
        return cls.model_validate(d)


class CriticFeedback(BaseModel):
    """Structured feedback from the critic agent."""

    quality_score: float = 0.0
    gaps: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    complete: bool = False

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class OutlineResponse(BaseModel):
    """Structured outline output from the outline agent."""

    topics: list[ResearchTopic]


class CompressedFinding(BaseModel):
    """A single compressed finding."""

    topic: str
    summary: str
    key_sources: list[str] = Field(default_factory=list)


class CompressedFindings(BaseModel):
    """Structured output from the compressor agent."""

    compressed: list[CompressedFinding]
    notes: list[str] = Field(default_factory=list)


class RefinedQueries(BaseModel):
    """Structured output from the query refiner agent."""

    queries: list[str]


class SourceRecord(BaseModel):
    """A URL encountered during research (legacy compat)."""

    url: str
    title: str = ""
    fetched_at: str = ""
    query: str = ""


class ResearchState(BaseModel):
    """Mutable state flowing through the research workflow."""

    query: str
    max_rounds: int = 3
    current_round: int = 0
    outline: list[ResearchTopic] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    source: str = "web"
    report: str = ""
    output_path: str = "report.md"
    research_dir: str = ""
    started_at: str = ""
    sources: list[SourceRecord] = Field(default_factory=list)
    outline_data: dict[str, Any] = Field(default_factory=dict)
    raw_notes: list[str] = Field(default_factory=list)
    compressed_notes: list[str] = Field(default_factory=list)
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
