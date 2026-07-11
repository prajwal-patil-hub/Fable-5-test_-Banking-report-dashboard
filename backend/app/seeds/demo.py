"""Synthetic demo dataset — four fictional banks, three fiscal years.

The four institutions are deliberately distinct strategic archetypes so every
analytic surface (benchmarking spread, validation warnings, narrative
recommendations) has signal out of the box:

- SVRN Suvarna Bank           — high-performing private-sector franchise
- BHNB Bharat National Bank   — large PSU: cost-heavy, NPA overhang, improving
- NLND Nalanda Bank           — fast-growing private challenger: thin capital,
                              thin PCR, credit outrunning deposits (trips rules)
- HMGR Himgiri Bank           — conservative fortress balance sheet

All figures are synthetic (banks flagged ``is_demo``); they are calibrated to
plausible Indian mid/large-bank magnitudes so ratios and narratives read true.
Values flow through the same upsert → derive → validate path as real
ingestion — the seed exercises the production write path, not a shortcut.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Bank, Document
from app.modules.kpi_warehouse import service as warehouse
from app.modules.kpi_warehouse.calculation import derive_missing
from app.modules.validation.engine import validate_bank_year

FISCAL_YEARS = ["FY2023", "FY2024", "FY2025"]

# Per-bank: FY2023 base values, then either multiplicative growth ("g", %/yr)
# or additive drift ("d", units/yr) per KPI across the three years.
PROFILES: dict[str, dict] = {
    "SVRN": {
        "name": "Suvarna Bank", "segment": "private",
        "base": {
            "total_income": 52000, "nii": 21000, "other_income": 9000, "nim": 4.10,
            "operating_expenses": 12500, "operating_profit": 17500, "pat": 9800,
            "total_assets": 620000, "net_worth": 62000, "gross_advances": 380000,
            "gnpa": 8200, "nnpa": 2100, "nnpa_ratio": 0.55, "pcr": 76,
            "slippages": 5200, "recoveries": 3800,
            "cet1_ratio": 14.5, "tier1_ratio": 15.2, "crar": 17.0,
            "deposits": 450000, "casa_deposits": 198000, "lcr": 125, "nsfr": 118,
            "employees": 68000, "branches": 4200, "customers": 45, "digital_txn_share": 86,
            "green_financing": 18000, "women_workforce_pct": 26,
        },
        "growth": {"total_income": 15, "nii": 14, "other_income": 16, "operating_expenses": 11,
                   "operating_profit": 17, "pat": 18, "total_assets": 14, "net_worth": 15,
                   "gross_advances": 16, "deposits": 14, "casa_deposits": 12,
                   "gnpa": 2, "nnpa": -2, "slippages": 4, "recoveries": 9,
                   "employees": 5, "branches": 4, "customers": 9, "green_financing": 28},
        "drift": {"nim": 0.05, "nnpa_ratio": -0.05, "pcr": 1.0, "cet1_ratio": 0.2,
                  "tier1_ratio": 0.2, "crar": 0.1, "lcr": 2, "nsfr": 1,
                  "digital_txn_share": 3, "women_workforce_pct": 1.0},
    },
    "BHNB": {
        "name": "Bharat National Bank", "segment": "public",
        "base": {
            "total_income": 98000, "nii": 36000, "other_income": 14000, "nim": 2.85,
            "operating_expenses": 28500, "operating_profit": 21500, "pat": 8200,
            "total_assets": 1450000, "net_worth": 98000, "gross_advances": 820000,
            "gnpa": 49000, "nnpa": 12500, "nnpa_ratio": 1.55, "pcr": 74,
            "slippages": 21000, "recoveries": 16500,
            "cet1_ratio": 11.2, "tier1_ratio": 12.0, "crar": 14.3,
            "deposits": 1180000, "casa_deposits": 495000, "lcr": 138, "nsfr": 126,
            "employees": 182000, "branches": 11200, "customers": 110, "digital_txn_share": 71,
            "green_financing": 26000, "women_workforce_pct": 24,
        },
        "growth": {"total_income": 9, "nii": 8, "other_income": 7, "operating_expenses": 8,
                   "operating_profit": 9, "pat": 16, "total_assets": 9, "net_worth": 10,
                   "gross_advances": 11, "deposits": 9, "casa_deposits": 6,
                   "gnpa": -9, "nnpa": -13, "slippages": -7, "recoveries": 3,
                   "employees": -1, "branches": 0, "customers": 4, "green_financing": 18},
        "drift": {"nim": 0.04, "nnpa_ratio": -0.20, "pcr": 1.5, "cet1_ratio": 0.4,
                  "tier1_ratio": 0.4, "crar": 0.3, "lcr": -2, "nsfr": -1,
                  "digital_txn_share": 4, "women_workforce_pct": 0.7},
    },
    "NLND": {
        "name": "Nalanda Bank", "segment": "private",
        "base": {
            "total_income": 21000, "nii": 8200, "other_income": 3600, "nim": 3.95,
            "operating_expenses": 6100, "operating_profit": 5700, "pat": 2900,
            "total_assets": 245000, "net_worth": 21500, "gross_advances": 168000,
            "gnpa": 3900, "nnpa": 1450, "nnpa_ratio": 0.86, "pcr": 63,
            "slippages": 2900, "recoveries": 1700,
            "cet1_ratio": 12.6, "tier1_ratio": 13.1, "crar": 14.2,
            "deposits": 182000, "casa_deposits": 61000, "lcr": 112, "nsfr": 106,
            "employees": 31000, "branches": 1450, "customers": 18, "digital_txn_share": 91,
            "green_financing": 5200, "women_workforce_pct": 31,
        },
        "growth": {"total_income": 24, "nii": 23, "other_income": 26, "operating_expenses": 21,
                   "operating_profit": 25, "pat": 26, "total_assets": 22, "net_worth": 17,
                   "gross_advances": 26, "deposits": 18, "casa_deposits": 15,
                   "gnpa": 18, "nnpa": 20, "slippages": 22, "recoveries": 15,
                   "employees": 16, "branches": 12, "customers": 22, "green_financing": 40},
        "drift": {"nim": -0.06, "nnpa_ratio": 0.03, "pcr": -1.5, "cet1_ratio": -0.5,
                  "tier1_ratio": -0.5, "crar": -0.5, "lcr": -3, "nsfr": -2,
                  "digital_txn_share": 2, "women_workforce_pct": 1.2},
    },
    "HMGR": {
        "name": "Himgiri Bank", "segment": "private",
        "base": {
            "total_income": 34000, "nii": 14800, "other_income": 4900, "nim": 3.70,
            "operating_expenses": 8900, "operating_profit": 10800, "pat": 6100,
            "total_assets": 415000, "net_worth": 48500, "gross_advances": 252000,
            "gnpa": 4300, "nnpa": 980, "nnpa_ratio": 0.39, "pcr": 82,
            "slippages": 2400, "recoveries": 2100,
            "cet1_ratio": 16.8, "tier1_ratio": 17.3, "crar": 18.9,
            "deposits": 332000, "casa_deposits": 156000, "lcr": 152, "nsfr": 132,
            "employees": 47000, "branches": 2900, "customers": 32, "digital_txn_share": 78,
            "green_financing": 11500, "women_workforce_pct": 29,
        },
        "growth": {"total_income": 10, "nii": 10, "other_income": 9, "operating_expenses": 9,
                   "operating_profit": 11, "pat": 12, "total_assets": 10, "net_worth": 11,
                   "gross_advances": 11, "deposits": 11, "casa_deposits": 10,
                   "gnpa": -3, "nnpa": -6, "slippages": -2, "recoveries": 4,
                   "employees": 3, "branches": 2, "customers": 6, "green_financing": 22},
        "drift": {"nim": 0.02, "nnpa_ratio": -0.04, "pcr": 0.8, "cet1_ratio": 0.1,
                  "tier1_ratio": 0.1, "crar": 0.0, "lcr": 1, "nsfr": 1,
                  "digital_txn_share": 4, "women_workforce_pct": 0.8},
    },
}

# Plausible annual-report page placement per KPI category, for lineage demo.
CATEGORY_PAGES = {"financial": 18, "asset_quality": 64, "capital": 92,
                  "liquidity": 71, "operations": 33, "esg": 121}


def _year_value(base: float, code: str, profile: dict, year_idx: int) -> float:
    growth = profile["growth"].get(code)
    if growth is not None:
        return round(base * (1 + growth / 100) ** year_idx, 2)
    drift = profile["drift"].get(code, 0.0)
    return round(base + drift * year_idx, 2)


def seed_demo(db: Session) -> bool:
    """Idempotent: no-op when demo banks already exist."""
    if db.execute(select(Bank).where(Bank.is_demo)).first():
        return False

    from app.modules.kpi_warehouse.registry import KPI_REGISTRY

    for code, profile in PROFILES.items():
        bank = Bank(code=code, name=profile["name"],
                    segment=profile.get("segment", "universal"), is_demo=True)
        db.add(bank)
        db.flush()

        prior: dict[str, float] = {}
        for year_idx, fy in enumerate(FISCAL_YEARS):
            doc = Document(
                bank_id=bank.id, doc_type="annual_report", fiscal_year=fy,
                title=f"{profile['name']} Integrated Annual Report {fy} (Synthetic Demo)",
                pages=324, status="processed",
            )
            db.add(doc)
            db.flush()

            current = {c: _year_value(v, c, profile, year_idx)
                       for c, v in profile["base"].items()}
            for kpi_code, value in current.items():
                category = KPI_REGISTRY[kpi_code].category
                warehouse.upsert_value(
                    db, bank_id=bank.id, fy=fy, kpi_code=kpi_code, value=value,
                    document_id=doc.id, page=CATEGORY_PAGES.get(category, 18),
                    extraction_method="manual", confidence=1.0,
                    source_text="Synthetic demo figure (seed dataset)",
                )
            db.flush()

            for d in derive_missing(dict(current), prior):
                warehouse.upsert_value(
                    db, bank_id=bank.id, fy=fy, kpi_code=d.kpi_code, value=d.value,
                    document_id=doc.id, page=None, extraction_method="derived",
                    confidence=0.99, source_text=f"Derived: {d.expression}",
                )
                current[d.kpi_code] = d.value
            db.flush()

            validate_bank_year(db, bank.id, fy, dict(current), dict(prior))
            prior = current

    db.add(AuditLog(action="demo_seeded", detail=f"banks={list(PROFILES)} years={FISCAL_YEARS}"))
    db.commit()
    return True
