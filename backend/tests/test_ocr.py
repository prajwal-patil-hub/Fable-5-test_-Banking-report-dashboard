"""Scanned-PDF OCR round trip. Skipped when Tesseract/OCR deps are absent —
ingestion must then mark the document ocr_required (also tested)."""
import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.modules.document_intelligence.ocr import ocr_available


def scanned_pdf(lines: list[str]) -> bytes:
    """A PDF whose single page is a rendered IMAGE of text — no text layer."""
    img = Image.new("RGB", (1700, 800), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    for i, line in enumerate(lines):
        draw.text((60, 60 + i * 70), line, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PDF", resolution=150)
    return buf.getvalue()


LINES = [
    "Pinnacle Trust Bank - Annual Report FY2025",
    "Net Interest Income of 18,420 crore for the year.",
    "Profit After Tax stood at 7,650 crore.",
    "Return on Equity was 15.1% for the year.",
]


@pytest.mark.skipif(not ocr_available(), reason="tesseract not installed")
def test_scanned_pdf_is_ocred_and_extracted(db, seeded_db):
    from app.modules.document_intelligence.pipeline import ingest_pdf
    from app.modules.kpi_warehouse import service as warehouse

    result = ingest_pdf(
        db, data=scanned_pdf(LINES), bank_id=1, doc_type="annual_report",
        fiscal_year="FY2027", title="Scanned demo")

    assert result.document.status == "processed_ocr"
    assert "nii" in result.extracted and result.extracted["nii"].value == 18420.0
    assert "roe" in result.extracted and result.extracted["roe"].value == 15.1
    # OCR haircut: below the clean-text rule-based confidence (~0.75)
    assert result.extracted["nii"].confidence < 0.70

    rows = warehouse.values_map(db, 1, "FY2027")
    assert rows["nii"].extraction_method == "rule_based"
    assert rows["nii"].page == 1


def test_without_ocr_scanned_pdf_marked_ocr_required(db, seeded_db, monkeypatch):
    from app.modules.document_intelligence import pipeline

    monkeypatch.setattr(pipeline, "ocr_available", lambda: False)
    result = pipeline.ingest_pdf(
        db, data=scanned_pdf(LINES), bank_id=1, doc_type="annual_report",
        fiscal_year="FY2027", title="Scanned demo")
    assert result.document.status == "ocr_required"
    assert result.extracted == {}
