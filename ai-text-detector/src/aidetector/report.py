"""Standalone HTML report generation for a :class:`DocumentResult`."""

from __future__ import annotations

import html
from datetime import datetime

from .models import DocumentResult, ParagraphResult


def _color(ai_pct: float) -> str:
    ratio = max(0.0, min(1.0, ai_pct / 100))
    red = int(198 * ratio + 46 * (1 - ratio))
    green = int(40 * ratio + 125 * (1 - ratio))
    return f"rgb({red}, {green}, 40)"


def _bg(ai_pct: float) -> str:
    ratio = max(0.0, min(1.0, ai_pct / 100))
    red = int(198 * ratio + 46 * (1 - ratio))
    green = int(40 * ratio + 125 * (1 - ratio))
    return f"rgba({red}, {green}, 40, 0.16)"


def _paragraph_html(pr: ParagraphResult) -> str:
    if pr.error:
        return (
            f"<div class='para err'><b>¶{pr.index + 1}</b> — ⚠️ "
            f"{html.escape(pr.error)}<p>{html.escape(pr.text[:400])}</p></div>"
        )
    pct = pr.ai_percentage or 0.0
    short = " <span class='tag'>short — excluded from total</span>" if pr.word_count < 8 else ""
    return (
        f"<div class='para' style='border-left-color:{_color(pct)};"
        f"background:{_bg(pct)}' id='p{pr.index + 1}'>"
        f"<div class='meta'><b>¶{pr.index + 1}</b> "
        f"<span class='pct' style='color:{_color(pct)}'>{pct:.1f}% AI</span> "
        f"<span class='wc'>· {pr.word_count} parole</span>{short}</div>"
        f"<p>{html.escape(pr.text)}</p></div>"
    )


def render_html(result: DocumentResult, *, title: str | None = None) -> str:
    total = result.total_ai_percentage
    title = title or f"AI Detection Report — {html.escape(result.source)}"
    label = result.overall.label.value.upper()

    analysed = result.analysed_paragraphs
    top = sorted(analysed, key=lambda p: -(p.ai_percentage or 0))[:10]
    top_rows = "".join(
        f"<li><a href='#p{p.index + 1}'>¶{p.index + 1}</a> — "
        f"<b style='color:{_color(p.ai_percentage or 0)}'>"
        f"{p.ai_percentage:.1f}%</b> "
        f"<span class='wc'>({html.escape(p.text[:80])}…)</span></li>"
        for p in top
    )

    paragraphs_html = "".join(_paragraph_html(p) for p in result.paragraphs)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
 body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
   max-width:900px;margin:0 auto;padding:24px;color:#1a1a1a;line-height:1.5}}
 h1{{font-size:1.5rem}} h2{{font-size:1.1rem;margin-top:2rem}}
 .summary{{display:flex;gap:24px;flex-wrap:wrap;margin:16px 0;padding:18px;
   border:1px solid #e0e0e0;border-radius:10px;background:#fafafa}}
 .metric{{text-align:center}} .metric .v{{font-size:2rem;font-weight:700}}
 .metric .l{{font-size:.8rem;color:#666;text-transform:uppercase}}
 .bar{{height:14px;border-radius:7px;background:#eee;overflow:hidden;margin:8px 0}}
 .bar>div{{height:100%}}
 .verdict{{font-weight:700;padding:2px 10px;border-radius:6px;color:#fff}}
 .para{{border-left:5px solid #ccc;padding:8px 14px;margin:10px 0;border-radius:5px}}
 .para p{{margin:6px 0 0}} .para.err{{background:#f3f3f3;border-left-color:#999}}
 .meta .pct{{font-weight:700}} .wc{{color:#888;font-size:.85rem}}
 .tag{{background:#ffe;border:1px solid #dd0;border-radius:4px;padding:0 6px;
   font-size:.75rem;color:#777}}
 .note{{background:#fff8e1;border:1px solid #ffe082;border-radius:8px;
   padding:12px 16px;font-size:.9rem;margin:16px 0}}
 ol a{{text-decoration:none}}
</style></head><body>
<h1>🔎 AI Detection Report</h1>
<p><b>Documento:</b> {html.escape(result.source)}<br>
   <b>Provider:</b> {html.escape(result.provider)} ·
   <b>Generato:</b> {ts}</p>

<div class="summary">
  <div class="metric"><div class="v" style="color:{_color(total)}">{total:.1f}%</div>
    <div class="l">AI</div></div>
  <div class="metric"><div class="v">{result.total_human_percentage:.1f}%</div>
    <div class="l">Human</div></div>
  <div class="metric"><div class="v">{len(analysed)}/{len(result.paragraphs)}</div>
    <div class="l">Paragrafi</div></div>
  <div class="metric"><div class="v">
    <span class="verdict" style="background:{_color(total)}">{label}</span></div>
    <div class="l">Verdetto</div></div>
</div>
<div class="bar"><div style="width:{min(100, total):.1f}%;background:{_color(total)}"></div></div>

<div class="note">⚠️ I detector di testo AI producono falsi positivi e negativi
 (in particolare su testi non in inglese). Usa questi valori come indicatori,
 non come prova.</div>

<h2>Paragrafi a più alta probabilità AI</h2>
<ol>{top_rows}</ol>

<h2>Analisi per paragrafo</h2>
{paragraphs_html}
</body></html>"""


def write_html(result: DocumentResult, path: str, *, title: str | None = None) -> None:
    from pathlib import Path

    Path(path).write_text(render_html(result, title=title), encoding="utf-8")
