"""HTTP layer. Thin by design: every endpoint delegates to a module service —
no business logic lives here. Shapes per docs/API_CONTRACT.md."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models import Bank, Document, ValidationResult
from app.modules.benchmarking.engine import benchmark_kpi, benchmark_summary
from app.modules.document_intelligence.pipeline import ingest_pdf
from app.modules.export.excel import build_excel
from app.modules.export.pdf import build_pdf
from app.modules.export.pptx import build_pptx
from app.modules.kpi_warehouse import service as warehouse
from app.modules.kpi_warehouse.registry import KPI_REGISTRY
from app.modules.narrative.engine import build_narrative

router = APIRouter(prefix="/api")


def _bank(db: Session, bank_id: int) -> Bank:
    bank = db.get(Bank, bank_id)
    if bank is None:
        raise HTTPException(404, f"Bank {bank_id} not found")
    return bank


@router.get("/health")
def health():
    return {"status": "ok", "version": settings.version}


@router.get("/banks")
def list_banks(db: Session = Depends(get_db)):
    banks = db.execute(select(Bank).order_by(Bank.name)).scalars().all()
    return {"banks": [{"id": b.id, "code": b.code, "name": b.name, "is_demo": b.is_demo}
                      for b in banks]}


@router.get("/banks/{bank_id}/years")
def list_years(bank_id: int, db: Session = Depends(get_db)):
    _bank(db, bank_id)
    return {"fiscal_years": warehouse.fiscal_years(db, bank_id)}


@router.get("/banks/{bank_id}/kpis")
def bank_kpis(bank_id: int, fiscal_year: str, db: Session = Depends(get_db)):
    return warehouse.kpi_payload(db, _bank(db, bank_id), fiscal_year)


@router.get("/banks/{bank_id}/kpis/{kpi_code}/history")
def kpi_history(bank_id: int, kpi_code: str, db: Session = Depends(get_db)):
    _bank(db, bank_id)
    if kpi_code not in KPI_REGISTRY:
        raise HTTPException(404, f"Unknown KPI: {kpi_code}")
    return warehouse.history(db, bank_id, kpi_code)


@router.get("/benchmarking")
def benchmarking(kpi_code: str, fiscal_year: str, db: Session = Depends(get_db)):
    if kpi_code not in KPI_REGISTRY:
        raise HTTPException(404, f"Unknown KPI: {kpi_code}")
    return benchmark_kpi(db, kpi_code, fiscal_year)


@router.get("/benchmarking/summary")
def benchmarking_summary(fiscal_year: str, db: Session = Depends(get_db)):
    return benchmark_summary(db, fiscal_year)


@router.get("/banks/{bank_id}/narrative")
def narrative(bank_id: int, fiscal_year: str, db: Session = Depends(get_db)):
    return build_narrative(db, _bank(db, bank_id), fiscal_year)


@router.get("/banks/{bank_id}/validations")
def validations(bank_id: int, fiscal_year: str, db: Session = Depends(get_db)):
    _bank(db, bank_id)
    rows = db.execute(select(ValidationResult).where(
        ValidationResult.bank_id == bank_id,
        ValidationResult.fiscal_year == fiscal_year,
    )).scalars().all()
    return {"results": [{
        "rule_code": r.rule_code, "rule_name": r.rule_name, "severity": r.severity,
        "status": r.status, "message": r.message,
        "kpi_codes": [c for c in r.kpi_codes.split(",") if c],
    } for r in rows]}


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    docs = db.execute(select(Document).order_by(Document.uploaded_at.desc())).scalars().all()
    return {"documents": [{
        "id": d.id, "bank_id": d.bank_id, "title": d.title, "doc_type": d.doc_type,
        "fiscal_year": d.fiscal_year, "pages": d.pages, "status": d.status,
        "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None,
    } for d in docs]}


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    bank_id: int = Form(...),
    doc_type: str = Form("annual_report"),
    fiscal_year: str = Form(...),
    db: Session = Depends(get_db),
):
    bank = _bank(db, bank_id)
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF documents are supported")
    data = await file.read()
    try:
        result = ingest_pdf(
            db, data=data, bank_id=bank.id, doc_type=doc_type, fiscal_year=fiscal_year,
            title=file.filename or f"{bank.name} {doc_type} {fiscal_year}",
            filename=file.filename,
        )
    except Exception as exc:  # corrupt/unreadable PDF
        raise HTTPException(422, f"Could not process PDF: {exc}") from exc
    return {
        "document_id": result.document.id,
        "status": result.document.status,
        "extracted_count": len(result.extracted),
        "validation": {
            "passed": result.validation_passed,
            "warnings": result.validation_warnings,
            "failed": result.validation_failed,
        },
    }


def _export_response(content: bytes, media_type: str, filename: str) -> StreamingResponse:
    return StreamingResponse(
        io.BytesIO(content), media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/exports/excel")
def export_excel(bank_id: int, fiscal_year: str, db: Session = Depends(get_db)):
    bank = _bank(db, bank_id)
    return _export_response(
        build_excel(db, bank, fiscal_year),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        f"sovereign_{bank.code}_{fiscal_year}_datapack.xlsx")


@router.get("/exports/pptx")
def export_pptx(bank_id: int, fiscal_year: str, db: Session = Depends(get_db)):
    bank = _bank(db, bank_id)
    return _export_response(
        build_pptx(db, bank, fiscal_year),
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        f"sovereign_{bank.code}_{fiscal_year}_board_deck.pptx")


@router.get("/exports/pdf")
def export_pdf(bank_id: int, fiscal_year: str, db: Session = Depends(get_db)):
    bank = _bank(db, bank_id)
    return _export_response(
        build_pdf(db, bank, fiscal_year), "application/pdf",
        f"sovereign_{bank.code}_{fiscal_year}_intelligence_report.pdf")
