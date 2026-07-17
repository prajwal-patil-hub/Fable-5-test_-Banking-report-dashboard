"""Statement-denomination handling and magnitude plausibility rails.

Root cause under test: Indian banks denominate statements in ₹ lakh or
₹ thousands with the scale stated only in a caption. Reading those bare
figures as crore inflates them 100×–10,000× — the 'astronomically higher
bank' bug. Fix: page-level scale hints + RBI-grounded plausibility rules.
"""
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table

from app.modules.document_intelligence.extractors import (
    DEFAULT_EXTRACTORS, PageContent, RuleBasedExtractor, resolve,
)
from app.modules.document_intelligence.normalize import detect_scale_hint, normalize_value
from app.modules.document_intelligence.pipeline import read_pdf
from app.modules.validation.engine import run_rules


def _outcome(outcomes, code):
    return next(o for o in outcomes if o.rule.code == code)


# ------------------------------------------------------------ hint detection

def test_detect_scale_hint_variants():
    assert detect_scale_hint("(₹ in lakh)") == 0.01
    assert detect_scale_hint("Rs. in Lakhs, except per share data") == 0.01
    assert detect_scale_hint("Amount in ₹ million") == 0.1
    assert detect_scale_hint("(₹ in '000)") == 0.0001
    assert detect_scale_hint("Rupees in thousand") == 0.0001
    assert detect_scale_hint("(₹ in crore, except ratios)") == 1.0
    assert detect_scale_hint("no denomination stated here") is None


def test_bare_numbers_respect_hint_but_explicit_units_override():
    # bare number on a lakh-denominated page: ÷100
    assert normalize_value("4,86,00,000", "", "inr_crore", scale_hint=0.01) == 486000.0
    # explicit "crore" beside the figure overrides the page hint
    assert normalize_value("1,234", "crore", "inr_crore", scale_hint=0.01) == 1234.0
    # ratios are never scaled by denomination
    assert normalize_value("14.2", "%", "percent", scale_hint=0.01) == 14.2


def test_rule_based_extractor_uses_page_hint():
    page = PageContent(
        number=3,
        text="Profit After Tax stood at 7,65,000 for the year.",
        tables=[], scale_hint=0.01)  # lakh-denominated page
    found = {c.kpi_code: c for c in RuleBasedExtractor().extract([page])}
    assert found["pat"].value == 7650.0  # ₹7,65,000 lakh = ₹7,650 crore


# ----------------------------------------------------------------- PDF round trip

def _lakh_pdf() -> bytes:
    buf = io.BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    doc.build([
        Paragraph("Statement of Financial Position", styles["Title"]),
        Paragraph("(₹ in lakh)", styles["Italic"]),
        Table([
            ["Particulars", "FY2025"],
            ["Total Deposits", "4,86,00,000"],
            ["Gross Advances", "4,12,00,000"],
            ["Profit After Tax", "7,65,000"],
        ]),
    ])
    return buf.getvalue()


def test_lakh_denominated_pdf_lands_in_crore():
    pages = read_pdf(_lakh_pdf())
    assert pages[0].scale_hint == 0.01
    candidates = []
    for extractor in DEFAULT_EXTRACTORS:
        candidates.extend(extractor.extract(pages))
    resolved = resolve(candidates)
    assert resolved["deposits"].value == 486000.0   # not 4,86,00,000 "crore"
    assert resolved["gross_advances"].value == 412000.0
    assert resolved["pat"].value == 7650.0


def test_crore_denominated_pdf_unchanged():
    # the stress fixture declares "(₹ in crore...)" — hint 1.0, values as-is
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import make_stress_pdf
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        make_stress_pdf.build(f.name)
        pages = read_pdf(Path(f.name).read_bytes())
    assert pages[0].scale_hint == 1.0


# ------------------------------------------------------- plausibility rails

def test_money_magnitude_rail_catches_scale_blowups():
    # a lakh statement read as crore: deposits 100× too big
    outcomes = run_rules({"deposits": 48_600_000.0})
    o = _outcome(outcomes, "money_magnitude_plausibility")
    assert o.status == "failed" and o.rule.severity == "error"
    assert "lakh" in o.message  # message explains the likely denomination cause

    assert _outcome(run_rules({"deposits": 486000.0}),
                    "money_magnitude_plausibility").status == "passed"


def test_ratio_plausibility_rails():
    bad = run_rules({"nim": 385.0, "gnpa_ratio": 131.0})  # % misread magnitudes
    assert _outcome(bad, "plausible_nim").status == "failed"
    assert _outcome(bad, "plausible_gnpa_ratio").status == "failed"

    # genuine extremes stay unflagged (SFB-high NIM, stressed-bank GNPA)
    ok = run_rules({"nim": 9.8, "gnpa_ratio": 27.0, "roe": -45.0})
    assert _outcome(ok, "plausible_nim").status == "passed"
    assert _outcome(ok, "plausible_gnpa_ratio").status == "passed"
    assert _outcome(ok, "plausible_roe").status == "passed"
