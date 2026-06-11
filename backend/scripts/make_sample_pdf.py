"""Generate a small synthetic annual-report PDF for end-to-end pipeline testing.

Usage: python scripts/make_sample_pdf.py [output.pdf]

The PDF contains a key-figures table and narrative key-figure sentences in the
formats real annual reports use, so it exercises both the table extractor and
the rule-based text extractor. Upload it via POST /api/documents/upload (or
the dashboard's Documents page) to watch the full extract → derive → validate
flow run on a real file.
"""
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

STYLES = getSampleStyleSheet()


def build(path: str) -> None:
    doc = SimpleDocTemplate(path, pagesize=A4)
    story = [
        Paragraph("Pinnacle Trust Bank — Integrated Annual Report FY2025", STYLES["Title"]),
        Spacer(1, 0.5 * cm),
        Paragraph(
            "During the year, the Bank delivered strong performance. "
            "Net Interest Income of 18,420 crore grew on the back of healthy advances. "
            "Profit After Tax stood at 7,650 crore. "
            "Net Interest Margin was 3.95% for the year. "
            "The Provision Coverage Ratio improved to 77.2%. "
            "Return on Equity was 15.1% and Return on Assets stood at 1.42%.",
            STYLES["BodyText"]),
        Spacer(1, 0.6 * cm),
        Paragraph("Key Performance Indicators", STYLES["Heading2"]),
    ]
    table = Table([
        ["Particulars", "FY2024", "FY2025"],
        ["Total Income", "41,200", "46,800"],
        ["Operating Expenses", "11,900", "13,100"],
        ["Other Income", "7,400", "8,300"],
        ["Total Assets", "5,42,000", "6,18,000"],
        ["Net Worth", "47,500", "53,400"],
        ["Gross Advances", "3,61,000", "4,12,000"],
        ["Total Deposits", "4,28,000", "4,86,000"],
        ["CASA Deposits", "1,79,000", "1,98,000"],
        ["Gross NPA", "5,900", "5,400"],
        ["Net NPA", "1,520", "1,310"],
        ["CET1 Ratio", "13.9%", "14.2%"],
        ["Tier 1 Capital Ratio", "14.6%", "14.9%"],
        ["Capital Adequacy Ratio", "16.8%", "17.1%"],
        ["Liquidity Coverage Ratio", "128%", "131%"],
        ["Number of Branches", "3,150", "3,275"],
        ["Number of Employees", "52,400", "55,800"],
    ])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A120B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#C7A56A")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story.append(table)
    doc.build(story)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sample_annual_report.pdf"
    build(out)
    print(f"Wrote {out}")
