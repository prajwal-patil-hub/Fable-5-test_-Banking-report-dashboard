from app.modules.document_intelligence.fiscal import fy_mismatch, infer_fiscal_years


def test_infers_common_indian_formats():
    text = ("Integrated Annual Report 2024-25. "
            "Results for the year ended March 31, 2025 were strong. "
            "FY2025 highlights follow; FY2024 comparatives are restated.")
    inferred = infer_fiscal_years(text)
    assert inferred[0] == "FY2025"  # most frequent
    assert "FY2024" in inferred


def test_infers_short_range_and_fy_short_forms():
    assert "FY2026" in infer_fiscal_years("Annual Report 2025-26")
    assert "FY2025" in infer_fiscal_years("Performance in FY25 was resilient")


def test_mismatch_flags_wrong_declared_year():
    text = "Annual Report 2024-25 for the year ended 31 March 2025"
    assert fy_mismatch("FY2020", text) is not None
    assert fy_mismatch("FY2025", text) is None


def test_mismatch_tolerates_comparative_years():
    # declared year present alongside prior-year comparatives: consistent
    text = "FY2025 results with FY2024 and FY2023 comparatives"
    assert fy_mismatch("FY2025", text) is None


def test_no_inference_means_no_flag():
    assert fy_mismatch("FY2025", "A document with no period references.") is None
