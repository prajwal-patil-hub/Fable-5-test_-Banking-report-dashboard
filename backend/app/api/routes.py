"""HTTP layer. Thin by design: every endpoint delegates to a module service —
no business logic lives here. Shapes per docs/API_CONTRACT.md."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models import AuditLog, Bank, Document, KpiValue, ValidationResult
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


VALID_SEGMENTS = ("private", "public", "sfb", "foreign", "universal")


@router.get("/banks")
def list_banks(db: Session = Depends(get_db)):
    banks = db.execute(select(Bank).order_by(Bank.name)).scalars().all()
    with_data = set(db.execute(select(KpiValue.bank_id).distinct()).scalars().all())
    return {"banks": [{"id": b.id, "code": b.code, "name": b.name,
                       "segment": b.segment, "is_demo": b.is_demo,
                       "has_data": b.id in with_data}
                      for b in banks]}


class BankCreate(BaseModel):
    name: str
    segment: str = "private"
    code: str | None = None


@router.post("/banks", status_code=201)
def create_bank(payload: BankCreate, db: Session = Depends(get_db)):
    """Register an institution not in the seeded roster; its figures arrive
    via document upload."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(422, "Bank name must not be empty")
    if payload.segment not in VALID_SEGMENTS:
        raise HTTPException(422, f"segment must be one of {', '.join(VALID_SEGMENTS)}")
    if db.execute(select(Bank).where(Bank.name.ilike(name))).scalar_one_or_none():
        raise HTTPException(409, f"Bank named '{name}' already exists")

    code = (payload.code or "".join(w[0] for w in name.split() if w[:1].isalpha())).upper()[:20]
    base_code, suffix = code or "BANK", 2
    while db.execute(select(Bank).where(Bank.code == code)).scalar_one_or_none():
        code = f"{base_code}{suffix}"[:20]
        suffix += 1

    bank = Bank(code=code, name=name, segment=payload.segment, is_demo=False)
    db.add(bank)
    db.add(AuditLog(action="bank_created", detail=f"name={name} segment={payload.segment}"))
    db.commit()
    return {"id": bank.id, "code": bank.code, "name": bank.name,
            "segment": bank.segment, "is_demo": bank.is_demo, "has_data": False}


@router.get("/banks/{bank_id}/years")
def list_years(bank_id: int, db: Session = Depends(get_db)):
    _bank(db, bank_id)
    return {"fiscal_years": warehouse.fiscal_years(db, bank_id)}


def _check_currency(currency: str) -> str:
    if currency not in ("inr", "usd"):
        raise HTTPException(422, "currency must be 'inr' or 'usd'")
    return currency


@router.get("/banks/{bank_id}/kpis")
def bank_kpis(bank_id: int, fiscal_year: str, currency: str = "inr",
              db: Session = Depends(get_db)):
    return warehouse.kpi_payload(db, _bank(db, bank_id), fiscal_year,
                                 _check_currency(currency))


@router.get("/banks/{bank_id}/kpis/{kpi_code}/history")
def kpi_history(bank_id: int, kpi_code: str, currency: str = "inr",
                db: Session = Depends(get_db)):
    _bank(db, bank_id)
    if kpi_code not in KPI_REGISTRY:
        raise HTTPException(404, f"Unknown KPI: {kpi_code}")
    return warehouse.history(db, bank_id, kpi_code, _check_currency(currency))


@router.get("/benchmarking")
def benchmarking(kpi_code: str, fiscal_year: str, segment: str | None = None,
                 db: Session = Depends(get_db)):
    if kpi_code not in KPI_REGISTRY:
        raise HTTPException(404, f"Unknown KPI: {kpi_code}")
    return benchmark_kpi(db, kpi_code, fiscal_year, segment)


@router.get("/benchmarking/summary")
def benchmarking_summary(fiscal_year: str, segment: str | None = None,
                         db: Session = Depends(get_db)):
    return benchmark_summary(db, fiscal_year, segment)


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
    if len(data) > 50 * 1024 * 1024:
        raise HTTPException(413, "PDF exceeds the 50 MB upload limit")
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
