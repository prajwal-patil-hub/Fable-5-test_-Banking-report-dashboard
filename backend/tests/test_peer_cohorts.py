from app.modules.benchmarking.engine import benchmark_kpi, benchmark_summary


def test_segment_filters_peer_universe(seeded_db):
    unfiltered = benchmark_kpi(seeded_db, "roe", "FY2025")
    assert len(unfiltered["peers"]) == 4
    assert unfiltered["segment"] is None

    private = benchmark_kpi(seeded_db, "roe", "FY2025", segment="private")
    assert len(private["peers"]) == 3  # BHNB (public PSU) excluded
    assert {p["bank_code"] for p in private["peers"]} == {"SVRN", "NLND", "HMGR"}
    assert private["segment"] == "private"

    public = benchmark_kpi(seeded_db, "roe", "FY2025", segment="public")
    assert [p["bank_code"] for p in public["peers"]] == ["BHNB"]
    assert public["peers"][0]["rank"] == 1 and public["peers"][0]["percentile"] == 100.0


def test_ranks_recomputed_within_cohort(seeded_db):
    # A bank's rank inside its cohort must reflect cohort membership only
    unfiltered = benchmark_kpi(seeded_db, "gnpa_ratio", "FY2025")
    private = benchmark_kpi(seeded_db, "gnpa_ratio", "FY2025", segment="private")
    assert [p["rank"] for p in private["peers"]] == [1, 2, 3]
    assert len(private["peers"]) < len(unfiltered["peers"])


def test_summary_accepts_segment(seeded_db):
    summary = benchmark_summary(seeded_db, "FY2025", segment="private")
    assert summary["segment"] == "private"
    assert all(len(k["peers"]) == 3 for k in summary["kpis"])
