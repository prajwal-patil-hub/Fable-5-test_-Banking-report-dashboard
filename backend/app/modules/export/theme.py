"""Old Money design tokens shared by every export format, mirroring the
frontend Tailwind theme so deliverables and dashboard are one visual system."""

INK = "1A120B"
INK_2 = "2C1E16"
CARD = "36251D"
GOLD = "C7A56A"
BRONZE = "9C7B4F"
HIGHLIGHT = "D8C49A"
SUCCESS = "5E8B6F"
WARNING = "B58A42"
RISK = "7A3E3E"
TEXT_PRIMARY = "F3EEE7"
TEXT_SECONDARY = "CFC3B0"
BORDER = "4B382F"

CATEGORY_LABELS = {
    "financial": "Financial Performance",
    "asset_quality": "Asset Quality",
    "capital": "Capital Adequacy",
    "liquidity": "Liquidity & Funding",
    "operations": "Operations",
    "esg": "ESG",
}

MODULE_LABELS = {**CATEGORY_LABELS, "benchmarking": "Peer Benchmarking"}


def format_value(value: float | None, unit: str) -> str:
    if value is None:
        return "—"
    if unit == "percent":
        return f"{value:,.2f}%"
    if unit == "inr_crore":
        return f"₹{value:,.0f} Cr"
    return f"{value:,.0f}"
