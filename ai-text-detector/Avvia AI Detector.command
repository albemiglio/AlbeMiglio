#!/bin/bash
# Doppio click per avviare AI Text Detector e aprirlo in Safari.
# (macOS: se appare un avviso di sicurezza, tasto destro sul file > "Apri".)

cd "$(dirname "$0")" || exit 1

echo "============================================"
echo "   AI Text Detector - avvio in corso..."
echo "============================================"
echo

# 1) Trova Python 3
PY="$(command -v python3)"
if [ -z "$PY" ]; then
  echo "Python 3 non e' installato."
  osascript -e 'display dialog "Python 3 non e'\''installato.\n\nClicca OK: apriro'\'' la pagina per installarlo. Dopo l'\''installazione, riapri questo file." buttons {"OK"} with title "AI Text Detector"' >/dev/null 2>&1
  open "https://www.python.org/downloads/macos/"
  exit 1
fi

# 2) Ambiente virtuale + dipendenze (solo la prima volta)
if [ ! -d ".venv" ]; then
  echo "Prima configurazione: installo i componenti (un paio di minuti)..."
  "$PY" -m venv .venv || { echo "Errore creazione ambiente."; read -r; exit 1; }
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --quiet --upgrade pip >/dev/null 2>&1
python -m pip install --quiet -r requirements.txt || {
  echo "Errore installazione dipendenze (serve connessione a internet)."; read -r; exit 1;
}

# 3) Apri Safari sulla UI appena il server e' pronto
( sleep 7; open -a Safari "http://localhost:8501" ) &

echo
echo "Apro l'interfaccia in Safari..."
echo "Per CHIUDERE il programma: torna qui e premi Ctrl+C, o chiudi questa finestra."
echo

# 4) Avvia la UI (headless: apriamo noi Safari, non il browser di default)
exec python -m streamlit run app.py \
  --server.headless true \
  --server.port 8501 \
  --browser.gatherUsageStats false
