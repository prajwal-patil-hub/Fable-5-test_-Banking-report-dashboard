"""Numeric and unit normalisation for extracted banking figures.

Everything in the warehouse is stored in canonical units:
₹ crore for money, percent for ratios, plain numbers for counts.
Indian reports mix lakh/crore/million/billion and Indian digit grouping
(1,23,456.78) — all are normalised here, in one place.
"""
from __future__ import annotations

import re

# number with optional Indian/Western grouping and decimals, optional parens for negatives
_NUMBER = r"\(?-?[\d,]+(?:\.\d+)?\)?"
_UNIT = r"(?:%|per\s?cent|percent|bps|crore|crores|cr\.?|lakh|lakhs|million|mn|billion|bn)?"

NUMBER_RE = re.compile(rf"({_NUMBER})\s*({_UNIT})", re.IGNORECASE)

_SCALE_TO_CRORE = {
    "crore": 1.0, "crores": 1.0, "cr": 1.0, "cr.": 1.0,
    "lakh": 0.01, "lakhs": 0.01,
    "million": 0.1, "mn": 0.1,
    "billion": 100.0, "bn": 100.0,
}


def parse_number(token: str) -> float | None:
    token = token.strip()
    negative = token.startswith("(") and token.endswith(")")
    token = token.strip("()").replace(",", "")
    try:
        value = float(token)
    except ValueError:
        return None
    return -value if negative else value


def normalize_value(raw_number: str, raw_unit: str, target_unit: str) -> float | None:
    """Convert an extracted (number, unit-word) pair into the KPI's canonical unit.

    Returns None when the source unit is incompatible with the target (e.g. a
    percentage found where a ₹ amount is expected) — better to drop a candidate
    than to store a silently wrong magnitude.
    """
    value = parse_number(raw_number)
    if value is None:
        return None
    unit = (raw_unit or "").lower().strip().replace(" ", "")  # "per cent" -> "percent"

    if target_unit == "percent":
        if unit == "bps":
            return round(value / 100, 4)
        if unit in ("%", "percent", ""):
            return value
        return None
    if target_unit == "inr_crore":
        if unit in ("%", "percent", "bps"):
            return None
        scale = _SCALE_TO_CRORE.get(unit, 1.0)  # bare numbers in annual reports default to crore
        return round(value * scale, 2)
    if target_unit in ("count", "ratio"):
        if unit in ("%", "percent", "bps"):
            return None
        return value
    return value
