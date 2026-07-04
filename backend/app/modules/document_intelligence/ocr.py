"""OCR stage for scanned (image-only) PDFs.

Sits in front of the extractors: when a PDF yields no text layer, pages are
rasterised (pypdfium2) and read with Tesseract. OCR output is plain text —
table *structure* is lost, so only the rule-based extractor applies, and all
OCR-derived candidates carry a confidence haircut (OCR misreads digits in
ways a text layer never does).

Optional capability: requires `pip install -e ".[ocr]"` plus the tesseract
binary. When unavailable, ingestion degrades exactly as before — the document
is marked ``ocr_required`` rather than failing.
"""
from __future__ import annotations

OCR_CONFIDENCE_FACTOR = 0.85  # applied to every candidate extracted from OCR text
RENDER_SCALE = 200 / 72  # ~200 dpi — Tesseract's sweet spot for report body text


def ocr_available() -> bool:
    try:
        import pypdfium2  # noqa: F401
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_pdf_pages(data: bytes) -> list[str]:
    """Rasterise each page and return its OCR'd text ('' for unreadable pages)."""
    import pypdfium2 as pdfium
    import pytesseract

    texts: list[str] = []
    pdf = pdfium.PdfDocument(data)
    try:
        for page in pdf:
            bitmap = page.render(scale=RENDER_SCALE)
            image = bitmap.to_pil()
            try:
                texts.append(pytesseract.image_to_string(image) or "")
            except Exception:
                texts.append("")
    finally:
        pdf.close()
    return texts
