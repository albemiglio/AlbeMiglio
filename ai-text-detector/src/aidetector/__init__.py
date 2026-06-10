"""aidetector - per-paragraph and document-level AI-text detection."""

from __future__ import annotations

from .analyzer import Analyzer
from .detectors import PROVIDERS, get_detector
from .models import DetectionResult, DocumentResult, Label, ParagraphResult

__version__ = "0.1.0"

__all__ = [
    "Analyzer",
    "get_detector",
    "PROVIDERS",
    "DetectionResult",
    "DocumentResult",
    "ParagraphResult",
    "Label",
    "__version__",
]
