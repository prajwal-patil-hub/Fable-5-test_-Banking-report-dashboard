from sqlalchemy import select

from app.core.config import settings
from app.models import Bank
from app.modules.kpi_warehouse import service as warehouse


def _bank(db):
    return db.execute(select(Bank).where(Bank.code == "MRDN")).scalar_one()


def test_usd_converts_only_monetary_kpis(seeded_db):
    bank = _bank(seeded_db)
    inr = {k["kpi_code"]: k for k in warehouse.kpi_payload(seeded_db, bank, "FY2025")["kpis"]}
    usd_payload = warehouse.kpi_payload(seeded_db, bank, "FY2025", currency="usd")
    usd = {k["kpi_code"]: k for k in usd_payload["kpis"]}

    assert usd_payload["currency"] == "usd"

    # monetary: ₹ crore → $ mn at 10/rate
    expected = round(inr["pat"]["value"] * 10 / settings.usd_inr_rate, 1)
    assert usd["pat"]["unit"] == "usd_mn" and usd["pat"]["value"] == expected
    # yoy absolute converted; percent change invariant
    assert usd["pat"]["yoy_change"] != inr["pat"]["yoy_change"]
    assert usd["pat"]["yoy_change_pct"] == inr["pat"]["yoy_change_pct"]
    # ratios and counts untouched
    assert usd["roe"] == inr["roe"]
    assert usd["branches"] == inr["branches"]


def test_history_currency(seeded_db):
    bank = _bank(seeded_db)
    inr = warehouse.history(seeded_db, bank.id, "deposits")
    usd = warehouse.history(seeded_db, bank.id, "deposits", currency="usd")
    assert usd["unit"] == "usd_mn"
    for p_inr, p_usd in zip(inr["series"], usd["series"]):
        assert p_usd["value"] == round(p_inr["value"] * 10 / settings.usd_inr_rate, 1)
    # percent KPI history is currency-invariant
    assert warehouse.history(seeded_db, bank.id, "roe", currency="usd")["unit"] == "percent"


def test_default_payload_unchanged(seeded_db):
    bank = _bank(seeded_db)
    payload = warehouse.kpi_payload(seeded_db, bank, "FY2025")
    assert payload["currency"] == "inr"
    assert all(k["unit"] != "usd_mn" for k in payload["kpis"])
