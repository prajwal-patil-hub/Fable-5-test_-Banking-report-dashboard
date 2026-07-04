"""Fiscal-year inference from document text.

Indian annual reports declare their period many ways — "FY2025", "FY 2024-25",
"2024-25", "Annual Report 2024-2025", "year ended March 31, 2025". The
uploader declares a fiscal year at ingestion; this module infers the years a
document actually mentions so validation can flag a mismatch (wrong file
uploaded, or wrong FY selected) instead of silently filing facts under the
wrong period. Indian FY convention: the year ending March 2025 is FY2025.
"""
from __future__ import annotations

import re
from collections import Counter

_PATTERNS = [
    # FY2025 / FY 2025 / FY25
    (re.compile(r"\bFY\s?(\d{4})\b", re.IGNORECASE), lambda m: int(m.group(1))),
    (re.compile(r"\bFY\s?(\d{2})\b", re.IGNORECASE), lambda m: 2000 + int(m.group(1))),
    # 2024-25 / 2024-2025 / 2024–25 (range ends in the FY label year)
    (re.compile(r"\b(\d{4})\s*[-–]\s*(\d{2,4})\b"),
     lambda m: int(m.group(2)) if len(m.group(2)) == 4 else (int(m.group(1)) // 100) * 100 + int(m.group(2))),
    # year ended March 31, 2025 / 31 March 2025 / 31st March, 2025
    (re.compile(r"March\s+31\s*,?\s*(\d{4})", re.IGNORECASE), lambda m: int(m.group(1))),
    (re.compile(r"31(?:st)?\s+March\s*,?\s*(\d{4})", re.IGNORECASE), lambda m: int(m.group(1))),
]


def infer_fiscal_years(text: str) -> list[str]:
    """Fiscal years mentioned in the text, most frequent first."""
    counts: Counter[int] = Counter()
    for pattern, to_year in _PATTERNS:
        for m in pattern.finditer(text):
            year = to_year(m)
            if year is not None and 1990 <= year <= 2100:
                counts[year] += 1
    return [f"FY{y}" for y, _ in counts.most_common()]


def fy_mismatch(declared_fy: str, text: str) -> str | None:
    """Failure message when the declared FY is absent from the document's own
    period references; None when consistent or when nothing could be inferred.

    A report legitimately references its prior year(s) for comparatives, so
    the declared year only has to APPEAR among the inferred years — it does
    not have to be the most frequent.
    """
    inferred = infer_fiscal_years(text)
    if not inferred or declared_fy in inferred:
        return None
    return (f"Document was filed under {declared_fy} but its text references "
            f"{', '.join(inferred[:3])} — verify the correct fiscal year was selected.")
