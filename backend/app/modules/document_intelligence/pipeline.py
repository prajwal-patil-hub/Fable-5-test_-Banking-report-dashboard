"""Ingestion pipeline: PDF → pages → candidates → resolved facts → derived
KPIs → validation. One transaction per document.

Scanned (image-only) PDFs go through the OCR stage (Tesseract) when it is
installed; its candidates carry a confidence haircut and the document is
marked ``processed_ocr``. Without OCR capability the document is marked
``ocr_required`` instead of silently producing an empty extraction.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, replace

import pdfplumber
from sqlalchemy.orm import Session

from app.models import AuditLog, Document, ValidationResult
from app.modules.document_intelligence.extractors import (
    DEFAULT_EXTRACTORS, Candidate, PageContent, resolve,
)
from app.modules.document_intelligence.fiscal import fy_mismatch
from app.modules.document_intelligence.ocr import (
    OCR_CONFIDENCE_FACTOR, ocr_available, ocr_pdf_pages,
)
from app.modules.kpi_warehouse import service as warehouse
from app.modules.kpi_warehouse.calculation import derive_missing
from app.modules.validation.engine import validate_bank_year


@dataclass
class IngestResult:
    document: Document
    extracted: dict[str, Candidate]
    derived_count: int
    validation_passed: int
    validation_warnings: int
    validation_failed: int


def read_pdf(data: bytes) -> list[PageContent]:
    from app.modules.document_intelligence.normalize import detect_scale_hint

    raw: list[tuple[int, str, list]] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            raw.append((i, page.extract_text() or "", page.extract_tables() or []))

    # Statement denomination ("₹ in lakh" etc.): a page's own caption wins;
    # pages without one inherit the document's first declared scale, so a
    # single front-matter caption governs the tables that follow it.
    doc_hint = next((h for _, text, _ in raw
                     if (h := detect_scale_hint(text)) is not None), None)
    return [PageContent(number=i, text=text, tables=tables,
                        scale_hint=detect_scale_hint(text) or doc_hint)
            for i, text, tables in raw]


def ingest_pdf(db: Session, *, data: bytes, bank_id: int, doc_type: str,
               fiscal_year: str, title: str, filename: str | None = None) -> IngestResult:
    pages = read_pdf(data)
    is_scanned = bool(pages) and all(not p.text.strip() for p in pages)

    ocr_used = False
    if is_scanned and ocr_available():
        texts = ocr_pdf_pages(data)
        if any(t.strip() for t in texts):
            pages = [PageContent(number=i, text=t, tables=[])
                     for i, t in enumerate(texts, start=1)]
            is_scanned = False
            ocr_used = True

    status = "ocr_required" if is_scanned else ("processed_ocr" if ocr_used else "processed")
    doc = Document(
        bank_id=bank_id, title=title, doc_type=doc_type, fiscal_year=fiscal_year,
        filename=filename, pages=len(pages), status=status,
    )
    db.add(doc)
    db.flush()

    resolved: dict[str, Candidate] = {}
    derived_count = 0
    counts = {"passed": 0, "warning": 0, "failed": 0}

    if not is_scanned:
        from app.core.config import settings
        from app.modules.document_intelligence.extractors import LlmExtractor

        extractors = list(DEFAULT_EXTRACTORS)
        if settings.llm_extraction_enabled:
            extractors.append(LlmExtractor())

        candidates: list[Candidate] = []
        for extractor in extractors:
            candidates.extend(extractor.extract(pages))
        if ocr_used:
            # OCR misreads digits in ways a native text layer never does
            candidates = [replace(c, confidence=round(c.confidence * OCR_CONFIDENCE_FACTOR, 3))
                          for c in candidates]
        resolved = resolve(candidates)

        for cand in resolved.values():
            warehouse.upsert_value(
                db, bank_id=bank_id, fy=fiscal_year, kpi_code=cand.kpi_code,
                value=cand.value, document_id=doc.id, page=cand.page,
                extraction_method=cand.method, confidence=cand.confidence,
                source_text=cand.source_text,
            )
        db.flush()

        # Derive missing KPIs from what this document (plus prior facts) provides
        cur_rows = warehouse.values_map(db, bank_id, fiscal_year)
        cur = {c: r.value for c, r in cur_rows.items()}
        prev_fy = warehouse.prior_year(db, bank_id, fiscal_year)
        prev_rows = warehouse.values_map(db, bank_id, prev_fy) if prev_fy else {}
        prev = {c: r.value for c, r in prev_rows.items()}
        for d in derive_missing(cur, prev):
            warehouse.upsert_value(
                db, bank_id=bank_id, fy=fiscal_year, kpi_code=d.kpi_code, value=d.value,
                document_id=doc.id, page=None, extraction_method="derived",
                confidence=0.99, source_text=f"Derived: {d.expression}",
            )
            derived_count += 1
        db.flush()

        cur_rows = warehouse.values_map(db, bank_id, fiscal_year)
        outcomes = validate_bank_year(
            db, bank_id, fiscal_year,
            {c: r.value for c, r in cur_rows.items()}, prev)
        for o in outcomes:
            if o.status == "passed":
                counts["passed"] += 1
            elif o.rule.severity == "error":
                counts["failed"] += 1
            else:
                counts["warning"] += 1

        # Document-level cross-check: does the file's own text agree with the
        # fiscal year it was filed under? (Runs after validate_bank_year,
        # which clears and rewrites the bank-year's rule results.)
        front_matter = "\n".join(p.text for p in pages[:5])
        mismatch = fy_mismatch(fiscal_year, front_matter)
        db.add(ValidationResult(
            bank_id=bank_id, fiscal_year=fiscal_year,
            rule_code="fy_crosscheck",
            rule_name="Declared fiscal year matches document text",
            severity="warning",
            status="failed" if mismatch else "passed",
            message=mismatch or "OK",
        ))
        if mismatch:
            counts["warning"] += 1
        else:
            counts["passed"] += 1

    db.add(AuditLog(action="document_ingested",
                    detail=f"doc={doc.id} bank={bank_id} fy={fiscal_year} "
                           f"extracted={len(resolved)} derived={derived_count} "
                           f"status={doc.status}"))
    db.commit()
    return IngestResult(doc, resolved, derived_count,
                        counts["passed"], counts["warning"], counts["failed"])
