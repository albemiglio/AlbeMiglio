"""Loading and paragraph segmentation for .txt and .docx documents."""

from __future__ import annotations

import re
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


def load_document(path: str | Path) -> str:
    """Load a .txt or .docx file and return its raw text."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".txt" or suffix in {".md", ".text"}:
        return read_txt(path)
    if suffix == ".docx":
        return read_docx(path)
    raise ValueError(
        f"Unsupported file type '{suffix}'. Supported: .txt, .docx"
    )


def load_paragraphs(path: str | Path) -> list[str]:
    return split_paragraphs(load_document(path))
