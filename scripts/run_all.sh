#!/bin/sh
# Usage: scripts/run_all.sh <folder with the five source PDFs> <work dir>
set -e
U="$1"; W="$2"; D="$(cd "$(dirname "$0")" && pwd)"; ROOT="$D/.."
python3 "$D/parse_musthafa.py" "$U"/*Musthafa.pdf "$W/musthafa.json"
python3 "$D/parse_sources.py" "$U" "$W/sources.json"
python3 "$D/build.py" "$W/musthafa.json" "$W/sources.json" "$W/report.json"
python3 "$D/make_report.py" "$W/report.json" "$ROOT/Musthafa_Area_Coverage_Report.html"
CHROME="${CHROME:-/opt/pw-browsers/chromium-1194/chrome-linux/chrome}"
"$CHROME" --headless --no-sandbox --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$ROOT/Musthafa_Area_Coverage_Report.pdf" "$ROOT/Musthafa_Area_Coverage_Report.html" 2>/dev/null
