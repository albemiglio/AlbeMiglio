"""Detector registry and factory."""

from __future__ import annotations

from .base import Detector
from .gptzero import GPTZeroDetector
from .heuristic import HeuristicDetector
from .sapling import SaplingDetector
from .winston import WinstonDetector

PROVIDERS = ("gptzero", "sapling", "winston", "heuristic")

# Providers that accept a `language` hint (e.g. "it" for Italian).
_LANGUAGE_AWARE = {"winston", "heuristic"}


def get_detector(
    provider: str,
    api_key: str | None = None,
    *,
    language: str = "en",
    **kwargs,
) -> Detector:
    """Instantiate a detector by provider name."""
    provider = (provider or "heuristic").lower()
    if provider in _LANGUAGE_AWARE:
        kwargs.setdefault("language", language)
    if provider == "gptzero":
        return GPTZeroDetector(api_key=api_key, **kwargs)
    if provider == "sapling":
        return SaplingDetector(api_key=api_key, **kwargs)
    if provider == "winston":
        return WinstonDetector(api_key=api_key, **kwargs)
    if provider == "heuristic":
        return HeuristicDetector(**kwargs)
    raise ValueError(
        f"Unknown provider '{provider}'. Choose one of: {', '.join(PROVIDERS)}"
    )


__all__ = [
    "Detector",
    "GPTZeroDetector",
    "SaplingDetector",
    "WinstonDetector",
    "HeuristicDetector",
    "get_detector",
    "PROVIDERS",
]
