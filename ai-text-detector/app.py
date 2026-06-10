"""Streamlit web UI for the AI-text detector.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import html
import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from aidetector import Analyzer, PROVIDERS  # noqa: E402
from aidetector.detectors import get_detector  # noqa: E402
from aidetector.models import Label  # noqa: E402

st.set_page_config(page_title="AI Text Detector", page_icon="🔎", layout="wide")

LABEL_COLOR = {
    Label.HUMAN: "#2e7d32",   # green
    Label.MIXED: "#f9a825",   # amber
    Label.AI: "#c62828",      # red
}


def color_for(ai_pct: float) -> str:
    """Continuous green→red colour for an AI percentage [0, 100]."""
    ratio = max(0.0, min(1.0, ai_pct / 100))
    red = int(198 * ratio + 46 * (1 - ratio))
    green = int(40 * ratio + 125 * (1 - ratio))
    return f"rgba({red}, {green}, 40, 0.18)"


def border_for(ai_pct: float) -> str:
    ratio = max(0.0, min(1.0, ai_pct / 100))
    red = int(198 * ratio + 46 * (1 - ratio))
    green = int(40 * ratio + 125 * (1 - ratio))
    return f"rgb({red}, {green}, 40)"


# ---------------------------------------------------------------- sidebar
st.sidebar.title("⚙️ Configuration")
provider = st.sidebar.selectbox(
    "Detection provider",
    PROVIDERS,
    index=PROVIDERS.index("heuristic"),
    help="GPTZero/Sapling need an API key. 'heuristic' runs offline (demo).",
)

env_key = {
    "gptzero": "GPTZERO_API_KEY",
    "sapling": "SAPLING_API_KEY",
    "winston": "WINSTON_API_KEY",
}.get(provider)

api_key = None
if env_key:
    api_key = st.sidebar.text_input(
        f"{provider} API key",
        value=os.getenv(env_key, ""),
        type="password",
        help=f"Or set the {env_key} environment variable.",
    )

language = st.sidebar.selectbox(
    "Document language",
    ["en", "it", "fr", "es", "de", "pt", "nl", "pl", "ro", "zh"],
    index=0,
    help="Used by winston (and the heuristic). Use 'it' for Italian.",
)

max_workers = st.sidebar.slider("Parallel requests", 1, 8, 4)

st.sidebar.markdown("---")
st.sidebar.caption(
    "The **heuristic** provider is an offline demo based on burstiness and "
    "stylometry — not a reliable detector. Use GPTZero or Sapling for real "
    "results."
)

# ---------------------------------------------------------------- main
st.title("🔎 AI Text Detector")
st.write(
    "Upload a **.txt**, **.docx** or **.pdf** document (or paste text) to "
    "estimate the AI-generated percentage for **each paragraph** and for the "
    "**whole document**."
)

tab_file, tab_text = st.tabs(["📄 Upload file", "✍️ Paste text"])

text_input = None
uploaded = None
with tab_file:
    uploaded = st.file_uploader(
        "Choose a document", type=["txt", "docx", "pdf", "md"]
    )
with tab_text:
    text_input = st.text_area("Paste your text here", height=240)

run = st.button("Analyse", type="primary")


def build_analyzer() -> Analyzer:
    detector = get_detector(
        provider, api_key=api_key or None, language=language
    )
    return Analyzer(detector=detector, max_workers=max_workers)


if run:
    try:
        analyzer = build_analyzer()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    with st.spinner("Analysing..."):
        if uploaded is not None:
            suffix = Path(uploaded.name).suffix or ".txt"
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix
            ) as tmp:
                tmp.write(uploaded.getbuffer())
                tmp_path = tmp.name
            try:
                result = analyzer.analyze_file(tmp_path)
                result.source = uploaded.name
            finally:
                os.unlink(tmp_path)
        elif text_input and text_input.strip():
            result = analyzer.analyze_text(text_input, source="pasted text")
        else:
            st.warning("Please upload a file or paste some text.")
            st.stop()

    # ---- document-level summary
    total = result.total_ai_percentage
    st.subheader(f"Overall result — {result.provider}")
    c1, c2, c3 = st.columns(3)
    c1.metric("AI generated", f"{total:.1f}%")
    c2.metric("Human", f"{result.total_human_percentage:.1f}%")
    c3.metric("Paragraphs", f"{len(result.analysed_paragraphs)}/"
                            f"{len(result.paragraphs)}")
    st.progress(min(1.0, total / 100))

    label = result.overall.label
    st.markdown(
        f"**Verdict:** "
        f"<span style='color:{LABEL_COLOR[label]};font-weight:700'>"
        f"{label.value.upper()}</span> "
        f"(confidence: {result.overall.confidence})",
        unsafe_allow_html=True,
    )

    if provider == "heuristic":
        st.info(
            "ℹ️ Using the offline heuristic demo. Scores are indicative only.",
            icon="ℹ️",
        )

    # ---- per-paragraph highlighted view
    st.subheader("Per-paragraph breakdown")
    for pr in result.paragraphs:
        if pr.error:
            st.markdown(
                f"<div style='border-left:4px solid #999;padding:6px 10px;"
                f"margin:6px 0;background:#f5f5f5'>"
                f"<b>¶{pr.index + 1}</b> — ⚠️ error: {html.escape(pr.error)}"
                f"<br>{html.escape(pr.text[:300])}</div>",
                unsafe_allow_html=True,
            )
            continue
        ai_pct = pr.ai_percentage or 0.0
        unreliable = pr.word_count < 8
        tag = " <i>(short — excluded from total)</i>" if unreliable else ""
        st.markdown(
            f"<div style='border-left:5px solid {border_for(ai_pct)};"
            f"background:{color_for(ai_pct)};padding:8px 12px;margin:6px 0;"
            f"border-radius:4px'>"
            f"<b>¶{pr.index + 1}</b> &nbsp; "
            f"<span style='font-weight:700'>{ai_pct:.1f}% AI</span> "
            f"<span style='opacity:.6'>· {pr.word_count} words</span>{tag}"
            f"<br>{html.escape(pr.text)}</div>",
            unsafe_allow_html=True,
        )

    # ---- export
    st.subheader("Export")
    import json

    export = {
        "source": result.source,
        "provider": result.provider,
        "total_ai_percentage": result.total_ai_percentage,
        "total_human_percentage": result.total_human_percentage,
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
    from aidetector.report import render_html

    col_json, col_html = st.columns(2)
    col_json.download_button(
        "⬇️ Download JSON report",
        data=json.dumps(export, ensure_ascii=False, indent=2),
        file_name="ai_detection_report.json",
        mime="application/json",
    )
    col_html.download_button(
        "⬇️ Download HTML report",
        data=render_html(result),
        file_name="ai_detection_report.html",
        mime="text/html",
    )
