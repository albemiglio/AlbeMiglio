"""Local heuristic detector (offline fallback / demo).

This detector needs no API key and runs fully offline. It derives a rough AI
probability from classic stylometric signals associated with machine text:

* **Low burstiness** - AI keeps a steady sentence-length rhythm; humans vary a
  lot. Measured as the coefficient of variation of sentence lengths.
* **Lexical diversity** (type-token ratio) - low diversity is weakly AI-like.
* **Connective / boilerplate density** - phrases like "moreover" / "inoltre" /
  "in conclusione" are over-represented in LLM prose. Language-aware.
* **Sentence-length regularity** - long, uniform sentences are AI-like.

Signals are combined and passed through a logistic squashing function so the
output is a *continuous* probability rather than a few coarse steps. This is
**not** a reliable detector: it exists so the tool is runnable and testable
without a paid API. For real results select ``winston`` (best for Italian),
``gptzero`` or ``sapling``. The score is deterministic for a given text.
"""

from __future__ import annotations

import math
import re

from ..models import DetectionResult
from .base import Detector

_BOILERPLATE = {
    "en": (
        "moreover", "furthermore", "in conclusion", "it is important to note",
        "it is worth noting", "overall", "additionally", "however",
        "therefore", "in summary", "delve", "tapestry", "navigating",
        "realm", "underscore", "crucial", "comprehensive", "leverage",
    ),
    "it": (
        "inoltre", "tuttavia", "in conclusione", "è importante notare",
        "è bene sottolineare", "in sintesi", "pertanto", "di conseguenza",
        "in particolare", "in questo contesto", "in tal senso", "altresì",
        "occorre sottolineare", "va evidenziato", "risulta fondamentale",
        "approfondire", "cruciale", "fondamentale", "ambito", "panorama",
    ),
}


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


def _logistic(x: float, *, midpoint: float = 0.5, steepness: float = 6.0) -> float:
    """Smoothly map a raw [0, 1] signal mix to a probability, centred on a
    neutral midpoint so that average text lands near 0.5 instead of snapping to
    discrete steps."""
    return 1.0 / (1.0 + math.exp(-steepness * (x - midpoint)))


class HeuristicDetector(Detector):
    name = "heuristic"

    def __init__(self, language: str = "en"):
        self.language = (language or "en").lower()
        self._boilerplate = _BOILERPLATE.get(
            self.language, _BOILERPLATE["en"]
        )

    def detect(self, text: str) -> DetectionResult:
        words = re.findall(r"[A-Za-zÀ-ÿ']+", text.lower())
        sentences = _sentences(text)

        if len(words) < 5:
            return DetectionResult.from_ai_probability(
                0.5, provider="heuristic", confidence="low",
                raw={"reason": "text too short", "language": self.language},
            )

        # 1) Burstiness proxy: low variation in sentence length -> AI-like.
        lengths = [len(re.findall(r"\w+", s)) for s in sentences]
        cv = _coef_variation(lengths)
        burstiness_signal = _clamp((0.6 - cv) / 0.6)

        # 2) Lexical diversity: type-token ratio. Low -> slightly AI-like.
        ttr = len(set(words)) / len(words)
        diversity_signal = _clamp((0.55 - ttr) / 0.35)

        # 3) Boilerplate / connective density (language-aware).
        lowered = " " + " ".join(words) + " "
        hits = sum(lowered.count(" " + b.split()[0] + " ") for b in self._boilerplate)
        boilerplate_signal = _clamp(hits / max(len(sentences), 1) / 0.5)

        # 4) Average sentence length: long, even sentences -> AI-like.
        avg_len = sum(lengths) / len(lengths) if lengths else 0
        length_signal = _clamp((avg_len - 18) / 22)

        raw_mix = (
            0.42 * burstiness_signal
            + 0.18 * diversity_signal
            + 0.22 * boilerplate_signal
            + 0.18 * length_signal
        )
        # Continuous squashing instead of a coarse linear sum.
        score = _logistic(raw_mix, midpoint=0.45, steepness=5.5)

        return DetectionResult.from_ai_probability(
            score,
            provider="heuristic",
            confidence="low",
            raw={
                "language": self.language,
                "sentence_count": len(sentences),
                "cv_sentence_length": round(cv, 3),
                "type_token_ratio": round(ttr, 3),
                "boilerplate_hits": hits,
                "avg_sentence_length": round(avg_len, 1),
                "raw_mix": round(raw_mix, 3),
                "signals": {
                    "burstiness": round(burstiness_signal, 3),
                    "diversity": round(diversity_signal, 3),
                    "boilerplate": round(boilerplate_signal, 3),
                    "length": round(length_signal, 3),
                },
            },
        )
