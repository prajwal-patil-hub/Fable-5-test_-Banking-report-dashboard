"""The universal banking KPI registry — single source of truth for KPI semantics.

Every module reads from this catalog:
- the extraction engine uses ``aliases`` to map report language to KPI codes;
- the calculation engine uses ``formula`` to derive missing metrics;
- the benchmarking engine uses ``benchmarkable`` and ``direction``;
- the narrative/export/dashboard layers use names, units and categories.

Adding a KPI means adding ONE entry here — no other module needs to change.

Two deliberate semantics:
- A KPI may be both extractable and derivable (e.g. ROE). The reported figure
  wins; the formula only backfills when the figure is absent. Reported ratios
  reflect management's official basis (e.g. average vs closing equity) and a
  consistency-check rule flags material divergence instead of overwriting.
- Formulas declare their inputs explicitly so derived values are auditable:
  lineage for a derived value records the expression, not a black box.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

Values = Mapping[str, float]


@dataclass(frozen=True)
class Formula:
    inputs: tuple[str, ...]
    expression: str  # human-readable, surfaced as lineage for derived values
    compute: Callable[[Values, Values], float | None]  # (current, prior) -> value
    prior_inputs: tuple[str, ...] = ()


@dataclass(frozen=True)
class KpiDef:
    code: str
    name: str
    category: str  # financial | asset_quality | capital | liquidity | operations | esg
    unit: str  # inr_crore | percent | count | ratio
    direction: str  # higher_is_better | lower_is_better | neutral
    aliases: tuple[str, ...] = ()
    formula: Formula | None = None
    benchmarkable: bool = False
    description: str = ""


def _ratio(num: str, den: str, expression: str) -> Formula:
    def compute(cur: Values, _prior: Values) -> float | None:
        n, d = cur.get(num), cur.get(den)
        if n is None or d in (None, 0):
            return None
        return round(n / d * 100, 2)

    return Formula(inputs=(num, den), expression=expression, compute=compute)


def _yoy_growth(code: str, label: str) -> Formula:
    def compute(cur: Values, prior: Values) -> float | None:
        c, p = cur.get(code), prior.get(code)
        if c is None or p in (None, 0):
            return None
        return round((c / p - 1) * 100, 2)

    return Formula(inputs=(code,), prior_inputs=(code,),
                   expression=f"YoY growth of {label}", compute=compute)


def _cti_formula() -> Formula:
    def compute(cur: Values, _prior: Values) -> float | None:
        opex, nii, other = cur.get("operating_expenses"), cur.get("nii"), cur.get("other_income")
        if opex is None or nii is None or other is None or (nii + other) == 0:
            return None
        return round(opex / (nii + other) * 100, 2)

    return Formula(inputs=("operating_expenses", "nii", "other_income"),
                   expression="Operating Expenses / (NII + Other Income) × 100", compute=compute)


KPI_REGISTRY: dict[str, KpiDef] = {}


def _register(*defs: KpiDef) -> None:
    for d in defs:
        if d.code in KPI_REGISTRY:
            raise ValueError(f"duplicate KPI code: {d.code}")
        KPI_REGISTRY[d.code] = d


# ---------------------------------------------------------------- financial
_register(
    KpiDef("total_income", "Total Income", "financial", "inr_crore", "higher_is_better",
           aliases=("total income", "total revenue", "revenue")),
    KpiDef("nii", "Net Interest Income", "financial", "inr_crore", "higher_is_better",
           aliases=("net interest income", "nii")),
    KpiDef("other_income", "Other Income", "financial", "inr_crore", "higher_is_better",
           aliases=("other income", "non-interest income", "non interest income")),
    KpiDef("nim", "Net Interest Margin", "financial", "percent", "higher_is_better",
           aliases=("net interest margin", "nim"), benchmarkable=True),
    KpiDef("operating_expenses", "Operating Expenses", "financial", "inr_crore", "lower_is_better",
           aliases=("operating expenses", "operating expense", "opex")),
    KpiDef("operating_profit", "Operating Profit", "financial", "inr_crore", "higher_is_better",
           aliases=("operating profit", "pre-provision operating profit", "ppop")),
    KpiDef("pat", "Profit After Tax", "financial", "inr_crore", "higher_is_better",
           aliases=("profit after tax", "net profit", "pat", "profit for the year"),
           benchmarkable=True),
    KpiDef("total_assets", "Total Assets", "financial", "inr_crore", "neutral",
           aliases=("total assets",)),
    KpiDef("net_worth", "Net Worth", "financial", "inr_crore", "neutral",
           aliases=("net worth", "shareholders' funds", "shareholders funds", "total equity")),
    KpiDef("roa", "Return on Assets", "financial", "percent", "higher_is_better",
           aliases=("return on assets", "roa"),
           formula=_ratio("pat", "total_assets", "PAT / Total Assets × 100"),
           benchmarkable=True),
    KpiDef("roe", "Return on Equity", "financial", "percent", "higher_is_better",
           aliases=("return on equity", "roe", "return on net worth"),
           formula=_ratio("pat", "net_worth", "PAT / Net Worth × 100"),
           benchmarkable=True),
    KpiDef("cost_to_income", "Cost-to-Income Ratio", "financial", "percent", "lower_is_better",
           aliases=("cost to income ratio", "cost-to-income ratio", "cost to income"),
           formula=_cti_formula(), benchmarkable=True),
)

# ------------------------------------------------------------- asset quality
_register(
    KpiDef("gross_advances", "Gross Advances", "financial", "inr_crore", "higher_is_better",
           aliases=("gross advances", "advances", "total advances", "loans and advances")),
    KpiDef("gnpa", "Gross NPA", "asset_quality", "inr_crore", "lower_is_better",
           aliases=("gross npa", "gross non-performing assets", "gnpa")),
    KpiDef("nnpa", "Net NPA", "asset_quality", "inr_crore", "lower_is_better",
           aliases=("net npa", "net non-performing assets", "nnpa")),
    KpiDef("gnpa_ratio", "Gross NPA Ratio", "asset_quality", "percent", "lower_is_better",
           aliases=("gross npa ratio", "gnpa ratio", "gnpa %"),
           formula=_ratio("gnpa", "gross_advances", "Gross NPA / Gross Advances × 100"),
           benchmarkable=True),
    KpiDef("nnpa_ratio", "Net NPA Ratio", "asset_quality", "percent", "lower_is_better",
           aliases=("net npa ratio", "nnpa ratio", "nnpa %"),
           benchmarkable=True),
    KpiDef("pcr", "Provision Coverage Ratio", "asset_quality", "percent", "higher_is_better",
           aliases=("provision coverage ratio", "pcr"), benchmarkable=True),
    KpiDef("slippages", "Fresh Slippages", "asset_quality", "inr_crore", "lower_is_better",
           aliases=("fresh slippages", "slippages", "gross slippages")),
    KpiDef("recoveries", "Recoveries & Upgrades", "asset_quality", "inr_crore", "higher_is_better",
           aliases=("recoveries and upgrades", "recoveries & upgrades", "recoveries")),
)

# ------------------------------------------------------------------- capital
_register(
    KpiDef("cet1_ratio", "CET1 Ratio", "capital", "percent", "higher_is_better",
           aliases=("cet1 ratio", "common equity tier 1", "cet-1", "cet1"),
           benchmarkable=True),
    KpiDef("tier1_ratio", "Tier 1 Capital Ratio", "capital", "percent", "higher_is_better",
           aliases=("tier 1 capital ratio", "tier 1 ratio", "tier-1 ratio", "tier i")),
    KpiDef("crar", "Capital Adequacy Ratio (CRAR)", "capital", "percent", "higher_is_better",
           aliases=("capital adequacy ratio", "crar", "capital to risk weighted assets ratio",
                    "total capital ratio"),
           benchmarkable=True),
)

# ----------------------------------------------------------------- liquidity
_register(
    KpiDef("deposits", "Total Deposits", "liquidity", "inr_crore", "higher_is_better",
           aliases=("total deposits", "deposits")),
    KpiDef("casa_deposits", "CASA Deposits", "liquidity", "inr_crore", "higher_is_better",
           aliases=("casa deposits", "current and savings account deposits")),
    KpiDef("casa_ratio", "CASA Ratio", "liquidity", "percent", "higher_is_better",
           aliases=("casa ratio", "casa %"),
           formula=_ratio("casa_deposits", "deposits", "CASA Deposits / Total Deposits × 100"),
           benchmarkable=True),
    KpiDef("lcr", "Liquidity Coverage Ratio", "liquidity", "percent", "higher_is_better",
           aliases=("liquidity coverage ratio", "lcr"), benchmarkable=True),
    KpiDef("nsfr", "Net Stable Funding Ratio", "liquidity", "percent", "higher_is_better",
           aliases=("net stable funding ratio", "nsfr")),
    KpiDef("deposit_growth", "Deposit Growth (YoY)", "liquidity", "percent", "higher_is_better",
           aliases=("deposit growth",),
           formula=_yoy_growth("deposits", "Total Deposits")),
    KpiDef("loan_growth", "Loan Growth (YoY)", "liquidity", "percent", "higher_is_better",
           aliases=("loan growth", "advances growth", "credit growth"),
           formula=_yoy_growth("gross_advances", "Gross Advances")),
)

# ---------------------------------------------------------------- operations
_register(
    KpiDef("employees", "Employees", "operations", "count", "neutral",
           aliases=("number of employees", "employees", "employee count", "headcount")),
    KpiDef("branches", "Branches", "operations", "count", "neutral",
           aliases=("number of branches", "branches", "branch network")),
    KpiDef("customers", "Customers (mn)", "operations", "count", "higher_is_better",
           aliases=("customer base", "customers", "number of customers")),
    KpiDef("digital_txn_share", "Digital Transaction Share", "operations", "percent",
           "higher_is_better",
           aliases=("digital transaction share", "digital transactions share",
                    "share of digital transactions")),
)

# ----------------------------------------------------------------------- esg
_register(
    KpiDef("green_financing", "Green Financing Portfolio", "esg", "inr_crore", "higher_is_better",
           aliases=("green financing", "green financing portfolio", "sustainable finance portfolio")),
    KpiDef("women_workforce_pct", "Women in Workforce", "esg", "percent", "higher_is_better",
           aliases=("women in workforce", "female employees", "gender diversity ratio")),
)


def get_kpi(code: str) -> KpiDef:
    return KPI_REGISTRY[code]


def kpis_by_category(category: str) -> list[KpiDef]:
    return [k for k in KPI_REGISTRY.values() if k.category == category]


def benchmarkable_kpis() -> list[KpiDef]:
    return [k for k in KPI_REGISTRY.values() if k.benchmarkable]


def alias_index() -> list[tuple[str, str]]:
    """(alias, kpi_code) pairs, longest alias first so specific labels win
    (e.g. 'gross npa ratio' must match before 'gross npa')."""
    pairs = [(a, k.code) for k in KPI_REGISTRY.values() for a in k.aliases]
    return sorted(pairs, key=lambda p: -len(p[0]))
