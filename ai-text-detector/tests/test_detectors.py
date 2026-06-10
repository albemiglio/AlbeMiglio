import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aidetector.detectors import get_detector  # noqa: E402
from aidetector.detectors.gptzero import GPTZeroDetector  # noqa: E402
from aidetector.models import Label  # noqa: E402


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        get_detector("does-not-exist")


def test_api_providers_require_key_at_class_level(monkeypatch):
    # The detector classes still demand a key when constructed directly.
    from aidetector.detectors.gptzero import GPTZeroDetector
    from aidetector.detectors.sapling import SaplingDetector

    monkeypatch.delenv("GPTZERO_API_KEY", raising=False)
    monkeypatch.delenv("SAPLING_API_KEY", raising=False)
    with pytest.raises(ValueError):
        GPTZeroDetector(api_key=None)
    with pytest.raises(ValueError):
        SaplingDetector(api_key=None)


def test_factory_uses_hardcoded_key_fallback(monkeypatch):
    # The packaged factory falls back to the hard-coded key, so no env needed.
    from aidetector.config import HARDCODED_API_KEY

    monkeypatch.delenv("WINSTON_API_KEY", raising=False)
    det = get_detector("winston", language="it")
    assert det.api_key == HARDCODED_API_KEY
    assert det.language == "it"


def test_gptzero_response_parsing():
    payload = {
        "documents": [
            {
                "document_classification": "MIXED",
                "confidence_category": "high",
                "class_probabilities": {"human": 0.3, "ai": 0.6, "mixed": 0.1},
            }
        ]
    }
    result = GPTZeroDetector._parse(payload)
    assert result.ai_probability == 0.6
    assert result.label == Label.MIXED
    assert result.confidence == "high"


def test_gptzero_fallback_to_completely_generated_prob():
    payload = {"documents": [{"completely_generated_prob": 0.8}]}
    result = GPTZeroDetector._parse(payload)
    assert result.ai_probability == 0.8
    assert result.label == Label.AI


def test_winston_human_score_inverted_to_ai_probability():
    from aidetector.detectors.winston import WinstonDetector

    # Winston: score is a HUMAN score (100 = human, 0 = AI).
    assert WinstonDetector._parse({"score": 90}).ai_probability == 0.1
    assert WinstonDetector._parse({"score": 10}).ai_probability == 0.9
    res = WinstonDetector._parse({"score": 10})
    assert res.label == Label.AI
    assert res.provider == "winston"


def test_winston_requires_key_at_class_level(monkeypatch):
    from aidetector.detectors.winston import WinstonDetector

    monkeypatch.delenv("WINSTON_API_KEY", raising=False)
    with pytest.raises(ValueError):
        WinstonDetector(api_key=None)
