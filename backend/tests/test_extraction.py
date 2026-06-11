from app.modules.document_intelligence.extractors import (
    Candidate, PageContent, RuleBasedExtractor, TableExtractor, resolve,
)
from app.modules.document_intelligence.normalize import normalize_value, parse_number


def test_parse_number_indian_grouping_and_parens():
    assert parse_number("1,23,456.78") == 123456.78
    assert parse_number("(2,500)") == -2500.0
    assert parse_number("abc") is None


def test_normalize_units():
    assert normalize_value("12,345", "crore", "inr_crore") == 12345.0
    assert normalize_value("1.2", "billion", "inr_crore") == 120.0
    assert normalize_value("3.95", "%", "percent") == 3.95
    assert normalize_value("250", "bps", "percent") == 2.5
    # incompatible unit must be rejected, not coerced
    assert normalize_value("3.95", "%", "inr_crore") is None


def test_rule_based_extractor_reads_labeled_lines():
    page = PageContent(number=4, text=(
        "Net Interest Income of 18,420 crore grew strongly.\n"
        "Net Interest Margin was 3.95% for the year.\n"
        "The Provision Coverage Ratio improved to 77.2%.\n"
    ), tables=[])
    found = {c.kpi_code: c for c in RuleBasedExtractor().extract([page])}
    assert found["nii"].value == 18420.0
    assert found["nim"].value == 3.95
    assert found["pcr"].value == 77.2
    assert all(c.page == 4 and c.method == "rule_based" for c in found.values())


def test_table_extractor_takes_latest_column():
    page = PageContent(number=9, text="", tables=[[
        ["Particulars", "FY2024", "FY2025"],
        ["Gross NPA", "5,900", "5,400"],
        ["CET1 Ratio", "13.9%", "14.2%"],
    ]])
    found = {c.kpi_code: c for c in TableExtractor().extract([page])}
    assert found["gnpa"].value == 5400.0  # current-year column
    assert found["cet1_ratio"].value == 14.2
    assert found["gnpa"].confidence > 0.8


def test_resolution_prefers_confidence_then_page():
    candidates = [
        Candidate("pat", 100.0, page=200, method="rule_based", confidence=0.7, source_text="a"),
        Candidate("pat", 105.0, page=10, method="table", confidence=0.9, source_text="b"),
        Candidate("pat", 101.0, page=5, method="table", confidence=0.9, source_text="c"),
    ]
    best = resolve(candidates)
    assert best["pat"].value == 101.0  # highest confidence, earliest page
