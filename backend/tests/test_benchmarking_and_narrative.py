from sqlalchemy import select

from app.models import Bank
from app.modules.benchmarking.engine import bank_position, benchmark_kpi, benchmark_summary
from app.modules.narrative.engine import build_narrative


def _bank(db, code):
    return db.execute(select(Bank).where(Bank.code == code)).scalar_one()


def test_benchmark_ranks_respect_direction(seeded_db):
    roe = benchmark_kpi(seeded_db, "roe", "FY2025")
    assert len(roe["peers"]) == 4
    values = [p["value"] for p in roe["peers"]]
    assert values == sorted(values, reverse=True)  # higher_is_better: best first
    assert roe["peers"][0]["rank"] == 1
    assert roe["peers"][0]["percentile"] == 100.0

    gnpa = benchmark_kpi(seeded_db, "gnpa_ratio", "FY2025")
    values = [p["value"] for p in gnpa["peers"]]
    assert values == sorted(values)  # lower_is_better: lowest ranked first
    assert gnpa["peers"][0]["rank"] == 1


def test_benchmark_summary_covers_benchmarkable_kpis(seeded_db):
    summary = benchmark_summary(seeded_db, "FY2025")
    codes = {k["kpi_code"] for k in summary["kpis"]}
    assert {"roe", "roa", "nim", "cost_to_income", "gnpa_ratio", "crar", "casa_ratio"} <= codes


def test_bank_position(seeded_db):
    mrdn = _bank(seeded_db, "MRDN")
    pos = bank_position(seeded_db, mrdn.id, "roe", "FY2025")
    assert pos is not None and pos["peer_count"] == 4
    assert 1 <= pos["rank"] <= 4


def test_narrative_structure_and_grounding(seeded_db):
    mrdn = _bank(seeded_db, "MRDN")
    narrative = build_narrative(seeded_db, mrdn, "FY2025")
    modules = [s["module"] for s in narrative["sections"]]
    assert modules == ["financial", "asset_quality", "capital",
                       "liquidity", "operations", "benchmarking"]
    assert 3 <= len(narrative["executive_summary"]) <= 6
    for section in narrative["sections"]:
        assert section["headline"]
        assert section["commentary"]


def test_narrative_recommends_on_weakness(seeded_db):
    # Crestline: PCR < 70 and thin capital must surface recommendations
    crst = _bank(seeded_db, "CRST")
    narrative = build_narrative(seeded_db, crst, "FY2025")
    aq = next(s for s in narrative["sections"] if s["module"] == "asset_quality")
    assert any("70%" in r for r in aq["recommendations"])
