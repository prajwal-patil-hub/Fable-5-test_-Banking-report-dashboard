"""Benchmarking engine — peer comparison over warehouse facts.

Ranks every bank with a value for (kpi, fiscal_year); rank 1 is best given the
KPI's direction. Percentile is 0–100 with 100 = best, so the dashboard, deck
and narrative all describe positioning identically.
"""
from __future__ import annotations

from statistics import mean, median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Bank, KpiValue
from app.modules.kpi_warehouse.registry import KPI_REGISTRY, benchmarkable_kpis


def benchmark_kpi(db: Session, kpi_code: str, fy: str) -> dict:
    kpi = KPI_REGISTRY[kpi_code]
    rows = db.execute(
        select(KpiValue, Bank)
        .join(Bank, Bank.id == KpiValue.bank_id)
        .where(KpiValue.kpi_code == kpi_code, KpiValue.fiscal_year == fy)
    ).all()

    entries = [
        {"bank_id": bank.id, "bank_code": bank.code, "bank_name": bank.name, "value": kv.value}
        for kv, bank in rows if kv.value is not None
    ]
    reverse = kpi.direction != "lower_is_better"  # neutral ranks like higher_is_better
    entries.sort(key=lambda e: e["value"], reverse=reverse)

    n = len(entries)
    for i, e in enumerate(entries):
        e["rank"] = i + 1
        e["percentile"] = round((n - 1 - i) / (n - 1) * 100, 1) if n > 1 else 100.0

    values = [e["value"] for e in entries]
    stats = {
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "median": round(median(values), 2) if values else None,
        "mean": round(mean(values), 2) if values else None,
    }
    return {
        "kpi_code": kpi_code, "name": kpi.name, "unit": kpi.unit,
        "direction": kpi.direction, "fiscal_year": fy,
        "peers": entries, "stats": stats,
    }


def benchmark_summary(db: Session, fy: str) -> dict:
    return {
        "fiscal_year": fy,
        "kpis": [benchmark_kpi(db, k.code, fy) for k in benchmarkable_kpis()],
    }


def bank_position(db: Session, bank_id: int, kpi_code: str, fy: str) -> dict | None:
    """Convenience for the narrative engine: this bank's rank/percentile."""
    result = benchmark_kpi(db, kpi_code, fy)
    for peer in result["peers"]:
        if peer["bank_id"] == bank_id:
            return {**peer, "peer_count": len(result["peers"]), "stats": result["stats"]}
    return None
