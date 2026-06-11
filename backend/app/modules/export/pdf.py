"""Annual Banking Intelligence Report (PDF) — cover, table of contents,
per-module analysis with evidence tables and recommendations, appendix with
full lineage. Built with reportlab/platypus."""
from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)
from sqlalchemy.orm import Session

from app.models import Bank
from app.modules.benchmarking.engine import benchmark_summary
from app.modules.export import theme
from app.modules.export.theme import CATEGORY_LABELS, MODULE_LABELS, format_value
from app.modules.kpi_warehouse import service as warehouse
from app.modules.narrative.engine import build_narrative

INK = colors.HexColor(f"#{theme.INK}")
CARD = colors.HexColor(f"#{theme.CARD}")
GOLD = colors.HexColor(f"#{theme.GOLD}")
TEXT = colors.HexColor(f"#{theme.TEXT_PRIMARY}")
TEXT_2 = colors.HexColor(f"#{theme.TEXT_SECONDARY}")
BORDER = colors.HexColor(f"#{theme.BORDER}")

S_TITLE = ParagraphStyle("title", fontName="Times-Bold", fontSize=30, textColor=GOLD, leading=36)
S_SUB = ParagraphStyle("sub", fontName="Times-Roman", fontSize=15, textColor=TEXT, leading=20)
S_H1 = ParagraphStyle("h1", fontName="Times-Bold", fontSize=18, textColor=INK,
                      spaceBefore=18, spaceAfter=8)
S_H2 = ParagraphStyle("h2", fontName="Times-Bold", fontSize=13, textColor=CARD, spaceAfter=6)
S_BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=15,
                        textColor=colors.HexColor("#33291F"))
S_BULLET = ParagraphStyle("bullet", parent=S_BODY, leftIndent=14, bulletIndent=4)
S_FOOT = ParagraphStyle("foot", fontName="Helvetica", fontSize=8, textColor=TEXT_2)


def _cover(story: list, bank: Bank, fy: str) -> None:
    story.append(Spacer(1, 6 * cm))
    story.append(Paragraph("SOVEREIGN", S_TITLE))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("Annual Banking Intelligence Report", S_SUB))
    story.append(Spacer(1, 1.6 * cm))
    story.append(Paragraph(f"<b>{bank.name}</b> ({bank.code})", S_SUB))
    story.append(Paragraph(f"Fiscal Year {fy.removeprefix('FY')}", S_SUB))
    story.append(Spacer(1, 8 * cm))
    story.append(Paragraph(
        f"Generated {date.today():%d %B %Y} · Sovereign Banking Intelligence Platform · "
        f"All figures from the validated KPI warehouse with full source lineage.", S_FOOT))
    story.append(PageBreak())


def _toc(story: list, sections: list[dict]) -> None:
    story.append(Paragraph("Table of Contents", S_H1))
    entries = ["Executive Summary"] + \
              [MODULE_LABELS.get(s["module"], s["module"]) for s in sections] + \
              ["Peer Benchmarking Detail", "Appendix — KPI Lineage"]
    for i, entry in enumerate(entries, start=1):
        story.append(Paragraph(f"{i}.  {entry}", S_BODY))
    story.append(PageBreak())


def _kpi_table(kpis: list[dict]) -> Table:
    data = [["KPI", "Value", "YoY Δ", "Validation"]]
    for k in kpis:
        yoy = f"{k['yoy_change']:+,.2f}" if k["yoy_change"] is not None else "—"
        data.append([k["name"], format_value(k["value"], k["unit"]), yoy, k["validation_status"]])
    table = Table(data, colWidths=[7 * cm, 4 * cm, 3 * cm, 3 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), GOLD),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F1E7")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def build_pdf(db: Session, bank: Bank, fy: str) -> bytes:
    narrative = build_narrative(db, bank, fy)
    payload = warehouse.kpi_payload(db, bank, fy)
    by_category: dict[str, list[dict]] = {}
    for k in payload["kpis"]:
        by_category.setdefault(k["category"], []).append(k)

    buf = io.BytesIO()

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(TEXT_2)
        canvas.drawString(2 * cm, 1.2 * cm, f"Sovereign · {bank.name} · {fy}")
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc_.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm,
                            title=f"Sovereign — {bank.name} {fy}")
    story: list = []
    _cover(story, bank, fy)
    _toc(story, narrative["sections"])

    story.append(Paragraph("1. Executive Summary", S_H1))
    for bullet in narrative["executive_summary"]:
        story.append(Paragraph(bullet, S_BULLET, bulletText="—"))
    story.append(Spacer(1, 0.5 * cm))

    module_category = {"financial": "financial", "asset_quality": "asset_quality",
                       "capital": "capital", "liquidity": "liquidity",
                       "operations": "operations"}
    for i, section in enumerate(narrative["sections"], start=2):
        story.append(Paragraph(f"{i}. {MODULE_LABELS.get(section['module'], section['module'])}",
                               S_H1))
        story.append(Paragraph(section["headline"], S_H2))
        story.append(Paragraph(section["commentary"], S_BODY))
        story.append(Spacer(1, 0.3 * cm))
        category = module_category.get(section["module"])
        if category and by_category.get(category):
            story.append(_kpi_table(by_category[category]))
            story.append(Spacer(1, 0.3 * cm))
        for t in section["takeaways"]:
            story.append(Paragraph(f"<b>Takeaway:</b> {t}", S_BULLET, bulletText="—"))
        for r in section["recommendations"]:
            story.append(Paragraph(f"<b>Recommendation:</b> {r}", S_BULLET, bulletText="—"))
        story.append(Spacer(1, 0.5 * cm))

    # Benchmarking detail
    story.append(PageBreak())
    story.append(Paragraph("Peer Benchmarking Detail", S_H1))
    bench = benchmark_summary(db, fy)
    for b in bench["kpis"]:
        data = [[b["name"], "Value", "Rank", "Percentile"]] + [
            [p["bank_name"], format_value(p["value"], b["unit"]), p["rank"], p["percentile"]]
            for p in b["peers"]
        ]
        table = Table(data, colWidths=[7 * cm, 4 * cm, 3 * cm, 3 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), CARD),
            ("TEXTCOLOR", (0, 0), (-1, 0), GOLD),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.4 * cm))

    # Lineage appendix
    story.append(PageBreak())
    story.append(Paragraph("Appendix — KPI Lineage", S_H1))
    data = [["KPI", "Method", "Conf.", "Document", "Page"]]
    for k in payload["kpis"]:
        lin = k["lineage"]
        data.append([k["name"], lin["extraction_method"], f"{lin['confidence']:.2f}",
                     (lin["document_title"] or "—")[:45], lin["page"] or "—"])
    table = Table(data, colWidths=[5.5 * cm, 2.5 * cm, 1.5 * cm, 6 * cm, 1.5 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), GOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(table)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
