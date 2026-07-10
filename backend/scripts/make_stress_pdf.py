"""Generate a stress-test annual report PDF replicating hostile real-world
patterns that trip naive extractors:

- movement-then-level phrasing ("improved by 25 bps to 3.85 per cent")
- "per cent" spelled out; "Rs." prefixes; Indian digit grouping
- multi-year tables where the CURRENT year is the last column
- section-header rows and blank cells inside tables
- ratio tables with the unit in the LABEL ("(%)"), not the cell
- prior-year figures adjacent to current-year figures in narrative

Usage: python scripts/make_stress_pdf.py [output.pdf]
Used by tests/test_stress_extraction.py as the extraction-quality gate.
"""
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

STYLES = getSampleStyleSheet()

# (kpi_code, expected canonical value) — the ground truth the test asserts
EXPECTED = {
    "nim": 3.85,
    "pat": 7650.0,
    "roa": 1.42,
    "roe": 15.1,
    "pcr": 77.2,
    "nii": 33410.0,
    "other_income": 8300.0,
    "total_income": 46800.0,
    "operating_expenses": 13100.0,
    "operating_profit": 28610.0,
    "total_assets": 618000.0,
    "net_worth": 53400.0,
    "gross_advances": 412000.0,
    "deposits": 486000.0,
    "casa_deposits": 198000.0,
    "gnpa": 5400.0,
    "nnpa": 1310.0,
    "gnpa_ratio": 1.31,
    "nnpa_ratio": 0.32,
    "cet1_ratio": 14.2,
    "tier1_ratio": 14.9,
    "crar": 17.1,
    "lcr": 131.0,
    "casa_ratio": 40.7,
    "branches": 3275.0,
    "employees": 55800.0,
}


def build(path: str) -> None:
    doc = SimpleDocTemplate(path, pagesize=A4)
    body = STYLES["BodyText"]

    story = [
        Paragraph("Pinnacle Trust Bank Limited", STYLES["Title"]),
        Paragraph("Integrated Annual Report 2024-25", STYLES["Heading2"]),
        Paragraph("For the year ended March 31, 2025", STYLES["Normal"]),
        Spacer(1, 0.8 * cm),
        Paragraph("Directors' Report — Financial Performance", STYLES["Heading2"]),
        Paragraph(
            "Your Bank delivered a resilient performance in a competitive deposit "
            "environment. Net Interest Margin improved by 25 bps to 3.85 per cent for "
            "the year, against 3.60 per cent in the previous year. Profit after tax "
            "rose to Rs. 7,650 crore, registering healthy growth. "
            "Return on Assets stood at 1.42 per cent and Return on Equity was 15.1% "
            "for the year. The Provision Coverage Ratio improved to 77.2%.", body),
        Paragraph(
            "The Bank's balance sheet remained granular. Total Deposits grew to "
            "4,86,000 crore, of which CASA Deposits were 1,98,000 crore — a CASA "
            "Ratio of 40.7 per cent. Gross Advances expanded to 4,12,000 crore. "
            "The Liquidity Coverage Ratio averaged 131% for the fourth quarter.", body),
        Spacer(1, 0.5 * cm),
        Paragraph("Financial Highlights", STYLES["Heading2"]),
        Paragraph("(₹ in crore, except ratios)", STYLES["Italic"]),
    ]

    highlights = Table([
        ["Particulars", "FY2023", "FY2024", "FY2025"],
        ["PROFITABILITY", "", "", ""],
        ["Net Interest Income", "26,400", "29,700", "33,410"],
        ["Other Income", "6,600", "7,400", "8,300"],
        ["Total Income", "36,900", "41,200", "46,800"],
        ["Operating Expenses", "10,800", "11,900", "13,100"],
        ["Operating Profit", "22,700", "25,200", "28,610"],
        ["BALANCE SHEET", "", "", ""],
        ["Total Assets", "4,81,000", "5,42,000", "6,18,000"],
        ["Net Worth", "42,300", "47,500", "53,400"],
        ["Gross Advances", "3,18,000", "3,61,000", "4,12,000"],
        ["Total Deposits", "3,79,000", "4,28,000", "4,86,000"],
        ["ASSET QUALITY", "", "", ""],
        ["Gross NPA", "6,300", "5,900", "5,400"],
        ["Net NPA", "1,760", "1,520", "1,310"],
        ["NETWORK", "", "", ""],
        ["Number of Branches", "3,020", "3,150", "3,275"],
        ["Number of Employees", "49,100", "52,400", "55,800"],
    ])
    highlights.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A120B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#C7A56A")),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ]))
    story += [highlights, PageBreak(),
              Paragraph("Key Ratios", STYLES["Heading2"])]

    ratios = Table([
        ["Ratio", "FY2024", "FY2025"],
        ["Gross NPA Ratio (%)", "1.63", "1.31"],
        ["Net NPA Ratio (%)", "0.42", "0.32"],
        ["CET1 Ratio (%)", "13.9", "14.2"],
        ["Tier 1 Capital Ratio (%)", "14.6", "14.9"],
        ["Capital Adequacy Ratio (%)", "16.8", "17.1"],
    ])
    ratios.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    story += [
        ratios,
        Spacer(1, 0.5 * cm),
        Paragraph(
            "Note 1: Figures for FY2023 and FY2024 have been regrouped where "
            "necessary. Note 2: Ratios are computed on period-end balances unless "
            "stated otherwise.", STYLES["Italic"]),
    ]
    doc.build(story)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "stress_annual_report.pdf"
    build(out)
    print(f"Wrote {out}")
