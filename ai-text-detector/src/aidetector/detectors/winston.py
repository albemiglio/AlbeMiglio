"""Winston AI detector — multilingual, including Italian.

Docs: https://docs.gowinston.ai/api-reference/v2/ai-content-detection/post

Winston returns a *human score* in [0, 100] where 100 means "very likely
human" and 0 means "very likely AI". We convert it to an AI probability with
``ai = (100 - score) / 100``. Winston supports Italian (``language="it"``),
which is why it is the recommended backend for non-English documents.
"""

from __future__ import annotations

import os

import requests

from ..models import DetectionResult
from .base import Detector

API_URL = "https://api.gowinston.ai/v2/ai-content-detection"

# Winston needs a minimum amount of text per request.
MIN_CHARS = 300


class WinstonDetector(Detector):
    name = "winston"

    def __init__(
        self,
        api_key: str | None = None,
        *,
        language: str = "en",
        timeout: float = 60.0,
    ):
        self.api_key = api_key or os.getenv("WINSTON_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Winston requires an API key. Set WINSTON_API_KEY or pass "
                "api_key=. Get one at https://gowinston.ai/"
            )
        self.language = language
        self.timeout = timeout

    def detect(self, text: str) -> DetectionResult:
        resp = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "text": text,
                "language": self.language,
                "sentences": False,
                "version": "latest",
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        payload = resp.json()
        return self._parse(payload)

    @staticmethod
    def _parse(payload: dict) -> DetectionResult:
        human_score = payload.get("score")
        if human_score is None:
            raise ValueError(f"Unexpected Winston response: {payload!r}")
        ai_probability = (100.0 - float(human_score)) / 100.0
        return DetectionResult.from_ai_probability(
            ai_probability,
            provider="winston",
            confidence="medium",
            raw={
                "human_score": human_score,
                "readability_score": payload.get("readability_score"),
                "credits_used": payload.get("credits_used"),
                "credits_remaining": payload.get("credits_remaining"),
                "language": payload.get("language"),
                "attack_detected": payload.get("attack_detected"),
            },
        )
