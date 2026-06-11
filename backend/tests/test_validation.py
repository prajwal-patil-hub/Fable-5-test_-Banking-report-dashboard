from app.modules.validation.engine import run_rules


def _outcome(outcomes, code):
    return next(o for o in outcomes if o.rule.code == code)


def test_nnpa_exceeding_gnpa_fails():
    outcomes = run_rules({"gnpa": 100.0, "nnpa": 150.0})
    assert _outcome(outcomes, "nnpa_le_gnpa").status == "failed"


def test_capital_stack_ordering():
    ok = run_rules({"cet1_ratio": 13.0, "tier1_ratio": 13.5, "crar": 15.0})
    assert _outcome(ok, "capital_stack_order").status == "passed"
    bad = run_rules({"cet1_ratio": 14.0, "tier1_ratio": 13.5, "crar": 15.0})
    assert _outcome(bad, "capital_stack_order").status == "failed"


def test_roe_consistency_flags_divergence():
    bad = run_rules({"roe": 20.0, "pat": 1000.0, "net_worth": 8000.0})  # implied 12.5%
    assert _outcome(bad, "roe_consistency").status == "failed"
    ok = run_rules({"roe": 12.6, "pat": 1000.0, "net_worth": 8000.0})
    assert _outcome(ok, "roe_consistency").status == "passed"


def test_yoy_jump_detection():
    outcomes = run_rules({"pat": 250.0}, {"pat": 100.0})
    assert _outcome(outcomes, "yoy_plausibility").status == "failed"
    outcomes = run_rules({"pat": 110.0}, {"pat": 100.0})
    assert _outcome(outcomes, "yoy_plausibility").status == "passed"


def test_rules_skip_when_inputs_missing():
    outcomes = run_rules({})
    # structural rules must not fail on absent data (not-applicable == passed)
    assert _outcome(outcomes, "nnpa_le_gnpa").status == "passed"
    assert _outcome(outcomes, "capital_stack_order").status == "passed"
    # but completeness rule should flag the empty period
    assert _outcome(outcomes, "headline_completeness").status == "failed"
