"""Loading and paragraph segmentation for .txt, .docx and .pdf documents."""

from __future__ import annotations

import re
import statistics
from pathlib import Path


def _normalise(text: str) -> str:
    # Normalise newlines and strip trailing whitespace per line.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n"))


def split_paragraphs(text: str) -> list[str]:
    """Split raw text into logical paragraphs.

    Paragraphs are separated by one or more blank lines. If the text has no
    blank-line separators (e.g. one paragraph per line), we fall back to
    treating every non-empty line as a paragraph.
    """
    text = _normalise(text)
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) > 1:
        # Collapse intra-paragraph single newlines into spaces.
        return [re.sub(r"\s*\n\s*", " ", b).strip() for b in blocks]
    # No blank-line separation: one paragraph per non-empty line.
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    return lines or ([text.strip()] if text.strip() else [])


def read_txt(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def read_docx(path: str | Path) -> str:
    try:
        import docx  # python-docx
    except ImportError as exc:  # pragma: no cover - depends on env
        raise RuntimeError(
            "Reading .docx files requires 'python-docx'. Install it with "
            "`pip install python-docx`."
        ) from exc

    document = docx.Document(str(path))
    # Keep empty paragraphs so blank lines act as separators.
    return "\n".join(p.text for p in document.paragraphs)


def read_pdf_paragraphs(path: str | Path) -> list[str]:
    """Extract paragraphs from a PDF using layout analysis.

    PDF text has no notion of "paragraph": every visual line is a separate text
    box. We reconstruct paragraphs from the *vertical gaps* between consecutive
    lines — a gap noticeably larger than the typical line spacing (or a page
    change) marks a paragraph break. This is far more reliable than splitting on
    the newlines produced by plain text extraction.
    """
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextContainer
    except ImportError as exc:  # pragma: no cover - depends on env
        raise RuntimeError(
            "Reading .pdf files requires 'pdfminer.six'. Install it with "
            "`pip install pdfminer.six`."
        ) from exc

    # Collect lines in reading order: (page_index, y_top, y_bottom, text).
    lines: list[tuple[int, float, float, str]] = []
    for page_index, page in enumerate(extract_pages(str(path))):
        page_lines: list[tuple[float, float, str]] = []
        for element in page:
            if isinstance(element, LTTextContainer):
                text = re.sub(r"\s+", " ", element.get_text()).strip()
                if text:
                    _x0, y0, _x1, y1 = element.bbox
                    page_lines.append((y1, y0, text))
        page_lines.sort(key=lambda t: -t[0])  # top to bottom
        for y_top, y_bottom, text in page_lines:
            lines.append((page_index, y_top, y_bottom, text))

    if not lines:
        return []

    # Typical line spacing = median vertical gap between same-page lines.
    gaps = [
        upper[2] - lower[1]  # y_bottom of upper line - y_top of lower line
        for upper, lower in zip(lines, lines[1:])
        if upper[0] == lower[0]
    ]
    gaps = [g for g in gaps if g > -2]
    median_gap = statistics.median(gaps) if gaps else 0.0
    threshold = median_gap + max(2.0, median_gap * 0.8)

    paragraphs: list[str] = []
    current = lines[0][3]
    for upper, lower in zip(lines, lines[1:]):
        same_page = upper[0] == lower[0]
        gap = upper[2] - lower[1] if same_page else float("inf")
        if not same_page or gap > threshold:
            paragraphs.append(current.strip())
            current = lower[3]
        else:
            current = f"{current} {lower[3]}".strip()
    paragraphs.append(current.strip())
    return [p for p in paragraphs if p]


def load_document(path: str | Path) -> str:
    """Load a .txt or .docx file and return its raw text."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".txt" or suffix in {".md", ".text"}:
        return read_txt(path)
    if suffix == ".docx":
        return read_docx(path)
    if suffix == ".pdf":
        return "\n\n".join(read_pdf_paragraphs(path))
    raise ValueError(
        f"Unsupported file type '{suffix}'. Supported: .txt, .docx, .pdf"
    )


def load_paragraphs(path: str | Path) -> list[str]:
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        # PDF paragraphs come from layout analysis, not newline splitting.
        return read_pdf_paragraphs(path)
    return split_paragraphs(load_document(path))


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def window_segments(
    paragraphs: list[str], target_words: int = 300
) -> list[str]:
    """Re-segment text into contiguous ~``target_words``-word blocks.

    This mirrors how Turnitin scores submissions: instead of natural
    paragraphs it works on fixed-size segments (~300 words). We pack whole
    sentences (across paragraph boundaries) until a segment reaches the target,
    then start a new one — so sentences are never split mid-way.
    """
    sentences: list[str] = []
    for para in paragraphs:
        sentences.extend(_split_sentences(para))

    segments: list[str] = []
    current: list[str] = []
    count = 0
    for sentence in sentences:
        words = len(re.findall(r"\w+", sentence))
        if current and count + words > target_words:
            segments.append(" ".join(current))
            current, count = [], 0
        current.append(sentence)
        count += words
    if current:
        segments.append(" ".join(current))
    return segments
