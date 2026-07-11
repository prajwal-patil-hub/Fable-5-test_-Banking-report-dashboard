"""Indian bank roster, bank self-registration, and RBI regulatory floors."""
from app.modules.validation.engine import run_rules
from app.seeds.roster import INDIAN_BANKS, seed_indian_roster


def _outcome(outcomes, code):
    return next(o for o in outcomes if o.rule.code == code)


# ------------------------------------------------------------------ roster

def test_roster_covers_indian_banking_landscape(db):
    added = seed_indian_roster(db)
    assert added == len(INDIAN_BANKS) >= 40
    assert seed_indian_roster(db) == 0  # idempotent

    segments = {s for _, _, s in INDIAN_BANKS}
    assert segments == {"public", "private", "sfb", "foreign"}
    names = {n for _, n, _ in INDIAN_BANKS}
    assert {"State Bank of India", "HDFC Bank", "ICICI Bank",
            "AU Small Finance Bank", "HSBC India"} <= names


def test_roster_banks_have_no_fabricated_data(client):
    banks = client.get("/api/banks").json()["banks"]
    real = [b for b in banks if not b["is_demo"]]
    assert len(real) >= 40
    assert all(not b["has_data"] for b in real)  # figures only via upload
    sbi = next(b for b in real if b["code"] == "SBIN")
    assert sbi["segment"] == "public"
    assert client.get(f"/api/banks/{sbi['id']}/years").json()["fiscal_years"] == []


# --------------------------------------------------------- self-registration

def test_create_bank_endpoint(client):
    resp = client.post("/api/banks", json={"name": "Vindhya Cooperative Bank",
                                           "segment": "private"})
    assert resp.status_code == 201
    created = resp.json()
    assert created["code"] == "VCB" and created["has_data"] is False

    # duplicate name rejected; bad segment rejected
    assert client.post("/api/banks", json={"name": "Vindhya Cooperative Bank",
                                           "segment": "private"}).status_code == 409
    assert client.post("/api/banks", json={"name": "X Bank",
                                           "segment": "cosmic"}).status_code == 422

    # code collision auto-suffixes
    resp2 = client.post("/api/banks", json={"name": "Vindhya Capital Bank",
                                            "segment": "private"})
    assert resp2.status_code == 201 and resp2.json()["code"] == "VCB2"

    banks = client.get("/api/banks").json()["banks"]
    assert any(b["name"] == "Vindhya Cooperative Bank" for b in banks)


# ------------------------------------------------------- RBI regulatory floors

def test_rbi_capital_floors():
    breached = run_rules({"cet1_ratio": 7.4, "tier1_ratio": 9.0, "crar": 10.9})
    assert _outcome(breached, "cet1_regulatory_floor").status == "failed"
    assert _outcome(breached, "tier1_regulatory_floor").status == "failed"
    assert _outcome(breached, "crar_regulatory_floor").status == "failed"
    assert "RBI minimum" in _outcome(breached, "cet1_regulatory_floor").message

    compliant = run_rules({"cet1_ratio": 8.0, "tier1_ratio": 9.5, "crar": 11.5})
    for code in ("cet1_regulatory_floor", "tier1_regulatory_floor", "crar_regulatory_floor"):
        assert _outcome(compliant, code).status == "passed"


def test_rbi_liquidity_floors():
    breached = run_rules({"lcr": 96.0, "nsfr": 99.0})
    assert _outcome(breached, "lcr_regulatory_floor").status == "failed"
    assert _outcome(breached, "nsfr_regulatory_floor").status == "failed"

    ok = run_rules({"lcr": 100.0, "nsfr": 100.0})
    assert _outcome(ok, "lcr_regulatory_floor").status == "passed"
    assert _outcome(ok, "nsfr_regulatory_floor").status == "passed"
