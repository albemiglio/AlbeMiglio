import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aidetector.document import split_paragraphs, window_segments  # noqa: E402


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


def test_window_segments_pack_to_target_without_splitting_sentences():
    # 10 sentences of 10 words each = 100 words; target 30 -> ~4 sentences/seg.
    sentence = " ".join(["word"] * 9) + " end."
    paragraphs = [" ".join([sentence] * 10)]
    segs = window_segments(paragraphs, target_words=30)
    assert len(segs) >= 3
    # Every segment is made of whole sentences (ends with the sentence period).
    for s in segs:
        assert s.strip().endswith("end.")
    # No segment greatly exceeds the target (allowing one sentence overshoot).
    import re
    for s in segs:
        assert len(re.findall(r"\w+", s)) <= 30 + 10
