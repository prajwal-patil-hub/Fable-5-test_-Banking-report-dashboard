"""Roster of Indian scheduled commercial banks — institutions only.

Seeds bank ENTITIES (name, code, cohort segment) so every major Indian bank
is selectable out of the box. Deliberately seeds NO figures: a real bank's
numbers enter the warehouse only through document ingestion (upload its
annual report), never through fabrication — that is a product principle.

Coverage: public-sector banks, major private-sector banks, small finance
banks, and the large foreign banks operating in India. Regional rural banks
and cooperative banks are out of scope for v1. Banks not listed here can be
added from the dashboard (POST /api/banks).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Bank

# (code, name, segment)
INDIAN_BANKS: list[tuple[str, str, str]] = [
    # Public sector (PSU)
    ("SBIN", "State Bank of India", "public"),
    ("PNB", "Punjab National Bank", "public"),
    ("BOB", "Bank of Baroda", "public"),
    ("CANBK", "Canara Bank", "public"),
    ("UNBK", "Union Bank of India", "public"),
    ("BOI", "Bank of India", "public"),
    ("INDB", "Indian Bank", "public"),
    ("CBOI", "Central Bank of India", "public"),
    ("IOB", "Indian Overseas Bank", "public"),
    ("UCO", "UCO Bank", "public"),
    ("BOM", "Bank of Maharashtra", "public"),
    ("PSB", "Punjab & Sind Bank", "public"),
    # Private sector
    ("HDFCB", "HDFC Bank", "private"),
    ("ICICI", "ICICI Bank", "private"),
    ("AXIS", "Axis Bank", "private"),
    ("KOTAK", "Kotak Mahindra Bank", "private"),
    ("IIB", "IndusInd Bank", "private"),
    ("YESB", "Yes Bank", "private"),
    ("IDFCFB", "IDFC FIRST Bank", "private"),
    ("FEDB", "Federal Bank", "private"),
    ("SIB", "South Indian Bank", "private"),
    ("KVB", "Karur Vysya Bank", "private"),
    ("CUB", "City Union Bank", "private"),
    ("RBL", "RBL Bank", "private"),
    ("BDNB", "Bandhan Bank", "private"),
    ("KTKB", "Karnataka Bank", "private"),
    ("DCB", "DCB Bank", "private"),
    ("CSB", "CSB Bank", "private"),
    ("TMB", "Tamilnad Mercantile Bank", "private"),
    ("JKB", "Jammu & Kashmir Bank", "private"),
    ("DHLB", "Dhanlaxmi Bank", "private"),
    # Small finance banks
    ("AUSFB", "AU Small Finance Bank", "sfb"),
    ("EQSFB", "Equitas Small Finance Bank", "sfb"),
    ("UJSFB", "Ujjivan Small Finance Bank", "sfb"),
    ("JANA", "Jana Small Finance Bank", "sfb"),
    ("SURSFB", "Suryoday Small Finance Bank", "sfb"),
    ("ESAF", "ESAF Small Finance Bank", "sfb"),
    ("UTKSFB", "Utkarsh Small Finance Bank", "sfb"),
    ("CAPSFB", "Capital Small Finance Bank", "sfb"),
    # Foreign banks in India
    ("HSBCIN", "HSBC India", "foreign"),
    ("SCBIN", "Standard Chartered Bank India", "foreign"),
    ("CITIIN", "Citibank N.A. India", "foreign"),
    ("DBIN", "Deutsche Bank India", "foreign"),
    ("DBSIN", "DBS Bank India", "foreign"),
]


def seed_indian_roster(db: Session) -> int:
    """Idempotent: inserts only banks whose code is not already present.
    Returns the number of banks added."""
    existing = set(db.execute(select(Bank.code)).scalars().all())
    added = 0
    for code, name, segment in INDIAN_BANKS:
        if code in existing:
            continue
        db.add(Bank(code=code, name=name, segment=segment, is_demo=False))
        added += 1
    if added:
        db.add(AuditLog(action="roster_seeded", detail=f"indian_banks_added={added}"))
        db.commit()
    return added
