"""Warehouse query layer.

Produces the contract-shaped KPI payloads (docs/API_CONTRACT.md) consumed by
the API, narrative engine and all three export formats — one read path for
every output surface.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Bank, KpiValue
from app.modules.kpi_warehouse.calculation import yoy_delta
from app.modules.kpi_warehouse.registry import KPI_REGISTRY


def fiscal_years(db: Session, bank_id: int) -> list[str]:
    rows = db.execute(
        select(KpiValue.fiscal_year).where(KpiValue.bank_id == bank_id).distinct()
    ).scalars().all()
    return sorted(rows)


def prior_year(db: Session, bank_id: int, fy: str) -> str | None:
    years = fiscal_years(db, bank_id)
    if fy not in years:
        return None
    idx = years.index(fy)
    return years[idx - 1] if idx > 0 else None


def values_map(db: Session, bank_id: int, fy: str) -> dict[str, KpiValue]:
    rows = db.execute(
        select(KpiValue).where(KpiValue.bank_id == bank_id, KpiValue.fiscal_year == fy)
    ).scalars().all()
    return {r.kpi_code: r for r in rows}


def kpi_payload(db: Session, bank: Bank, fy: str) -> dict:
    cur = values_map(db, bank.id, fy)
    prev_fy = prior_year(db, bank.id, fy)
    prev = values_map(db, bank.id, prev_fy) if prev_fy else {}

    kpis = []
    for code, row in cur.items():
        kpi = KPI_REGISTRY.get(code)
        if kpi is None:
            continue  # warehouse may hold codes a newer registry dropped
        prior_row = prev.get(code)
        abs_chg, pct_chg = yoy_delta(row.value, prior_row.value if prior_row else None)
        doc = row.document
        kpis.append({
            "kpi_code": code,
            "name": kpi.name,
            "category": kpi.category,
            "unit": kpi.unit,
            "direction": kpi.direction,
            "value": row.value,
            "fiscal_year": fy,
            "yoy_change": abs_chg,
            "yoy_change_pct": pct_chg,
            "lineage": {
                "document_id": row.document_id,
                "document_title": doc.title if doc else None,
                "page": row.page,
                "extraction_method": row.extraction_method,
                "confidence": row.confidence,
                "source_text": row.source_text,
            },
            "validation_status": row.validation_status,
        })

    order = list(KPI_REGISTRY)
    kpis.sort(key=lambda k: order.index(k["kpi_code"]))
    return {
        "bank": {"id": bank.id, "code": bank.code, "name": bank.name},
        "fiscal_year": fy,
        "kpis": kpis,
    }


def history(db: Session, bank_id: int, kpi_code: str) -> dict:
    kpi = KPI_REGISTRY[kpi_code]
    rows = db.execute(
        select(KpiValue)
        .where(KpiValue.bank_id == bank_id, KpiValue.kpi_code == kpi_code)
        .order_by(KpiValue.fiscal_year)
    ).scalars().all()
    return {
        "kpi_code": kpi_code,
        "name": kpi.name,
        "unit": kpi.unit,
        "direction": kpi.direction,
        "series": [{"fiscal_year": r.fiscal_year, "value": r.value} for r in rows],
    }


def upsert_value(db: Session, *, bank_id: int, fy: str, kpi_code: str, value: float,
                 document_id: int | None = None, page: int | None = None,
                 extraction_method: str = "manual", confidence: float = 1.0,
                 source_text: str | None = None) -> KpiValue:
    """Insert or overwrite the resolved fact for (bank, fy, kpi).

    Higher-confidence extractions replace lower-confidence ones; equal or lower
    confidence never silently overwrites an existing fact.
    """
    existing = db.execute(
        select(KpiValue).where(
            KpiValue.bank_id == bank_id, KpiValue.fiscal_year == fy, KpiValue.kpi_code == kpi_code
        )
    ).scalar_one_or_none()
    if existing is not None:
        if confidence <= existing.confidence and existing.extraction_method != "derived":
            return existing
        row = existing
    else:
        row = KpiValue(bank_id=bank_id, fiscal_year=fy, kpi_code=kpi_code)
        db.add(row)
    row.value = value
    row.document_id = document_id
    row.page = page
    row.extraction_method = extraction_method
    row.confidence = confidence
    row.source_text = source_text
    row.validation_status = "unvalidated"
    return row
