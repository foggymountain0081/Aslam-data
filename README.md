# Aslam – School Visit Verification (Malappuram)

Aslam's school-visit log checked against Deepika's Malappuram list, the State-syllabus census,
the CBSE/ICSE directory and the free stay-pass feedback register.

## Reports

| File | What it contains |
|---|---|
| `Aslam_Consolidated_Report.pdf` | Area summary, then one section per sheet: second-visit schedule, schools visited, pending first visits (with mobile / without mobile), Deepika's mobile numbers, free-pass feedback |
| `Aslam_Areawise_Report.pdf` | The same data, grouped by area (Tanur, Tirur, Tirurangadi, Tavanur, Vallikunnu, Kottakkal, Ponnani, Vengara) |
| `Aslam_School_Report.html` | Interactive version: tabs for every sheet, area filter, search box, area-wise view |
| `Aslam_School_Report.xlsx` | Every sheet as an Excel tab, plus one tab per area |

## Regenerating

The inputs are in `source_data/`. To rebuild every report:

```
pip install pdfplumber rapidfuzz reportlab openpyxl
python scripts/generate_reports.py
```

`scripts/load_data.py` parses the PDFs, `scripts/matching.py` handles name/place matching,
`scripts/build_data.py` cross-verifies the sources, and `scripts/report_tables.py` builds the sheets
used by `make_pdf.py`, `make_html.py` and `make_xlsx.py`. Place names the automatic mapping gets wrong
can be corrected in `PLACE_OVERRIDES` in `build_data.py`.
