import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aidetector.document import split_paragraphs  # noqa: E402


def test_split_on_blank_lines():
    text = "First paragraph here.\n\nSecond paragraph here.\n\n\nThird one."
    paras = split_paragraphs(text)
    assert paras == [
        "First paragraph here.",
        "Second paragraph here.",
        "Third one.",
    ]


def test_intra_paragraph_newlines_collapsed():
    text = "Line one\nstill same paragraph.\n\nNew paragraph."
    paras = split_paragraphs(text)
    assert paras[0] == "Line one still same paragraph."
    assert paras[1] == "New paragraph."


def test_one_paragraph_per_line_fallback():
    text = "Alpha line\nBeta line\nGamma line"
    paras = split_paragraphs(text)
    assert paras == ["Alpha line", "Beta line", "Gamma line"]


def test_empty():
    assert split_paragraphs("   \n  \n") == []
