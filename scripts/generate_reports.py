"""Build every report from the PDFs in ../source_data.

    pip install pdfplumber rapidfuzz reportlab openpyxl
    python scripts/generate_reports.py
"""
import os

from make_html import build_html
from make_pdf import build_areawise, build_consolidated
from make_xlsx import build_xlsx
from report_tables import make_tables

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

if __name__ == "__main__":
    T = make_tables()
    build_consolidated(T, os.path.join(OUT, "Aslam_Consolidated_Report.pdf"))
    build_areawise(T, os.path.join(OUT, "Aslam_Areawise_Report.pdf"))
    build_html(T, os.path.join(OUT, "Aslam_School_Report.html"))
    build_xlsx(T, os.path.join(OUT, "Aslam_School_Report.xlsx"))
    print("Reports written to", os.path.abspath(OUT))
