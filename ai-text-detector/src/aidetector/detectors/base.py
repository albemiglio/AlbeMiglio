"""Detector abstraction.

Every detector turns a piece of text into a :class:`DetectionResult` carrying
an AI probability in [0, 1]. Keeping the interface this small lets the analyzer
work the same way whether the score comes from a remote API (GPTZero, Sapling,
...) or from the local heuristic fallback.
"""

from __future__ import annotations

import abc

from ..models import DetectionResult


class Detector(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def detect(self, text: str) -> DetectionResult:
        """Return the AI-detection result for a single text span."""

    def detect_batch(self, texts: list[str]) -> list[DetectionResult]:
        """Default sequential batch; APIs may override with native batching."""
        return [self.detect(t) for t in texts]
