"""Validation engine — every fact entering the warehouse passes through here.

Banking-specific structural rules (NNPA ≤ GNPA, CET1 ≤ Tier 1 ≤ CRAR, ...),
internal-consistency checks (reported ratios vs recomputation from components)
and historical plausibility checks (YoY jumps). Results are persisted per
bank-year and each rule failure marks the involved KPI facts so the dashboard
can badge individual numbers, not just the page.

Rules are pure functions over the value maps, so the engine is trivially unit
testable and extending it means appending to RULES.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import KpiValue, ValidationResult

Values = dict[str, float]


@dataclass(frozen=True)
class Rule:
    code: str
    name: str
    severity: str  # error | warning | info
    kpi_codes: tuple[str, ...]
    # returns failure message, or None if the rule passes / is not applicable
    check: Callable[[Values, Values], str | None]


def _need(values: Values, *codes: str) -> bool:
    return all(values.get(c) is not None for c in codes)


def _nnpa_le_gnpa(v: Values, _p: Values) -> str | None:
    if not _need(v, "gnpa", "nnpa"):
        return None
    if v["nnpa"] > v["gnpa"]:
        return f"Net NPA (₹{v['nnpa']:,.0f} Cr) exceeds Gross NPA (₹{v['gnpa']:,.0f} Cr)."
    return None


def _capital_stack(v: Values, _p: Values) -> str | None:
    if not _need(v, "cet1_ratio", "tier1_ratio", "crar"):
        return None
    if not (v["cet1_ratio"] <= v["tier1_ratio"] <= v["crar"]):
        return (f"Capital stack ordering violated: CET1 {v['cet1_ratio']}% / "
                f"Tier 1 {v['tier1_ratio']}% / CRAR {v['crar']}%.")
    return None


def _percent_range(code: str, lo: float, hi: float, label: str):
    def check(v: Values, _p: Values) -> str | None:
        val = v.get(code)
        if val is None:
            return None
        if not (lo <= val <= hi):
            return f"{label} of {val}% is outside the plausible range {lo}–{hi}%."
        return None
    return check


def _roe_consistency(v: Values, _p: Values) -> str | None:
    if not _need(v, "roe", "pat", "net_worth") or v["net_worth"] == 0:
        return None
    implied = v["pat"] / v["net_worth"] * 100
    if abs(implied - v["roe"]) > 2.0:
        return (f"Reported ROE {v['roe']}% diverges from PAT/Net Worth "
                f"({implied:.1f}%) by more than 2pp — check basis (average vs closing equity) "
                f"or extraction.")
    return None


def _gnpa_ratio_consistency(v: Values, _p: Values) -> str | None:
    if not _need(v, "gnpa_ratio", "gnpa", "gross_advances") or v["gross_advances"] == 0:
        return None
    implied = v["gnpa"] / v["gross_advances"] * 100
    if abs(implied - v["gnpa_ratio"]) > 0.5:
        return (f"Reported GNPA ratio {v['gnpa_ratio']}% diverges from GNPA/Gross Advances "
                f"({implied:.2f}%) — possible unit mismatch or extraction error.")
    return None


def _casa_consistency(v: Values, _p: Values) -> str | None:
    if not _need(v, "casa_ratio", "casa_deposits", "deposits") or v["deposits"] == 0:
        return None
    implied = v["casa_deposits"] / v["deposits"] * 100
    if abs(implied - v["casa_ratio"]) > 1.0:
        return (f"Reported CASA ratio {v['casa_ratio']}% diverges from "
                f"CASA/Deposits ({implied:.1f}%).")
    return None


def _crar_regulatory(v: Values, _p: Values) -> str | None:
    crar = v.get("crar")
    if crar is None:
        return None
    if crar < 11.5:
        return (f"CRAR of {crar}% is below the Basel III India comfort threshold of 11.5% "
                f"(incl. capital conservation buffer).")
    return None


def _yoy_jump(v: Values, p: Values) -> str | None:
    suspicious = []
    for code, val in v.items():
        prior = p.get(code)
        if prior in (None, 0) or val is None:
            continue
        change = abs(val / prior - 1)
        if change > 0.6:
            suspicious.append(f"{code} ({change * 100:.0f}% move)")
    if suspicious:
        return ("Unusually large YoY movement in: " + ", ".join(suspicious)
                + ". Verify extraction and units against source.")
    return None


def _headline_missing(v: Values, _p: Values) -> str | None:
    headline = ("pat", "roe", "gnpa_ratio", "crar", "casa_ratio")
    missing = [c for c in headline if v.get(c) is None]
    if missing:
        return "Headline KPIs missing from this period: " + ", ".join(missing) + "."
    return None


RULES: list[Rule] = [
    Rule("nnpa_le_gnpa", "Net NPA must not exceed Gross NPA", "error",
         ("gnpa", "nnpa"), _nnpa_le_gnpa),
    Rule("capital_stack_order", "CET1 ≤ Tier 1 ≤ CRAR ordering", "error",
         ("cet1_ratio", "tier1_ratio", "crar"), _capital_stack),
    Rule("pcr_range", "Provision coverage ratio within 0–100%", "error",
         ("pcr",), _percent_range("pcr", 0, 100, "Provision Coverage Ratio")),
    Rule("casa_range", "CASA ratio within 0–100%", "error",
         ("casa_ratio",), _percent_range("casa_ratio", 0, 100, "CASA Ratio")),
    Rule("cti_range", "Cost-to-income within plausible band (20–90%)", "warning",
         ("cost_to_income",), _percent_range("cost_to_income", 20, 90, "Cost-to-Income")),
    Rule("roe_consistency", "Reported ROE consistent with PAT / Net Worth", "warning",
         ("roe", "pat", "net_worth"), _roe_consistency),
    Rule("gnpa_ratio_consistency", "Reported GNPA ratio consistent with components", "warning",
         ("gnpa_ratio", "gnpa", "gross_advances"), _gnpa_ratio_consistency),
    Rule("casa_consistency", "Reported CASA ratio consistent with components", "warning",
         ("casa_ratio", "casa_deposits", "deposits"), _casa_consistency),
    Rule("crar_regulatory_floor", "CRAR vs Basel III India threshold", "info",
         ("crar",), _crar_regulatory),
    Rule("yoy_plausibility", "Year-over-year movement plausibility", "warning",
         (), _yoy_jump),
    Rule("headline_completeness", "Headline KPI completeness", "warning",
         (), _headline_missing),
]


@dataclass
class RuleOutcome:
    rule: Rule
    status: str  # passed | failed
    message: str


def run_rules(current: Values, prior: Values | None = None) -> list[RuleOutcome]:
    prior = prior or {}
    outcomes = []
    for rule in RULES:
        failure = rule.check(current, prior)
        outcomes.append(RuleOutcome(
            rule=rule,
            status="failed" if failure else "passed",
            message=failure or "OK",
        ))
    return outcomes


def validate_bank_year(db: Session, bank_id: int, fy: str,
                       current: Values, prior: Values | None = None) -> list[RuleOutcome]:
    """Run all rules, persist results, and badge each KPI fact with the worst
    outcome of any failed rule that names it."""
    outcomes = run_rules(current, prior)

    db.execute(delete(ValidationResult).where(
        ValidationResult.bank_id == bank_id, ValidationResult.fiscal_year == fy))
    for o in outcomes:
        db.add(ValidationResult(
            bank_id=bank_id, fiscal_year=fy, rule_code=o.rule.code, rule_name=o.rule.name,
            severity=o.rule.severity, status=o.status, message=o.message,
            kpi_codes=",".join(o.rule.kpi_codes),
        ))

    # error beats warning beats passed
    badge: dict[str, str] = {}
    for o in outcomes:
        if o.status != "failed":
            continue
        level = "failed" if o.rule.severity == "error" else "warning"
        for code in o.rule.kpi_codes:
            if badge.get(code) != "failed":
                badge[code] = level

    rows = db.execute(select(KpiValue).where(
        KpiValue.bank_id == bank_id, KpiValue.fiscal_year == fy)).scalars().all()
    for row in rows:
        row.validation_status = badge.get(row.kpi_code, "passed")
    return outcomes
