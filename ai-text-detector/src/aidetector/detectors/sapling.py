"""Sapling AI-content detector.

Docs: https://sapling.ai/docs/api/detector

We POST to ``/api/v1/aidetect`` with the API key in the JSON body. The response
contains a document-level ``score`` (probability in [0, 1] that the text is AI
generated) plus optional ``sentence_scores``.
"""

from __future__ import annotations

import os

import requests

from ..models import DetectionResult
from .base import Detector

API_URL = "https://api.sapling.ai/api/v1/aidetect"


class SaplingDetector(Detector):
    name = "sapling"

    def __init__(self, api_key: str | None = None, *, timeout: float = 30.0):
        self.api_key = api_key or os.getenv("SAPLING_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Sapling requires an API key. Set SAPLING_API_KEY or pass "
                "api_key=. Get one at https://sapling.ai/"
            )
        self.timeout = timeout

    def detect(self, text: str) -> DetectionResult:
        resp = requests.post(
            API_URL,
            json={"key": self.api_key, "text": text},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        score = payload.get("score")
        if score is None:
            raise ValueError(f"Unexpected Sapling response: {payload!r}")
        return DetectionResult.from_ai_probability(
            score, provider="sapling", raw=payload
        )
