"""Local heuristic detector (offline fallback / demo).

This detector needs no API key and runs fully offline. It derives a rough AI
probability from classic stylometric signals that the literature associates
with machine text:

* **Low burstiness** - AI text keeps a steady sentence-length rhythm, humans
  vary a lot. We use the coefficient of variation of sentence lengths.
* **Low lexical diversity** is *not* on its own a strong signal, but combined
  with low burstiness it helps.
* **Connective / boilerplate density** - phrases like "moreover", "in
  conclusion", "it is important to note" are over-represented in LLM prose.
* **Punctuation regularity** - very uniform comma usage.

This is intentionally simple and is **not** a reliable detector: it exists so
the tool is runnable and testable without a paid API. For real results select
the ``gptzero`` or ``sapling`` provider. The score is deterministic for a given
text.
"""

from __future__ import annotations

import math
import re

from ..models import DetectionResult
from .base import Detector

_BOILERPLATE = (
    "moreover",
    "furthermore",
    "in conclusion",
    "it is important to note",
    "it is worth noting",
    "overall",
    "additionally",
    "however",
    "therefore",
    "in summary",
    "delve",
    "tapestry",
    "navigating",
    "realm",
    "underscore",
)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def _coef_variation(values: list[int]) -> float:
    if len(values) < 2:
        return 1.0  # not enough data -> assume human-like variability
    mean = sum(values) / len(values)
    if mean == 0:
        return 1.0
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var) / mean


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


class HeuristicDetector(Detector):
    name = "heuristic"

    def detect(self, text: str) -> DetectionResult:
        words = re.findall(r"[A-Za-zÀ-ÿ']+", text.lower())
        sentences = _sentences(text)

        if len(words) < 5:
            # Too short to judge: stay neutral.
            return DetectionResult.from_ai_probability(
                0.5, provider="heuristic", confidence="low",
                raw={"reason": "text too short"},
            )

        # 1) Burstiness proxy: low variation in sentence length -> AI-like.
        lengths = [len(re.findall(r"\w+", s)) for s in sentences]
        cv = _coef_variation(lengths)
        burstiness_signal = _clamp((0.6 - cv) / 0.6)  # 1 when cv~0, 0 when cv>=0.6

        # 2) Lexical diversity: type-token ratio. Low -> slightly AI-like.
        ttr = len(set(words)) / len(words)
        diversity_signal = _clamp((0.55 - ttr) / 0.35)

        # 3) Boilerplate / connective density.
        joined = " " + " ".join(words) + " "
        hits = sum(joined.count(" " + b.split()[0]) for b in _BOILERPLATE)
        boilerplate_signal = _clamp(hits / max(len(sentences), 1) / 0.5)

        # 4) Average sentence length: very long, even sentences -> AI-like.
        avg_len = sum(lengths) / len(lengths) if lengths else 0
        length_signal = _clamp((avg_len - 18) / 22)

        score = (
            0.45 * burstiness_signal
            + 0.20 * diversity_signal
            + 0.20 * boilerplate_signal
            + 0.15 * length_signal
        )
        score = _clamp(score)

        return DetectionResult.from_ai_probability(
            score,
            provider="heuristic",
            confidence="low",
            raw={
                "sentence_count": len(sentences),
                "cv_sentence_length": round(cv, 3),
                "type_token_ratio": round(ttr, 3),
                "boilerplate_hits": hits,
                "avg_sentence_length": round(avg_len, 1),
                "signals": {
                    "burstiness": round(burstiness_signal, 3),
                    "diversity": round(diversity_signal, 3),
                    "boilerplate": round(boilerplate_signal, 3),
                    "length": round(length_signal, 3),
                },
            },
        )
