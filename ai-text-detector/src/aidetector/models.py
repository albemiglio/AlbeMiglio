"""Data models shared across the AI-text-detector package."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Label(str, Enum):
    """Human readable classification of a span of text."""

    HUMAN = "human"
    MIXED = "mixed"
    AI = "ai"

    @classmethod
    def from_probability(cls, ai_probability: float) -> "Label":
        """Bucket a continuous AI probability into a coarse label."""
        if ai_probability >= 0.75:
            return cls.AI
        if ai_probability >= 0.40:
            return cls.MIXED
        return cls.HUMAN


@dataclass
class DetectionResult:
    """Outcome of running a detector over a single piece of text."""

    ai_probability: float
    """Probability in [0, 1] that the text was AI generated."""

    label: Label
    confidence: str = "unknown"  # high / medium / low / unknown
    provider: str = "unknown"
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def human_probability(self) -> float:
        return 1.0 - self.ai_probability

    @property
    def ai_percentage(self) -> float:
        return round(self.ai_probability * 100, 1)

    @classmethod
    def from_ai_probability(
        cls,
        ai_probability: float,
        *,
        provider: str = "unknown",
        confidence: str = "unknown",
        raw: dict[str, Any] | None = None,
    ) -> "DetectionResult":
        ai_probability = max(0.0, min(1.0, float(ai_probability)))
        return cls(
            ai_probability=ai_probability,
            label=Label.from_probability(ai_probability),
            confidence=confidence,
            provider=provider,
            raw=raw or {},
        )


@dataclass
class ParagraphResult:
    """Per-paragraph detection result."""

    index: int
    text: str
    word_count: int
    char_count: int
    result: DetectionResult | None = None
    error: str | None = None

    @property
    def ai_percentage(self) -> float | None:
        return None if self.result is None else self.result.ai_percentage


@dataclass
class DocumentResult:
    """Aggregated detection result for a whole document."""

    source: str
    paragraphs: list[ParagraphResult]
    overall: DetectionResult
    provider: str

    @property
    def total_ai_percentage(self) -> float:
        return self.overall.ai_percentage

    @property
    def total_human_percentage(self) -> float:
        return round(self.overall.human_probability * 100, 1)

    @property
    def analysed_paragraphs(self) -> list[ParagraphResult]:
        return [p for p in self.paragraphs if p.result is not None]
