# Arshad – Kozhikode school coverage report

Builds `../Arshad_Kozhikode_School_Report.pdf` and `.html` from the five source PDFs
(Arshad's visit log, Deepika's Kozhikode list, Kozhikode School Data, ICSE/CBSE list,
free-pass feedback).

```
pip install pymupdf rapidfuzz reportlab
python3 parse_sources.py <folder-with-the-5-pdfs> sources.json   # PDF tables -> JSON
python3 build.py sources.json model.json                         # match + classify
python3 render_pdf.py model.json ../Arshad_Kozhikode_School_Report.pdf
python3 render_html.py model.json ../Arshad_Kozhikode_School_Report.html
```

- `mapping.py` – hand-verified school matches, place → area table, route localities for
  Elathur / Kunnamangalam, CBSE/ICSE area assignment, free-pass feedback matches.
- `build.py` – joins everything; confirmation-probability rules are in `classify()`.
- `tables.py` – the report sheets shared by both renderers.
