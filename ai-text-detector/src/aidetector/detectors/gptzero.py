"""GPTZero detector.

Docs: https://gptzero.stoplight.io/docs/gptzero-api

We send each text span to ``POST /v2/predict/text`` and read the AI probability
from ``documents[0].class_probabilities.ai`` (falling back to
``completely_generated_prob`` / ``average_generated_prob`` for older payloads).
GPTZero also returns per-sentence and per-paragraph breakdowns, but since the
analyzer drives paragraph segmentation itself we only need a single score per
call, which keeps the detector interface provider-agnostic.
"""

from __future__ import annotations

import os

import requests

from ..models import DetectionResult, Label
from .base import Detector

API_URL = "https://api.gptzero.me/v2/predict/text"


class GPTZeroDetector(Detector):
    name = "gptzero"

    def __init__(self, api_key: str | None = None, *, timeout: float = 30.0):
        self.api_key = api_key or os.getenv("GPTZERO_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GPTZero requires an API key. Set GPTZERO_API_KEY or pass "
                "api_key=. Get one at https://app.gptzero.me/app/api"
            )
        self.timeout = timeout

    def detect(self, text: str) -> DetectionResult:
        resp = requests.post(
            API_URL,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
            },
            json={"document": text},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        return self._parse(payload)

    @staticmethod
    def _parse(payload: dict) -> DetectionResult:
        documents = payload.get("documents") or []
        if not documents:
            raise ValueError(f"Unexpected GPTZero response: {payload!r}")
        doc = documents[0]

        probs = doc.get("class_probabilities") or {}
        ai_prob = probs.get("ai")
        if ai_prob is None:
            # Older payload shape.
            ai_prob = doc.get("completely_generated_prob")
        if ai_prob is None:
            ai_prob = doc.get("average_generated_prob", 0.0)

        result = DetectionResult.from_ai_probability(
            ai_prob,
            provider="gptzero",
            confidence=doc.get("confidence_category", "unknown"),
            raw=doc,
        )
        # Honour GPTZero's own classification when available.
        classification = doc.get("document_classification")
        mapping = {
            "AI_ONLY": Label.AI,
            "MIXED": Label.MIXED,
            "HUMAN_ONLY": Label.HUMAN,
        }
        if classification in mapping:
            result.label = mapping[classification]
        return result
