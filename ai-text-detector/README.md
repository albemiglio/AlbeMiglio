# 🔎 AI Text Detector

Stima la **percentuale di testo generato da AI** per **ogni paragrafo** e per
**l'intero documento** (`.txt` / `.docx` / `.pdf`). Web UI in Streamlit + CLI,
con backend di detection intercambiabili (API esterne o fallback offline).

```
¶  1  █████████░░░░░░░░░░░░░░░  36.4% AI
¶  2  █████████████░░░░░░░░░░░  52.9% AI
¶  3  █████░░░░░░░░░░░░░░░░░░░  20.0% AI
¶  4  ████████████░░░░░░░░░░░░  50.6% AI
============================================================
TOTAL  ██████████░░░░░░░░░░░░░░  40.2% AI  | verdict: MIXED
```

---

## Come funziona la detection (le tecniche)

I detector di testo AI vs human si basano su alcune famiglie di segnali:

| Tecnica | Idea | Note |
|---|---|---|
| **Perplexity** | Quanto è "prevedibile" ogni token dato il contesto. Gli LLM scelgono token statisticamente probabili → **perplexity bassa**; gli umani sono più sorprendenti. | Segnale storico (GPTZero). Da solo è aggirabile. |
| **Burstiness** | Quanto *varia* la perplexity/complessità tra le frasi. Gli umani hanno picchi e cali; l'AI è più piatta e uniforme. | Usato insieme alla perplexity. |
| **Probability curvature (DetectGPT)** | Il testo AI tende a stare in un massimo locale della log-prob del modello: si perturba il testo e si confrontano le probabilità. | ICML 2023, zero-shot, costoso. |
| **Classificatori supervisionati** | Modelli (transformer fine-tuned) addestrati su corpus human vs AI. | Sapling, Originality.ai, Pangram, GPTZero (modelli recenti). Migliore accuratezza pratica. |
| **Stilometria** | Diversità lessicale, lunghezza frasi, densità di connettivi/boilerplate ("moreover", "in conclusion"...). | Debole da sola, utile come feature. |

**Limiti (2025):** i modelli fine-tuned producono testo con perplexity simile
all'umano; il paraphrasing/"humanizer" abbatte i segnali; testi corti sono
inaffidabili. Nessun detector è affidabile al 100% — vanno usati come
indicatori, non come prova. L'accuratezza cresce con la lunghezza del testo
(documento > paragrafo > frase).

Questo strumento adotta l'approccio **classificatore via API esterna** (scelta
di progetto), mappando lo score sul **paragrafo** e aggregando il totale.

---

## Architettura

```
src/aidetector/
  document.py        # carica .txt/.docx/.pdf → paragrafi
                     #   .pdf: ricostruzione paragrafi via layout + gap verticali
  detectors/
    base.py          # interfaccia Detector.detect(text) -> DetectionResult
    gptzero.py       # API GPTZero  (POST /v2/predict/text)
    sapling.py       # API Sapling  (POST /api/v1/aidetect)
    heuristic.py     # fallback offline (burstiness + stilometria), no API key
  analyzer.py        # orchestrazione: paragrafi → detect (parallelo) → totale
  models.py          # DetectionResult / ParagraphResult / DocumentResult
app.py               # web UI Streamlit
cli.py               # interfaccia a riga di comando
```

Il **totale del documento** è la media degli score dei paragrafi **pesata sul
numero di parole**; i paragrafi troppo corti (< 8 parole) vengono mostrati ma
esclusi dal totale per evitare rumore. L'interfaccia `Detector` è minimale
(`detect(text) -> ai_probability`), così qualsiasi provider — API o locale —
si integra allo stesso modo.

---

## Installazione

```bash
pip install -r requirements.txt        # requests, python-docx, pdfminer.six, streamlit, pytest
cp .env.example .env                    # inserisci le API key che vuoi usare
```

## Uso — Web UI

```bash
streamlit run app.py
```

Carica un `.txt`/`.docx` o incolla del testo, scegli il provider (e la API key),
e ottieni: percentuale totale, verdetto, breakdown per paragrafo con
evidenziazione colorata (verde→rosso) ed export JSON del report.

## Uso — CLI

```bash
# Demo offline (nessuna key):
python cli.py sample/sample_mixed.txt

# Con un provider reale:
python cli.py documento.docx --provider gptzero --api-key $GPTZERO_API_KEY
python cli.py documento.txt  --provider sapling --json report.json
```

## Uso — come libreria

```python
import sys; sys.path.insert(0, "src")
from aidetector import Analyzer

result = Analyzer(provider="gptzero", api_key="...").analyze_file("doc.docx")
print(result.total_ai_percentage)                 # totale documento
for p in result.paragraphs:
    print(p.index, p.ai_percentage, p.text[:60])  # per paragrafo
```

## Provider

| Provider | API key | Note |
|---|---|---|
| `winston` | `WINSTON_API_KEY` | **Multilingua, consigliato per l'italiano** (`--language it`). Score documento + frase. [Docs](https://docs.gowinston.ai/) |
| `gptzero` | `GPTZERO_API_KEY` | Score documento/paragrafo/frase. Tarato sull'inglese. [Docs](https://gptzero.stoplight.io/docs/gptzero-api) |
| `sapling` | `SAPLING_API_KEY` | Score documento + frase. [Docs](https://sapling.ai/ai-detection-apis) |
| `heuristic` | — | **Offline demo** (burstiness + stilometria, language-aware EN/IT). Non affidabile, serve a far girare e testare lo strumento senza key. |

> **Nota su Turnitin:** Turnitin **non** è utilizzabile qui — è un servizio
> proprietario venduto solo alle istituzioni (integrato negli LMS), senza API
> pubblica per i singoli e con algoritmo chiuso. Non è replicabile "esattamente".
> Per l'italiano l'alternativa più vicina con API è **Winston**.

Aggiungere un provider = una sottoclasse di `Detector` che implementa
`detect(text) -> DetectionResult` e una voce nella factory in
`detectors/__init__.py`.

## Test

```bash
python -m pytest -q       # 12 test: parsing, aggregazione, parsing risposte API
```

---

⚠️ **Disclaimer:** i detector di testo AI producono falsi positivi e falsi
negativi. Non usare gli output come unica base per decisioni accademiche o
disciplinari.
