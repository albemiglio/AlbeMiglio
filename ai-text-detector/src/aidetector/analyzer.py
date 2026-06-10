"""Document analysis: orchestrates parsing, per-paragraph detection and the
length-weighted aggregation of the document-level score."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from .detectors import get_detector
from .detectors.base import Detector
from .document import load_paragraphs, split_paragraphs
from .models import DetectionResult, DocumentResult, ParagraphResult

# Paragraphs shorter than this many words are scored but flagged as unreliable,
# and excluded from the weighted document total to avoid noise.
MIN_RELIABLE_WORDS = 8


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text))


class Analyzer:
    """Run a :class:`Detector` over every paragraph of a document."""

    def __init__(
        self,
        detector: Detector | None = None,
        *,
        provider: str = "heuristic",
        api_key: str | None = None,
        max_workers: int = 4,
    ):
        self.detector = detector or get_detector(provider, api_key=api_key)
        self.max_workers = max(1, max_workers)

    # -- public API ------------------------------------------------------

    def analyze_file(self, path: str | Path) -> DocumentResult:
        paragraphs = load_paragraphs(path)
        return self._analyze(paragraphs, source=str(path))

    def analyze_text(
        self, text: str, *, source: str = "<text>"
    ) -> DocumentResult:
        return self._analyze(split_paragraphs(text), source=source)

    # -- internals -------------------------------------------------------

    def _analyze(
        self,
        paragraphs: list[str],
        *,
        source: str,
        progress: Callable[[int, int], None] | None = None,
    ) -> DocumentResult:
        results: list[ParagraphResult] = [
            ParagraphResult(
                index=i,
                text=para,
                word_count=_word_count(para),
                char_count=len(para),
            )
            for i, para in enumerate(paragraphs)
        ]

        def _run(pr: ParagraphResult) -> None:
            try:
                pr.result = self.detector.detect(pr.text)
            except Exception as exc:  # noqa: BLE001 - surface API errors per-para
                pr.error = f"{type(exc).__name__}: {exc}"

        if results:
            with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
                list(pool.map(_run, results))

        overall = self._aggregate(results)
        return DocumentResult(
            source=source,
            paragraphs=results,
            overall=overall,
            provider=self.detector.name,
        )

    def _aggregate(self, paragraphs: list[ParagraphResult]) -> DetectionResult:
        """Document score = word-weighted mean of reliable paragraph scores."""
        weighted_sum = 0.0
        weight_total = 0
        for pr in paragraphs:
            if pr.result is None or pr.word_count < MIN_RELIABLE_WORDS:
                continue
            weighted_sum += pr.result.ai_probability * pr.word_count
            weight_total += pr.word_count

        if weight_total == 0:
            # Fall back to a simple mean over whatever we managed to score.
            scored = [p.result for p in paragraphs if p.result is not None]
            if not scored:
                return DetectionResult.from_ai_probability(
                    0.0, provider=self.detector.name, confidence="low",
                    raw={"note": "no paragraph could be scored"},
                )
            mean = sum(r.ai_probability for r in scored) / len(scored)
            return DetectionResult.from_ai_probability(
                mean, provider=self.detector.name, confidence="low"
            )

        mean = weighted_sum / weight_total
        return DetectionResult.from_ai_probability(
            mean,
            provider=self.detector.name,
            confidence="medium",
            raw={"weighting": "word_count", "weighted_words": weight_total},
        )
