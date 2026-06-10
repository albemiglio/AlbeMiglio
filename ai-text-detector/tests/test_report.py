import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aidetector import Analyzer  # noqa: E402
from aidetector.report import render_html  # noqa: E402


def test_html_report_contains_summary_and_paragraphs():
    text = (
        "This is a genuinely human paragraph with varied natural wording here.\n\n"
        "Moreover, furthermore, in conclusion it is important to note the realm "
        "and the tapestry of the comprehensive framework underscores the synergy."
    )
    result = Analyzer(provider="heuristic").analyze_text(text, source="t.txt")
    out = render_html(result)
    assert "AI Detection Report" in out
    assert "t.txt" in out
    assert "% AI" in out
    # One paragraph anchor per paragraph.
    assert out.count("class='para'") == len(result.paragraphs)


def test_heuristic_italian_boilerplate_raises_score():
    it = Analyzer(provider="heuristic", language="it").analyze_text(
        "Inoltre, tuttavia, in conclusione è importante notare che il panorama "
        "risulta fondamentale e cruciale in tal senso, di conseguenza l'ambito."
    )
    en = Analyzer(provider="heuristic", language="en").analyze_text(
        "Inoltre, tuttavia, in conclusione è importante notare che il panorama "
        "risulta fondamentale e cruciale in tal senso, di conseguenza l'ambito."
    )
    # Italian boilerplate is only recognised under the 'it' language.
    assert it.total_ai_percentage >= en.total_ai_percentage
