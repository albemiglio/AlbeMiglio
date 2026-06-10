"""Detector registry and factory."""

from __future__ import annotations

from .base import Detector
from .gptzero import GPTZeroDetector
from .heuristic import HeuristicDetector
from .sapling import SaplingDetector

PROVIDERS = ("gptzero", "sapling", "heuristic")


def get_detector(provider: str, api_key: str | None = None, **kwargs) -> Detector:
    """Instantiate a detector by provider name."""
    provider = (provider or "heuristic").lower()
    if provider == "gptzero":
        return GPTZeroDetector(api_key=api_key, **kwargs)
    if provider == "sapling":
        return SaplingDetector(api_key=api_key, **kwargs)
    if provider == "heuristic":
        return HeuristicDetector()
    raise ValueError(
        f"Unknown provider '{provider}'. Choose one of: {', '.join(PROVIDERS)}"
    )


__all__ = [
    "Detector",
    "GPTZeroDetector",
    "SaplingDetector",
    "HeuristicDetector",
    "get_detector",
    "PROVIDERS",
]
