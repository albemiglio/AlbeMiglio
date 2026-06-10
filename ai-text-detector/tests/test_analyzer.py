import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aidetector import Analyzer  # noqa: E402
from aidetector.detectors.base import Detector  # noqa: E402
from aidetector.models import DetectionResult  # noqa: E402


class StubDetector(Detector):
    """Returns a fixed AI probability based on the presence of a keyword."""

    name = "stub"

    def detect(self, text: str) -> DetectionResult:
        prob = 0.9 if "robot" in text.lower() else 0.1
        return DetectionResult.from_ai_probability(prob, provider="stub")


def test_per_paragraph_and_weighted_total():
    text = (
        "This is a perfectly human paragraph with plenty of natural words here.\n\n"
        "robot robot robot robot robot robot robot robot robot robot generated."
    )
    result = Analyzer(detector=StubDetector()).analyze_text(text)

    assert len(result.paragraphs) == 2
    assert result.paragraphs[0].ai_percentage == 10.0
    assert result.paragraphs[1].ai_percentage == 90.0
    # Both paragraphs are long enough; total is word-weighted, between the two.
    assert 10.0 < result.total_ai_percentage < 90.0


def test_short_paragraphs_excluded_from_total():
    text = "robot.\n\nThis is a clearly human and sufficiently long paragraph indeed here."
    result = Analyzer(detector=StubDetector()).analyze_text(text)
    # The short 'robot.' paragraph (1 word) must not drag the total to AI.
    assert result.total_ai_percentage == 10.0


def test_errors_are_captured_per_paragraph():
    class Boom(Detector):
        name = "boom"

        def detect(self, text):
            raise RuntimeError("api down")

    result = Analyzer(detector=Boom()).analyze_text("Some text paragraph here now.")
    assert result.paragraphs[0].error is not None
    assert "api down" in result.paragraphs[0].error


def test_heuristic_provider_runs_offline():
    result = Analyzer(provider="heuristic").analyze_text(
        "Moreover, furthermore, in conclusion it is important to note the realm. "
        "Additionally the tapestry of the framework underscores the synergy."
    )
    assert 0.0 <= result.total_ai_percentage <= 100.0
