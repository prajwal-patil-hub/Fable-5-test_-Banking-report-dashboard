"""The single calculation engine.

Derives missing KPIs from base facts using registry formulas. Reported values
always win over derived ones — a bank's published ROE reflects its official
calculation basis; we only backfill gaps, and a validation rule separately
flags reported-vs-derived divergence.

Used by the ingestion pipeline and the seed loader. Dashboard, PDF, PPT and
Excel never compute anything themselves — they read warehouse facts that came
through here.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.modules.kpi_warehouse.registry import KPI_REGISTRY


@dataclass(frozen=True)
class DerivedValue:
    kpi_code: str
    value: float
    expression: str  # lineage for derived facts


def derive_missing(current: dict[str, float], prior: dict[str, float] | None = None,
                   max_passes: int = 3) -> list[DerivedValue]:
    """Compute every registry formula whose inputs are available and whose
    output is missing from ``current``.

    Runs multiple passes so chained derivations resolve (e.g. a ratio whose
    numerator was itself derived). ``current``/``prior`` map kpi_code -> value.
    """
    prior = prior or {}
    values = dict(current)
    derived: list[DerivedValue] = []

    for _ in range(max_passes):
        progressed = False
        for kpi in KPI_REGISTRY.values():
            if kpi.formula is None or kpi.code in values:
                continue
            f = kpi.formula
            if any(values.get(i) is None for i in f.inputs):
                continue
            if any(prior.get(i) is None for i in f.prior_inputs):
                continue
            result = f.compute(values, prior)
            if result is None:
                continue
            values[kpi.code] = result
            derived.append(DerivedValue(kpi.code, result, f.expression))
            progressed = True
        if not progressed:
            break
    return derived


def yoy_delta(current: float | None, prior: float | None) -> tuple[float | None, float | None]:
    """(absolute change, percent change) vs prior year."""
    if current is None or prior is None:
        return None, None
    abs_change = round(current - prior, 2)
    pct_change = round((current / prior - 1) * 100, 2) if prior != 0 else None
    return abs_change, pct_change
