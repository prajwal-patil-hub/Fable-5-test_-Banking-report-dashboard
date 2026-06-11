from app.modules.kpi_warehouse.calculation import derive_missing, yoy_delta
from app.modules.kpi_warehouse.registry import KPI_REGISTRY, alias_index, benchmarkable_kpis


def test_registry_integrity():
    assert len(KPI_REGISTRY) >= 30
    for kpi in KPI_REGISTRY.values():
        assert kpi.category in {"financial", "asset_quality", "capital",
                                "liquidity", "operations", "esg"}
        assert kpi.unit in {"inr_crore", "percent", "count", "ratio"}
        assert kpi.direction in {"higher_is_better", "lower_is_better", "neutral"}
        if kpi.formula:
            for dep in kpi.formula.inputs + kpi.formula.prior_inputs:
                assert dep in KPI_REGISTRY, f"{kpi.code} formula depends on unknown {dep}"


def test_alias_index_prefers_longest():
    aliases = alias_index()
    # 'gross npa ratio' must come before 'gross npa' so ratio lines map correctly
    codes_in_order = [c for a, c in aliases if a in ("gross npa ratio", "gross npa")]
    assert codes_in_order == ["gnpa_ratio", "gnpa"]


def test_benchmarkable_subset():
    codes = {k.code for k in benchmarkable_kpis()}
    assert {"roe", "gnpa_ratio", "crar", "casa_ratio"} <= codes


def test_derive_ratios():
    current = {"pat": 1000.0, "total_assets": 80000.0, "net_worth": 8000.0,
               "gnpa": 500.0, "gross_advances": 50000.0,
               "casa_deposits": 4000.0, "deposits": 10000.0,
               "operating_expenses": 900.0, "nii": 1500.0, "other_income": 500.0}
    derived = {d.kpi_code: d.value for d in derive_missing(current)}
    assert derived["roa"] == 1.25
    assert derived["roe"] == 12.5
    assert derived["gnpa_ratio"] == 1.0
    assert derived["casa_ratio"] == 40.0
    assert derived["cost_to_income"] == 45.0


def test_derive_respects_reported_values():
    current = {"pat": 1000.0, "net_worth": 8000.0, "roe": 13.1}  # reported wins
    derived = {d.kpi_code for d in derive_missing(current)}
    assert "roe" not in derived


def test_yoy_growth_needs_prior():
    current = {"deposits": 11000.0}
    assert not [d for d in derive_missing(current) if d.kpi_code == "deposit_growth"]
    derived = {d.kpi_code: d.value for d in derive_missing(current, {"deposits": 10000.0})}
    assert derived["deposit_growth"] == 10.0


def test_yoy_delta():
    assert yoy_delta(110.0, 100.0) == (10.0, 10.0)
    assert yoy_delta(None, 100.0) == (None, None)
    assert yoy_delta(100.0, 0.0) == (100.0, None)
