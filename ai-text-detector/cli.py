"""Command-line interface for the AI-text detector.

Examples:
    python cli.py sample/sample_mixed.txt
    python cli.py doc.docx --provider gptzero --json report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from aidetector import Analyzer, PROVIDERS  # noqa: E402
from aidetector.detectors import get_detector  # noqa: E402


def _bar(pct: float, width: int = 24) -> str:
    filled = int(round(pct / 100 * width))
    return "█" * filled + "░" * (width - filled)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Estimate AI-generated percentage per paragraph and total."
    )
    parser.add_argument("path", help="Path to a .txt or .docx document")
    parser.add_argument(
        "--provider", choices=PROVIDERS, default="heuristic",
        help="Detection backend (default: heuristic / offline demo)",
    )
    parser.add_argument("--api-key", default=None, help="API key for the provider")
    parser.add_argument(
        "--language", default="en",
        help="Document language hint, e.g. 'it' (used by winston/heuristic)",
    )
    parser.add_argument("--workers", type=int, default=4, help="Parallel requests")
    parser.add_argument("--json", metavar="FILE", help="Write a JSON report")
    parser.add_argument("--html", metavar="FILE", help="Write an HTML report")
    args = parser.parse_args(argv)

    try:
        detector = get_detector(
            args.provider, api_key=args.api_key, language=args.language
        )
    except ValueError as exc:
        parser.error(str(exc))

    analyzer = Analyzer(detector=detector, max_workers=args.workers)
    result = analyzer.analyze_file(args.path)

    print(f"\nDocument: {result.source}")
    print(f"Provider: {result.provider}")
    print("=" * 60)
    for pr in result.paragraphs:
        if pr.error:
            print(f"¶{pr.index + 1:>3}  ERROR: {pr.error}")
            continue
        pct = pr.ai_percentage or 0.0
        flag = "  (short)" if pr.word_count < 8 else ""
        print(f"¶{pr.index + 1:>3}  {_bar(pct)} {pct:5.1f}% AI{flag}")
    print("=" * 60)
    print(
        f"TOTAL  {_bar(result.total_ai_percentage)} "
        f"{result.total_ai_percentage:5.1f}% AI  "
        f"| verdict: {result.overall.label.value.upper()}"
    )

    if args.json:
        report = {
            "source": result.source,
            "provider": result.provider,
            "total_ai_percentage": result.total_ai_percentage,
            "verdict": result.overall.label.value,
            "paragraphs": [
                {
                    "index": p.index,
                    "ai_percentage": p.ai_percentage,
                    "word_count": p.word_count,
                    "error": p.error,
                    "text": p.text,
                }
                for p in result.paragraphs
            ],
        }
        Path(args.json).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nJSON report written to {args.json}")

    if args.html:
        from aidetector.report import write_html

        write_html(result, args.html)
        print(f"HTML report written to {args.html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
