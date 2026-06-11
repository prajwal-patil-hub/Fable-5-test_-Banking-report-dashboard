"""End-to-end: API surface against a seeded app, plus the full
document-ingestion round trip using a synthetic annual-report PDF."""
import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@pytest.fixture()
def client(db, monkeypatch):
    from app import main
    from app.core import db as core_db

    monkeypatch.setattr(core_db, "SessionLocal", lambda: db)

    def override_get_db():
        yield db

    main.app.dependency_overrides[core_db.get_db] = override_get_db

    from app.seeds.demo import seed_demo
    seed_demo(db)

    with TestClient(main.app, raise_server_exceptions=True) as c:
        yield c
    main.app.dependency_overrides.clear()


def test_banks_years_kpis(client):
    banks = client.get("/api/banks").json()["banks"]
    assert len(banks) >= 4 and all(b["is_demo"] for b in banks)

    bank_id = banks[0]["id"]
    years = client.get(f"/api/banks/{bank_id}/years").json()["fiscal_years"]
    assert years == ["FY2023", "FY2024", "FY2025"]

    payload = client.get(f"/api/banks/{bank_id}/kpis", params={"fiscal_year": "FY2025"}).json()
    kpis = {k["kpi_code"]: k for k in payload["kpis"]}
    assert {"roe", "gnpa_ratio", "crar", "casa_ratio"} <= set(kpis)
    roe = kpis["roe"]
    assert roe["lineage"]["extraction_method"] in ("derived", "manual")
    assert roe["yoy_change"] is not None  # FY2024 exists
    assert roe["validation_status"] in ("passed", "warning", "failed")


def test_history_benchmarking_narrative_validations(client):
    bank_id = client.get("/api/banks").json()["banks"][0]["id"]

    hist = client.get(f"/api/banks/{bank_id}/kpis/pat/history").json()
    assert [p["fiscal_year"] for p in hist["series"]] == ["FY2023", "FY2024", "FY2025"]

    bench = client.get("/api/benchmarking",
                       params={"kpi_code": "roe", "fiscal_year": "FY2025"}).json()
    assert len(bench["peers"]) == 4

    narrative = client.get(f"/api/banks/{bank_id}/narrative",
                           params={"fiscal_year": "FY2025"}).json()
    assert narrative["executive_summary"]

    validations = client.get(f"/api/banks/{bank_id}/validations",
                             params={"fiscal_year": "FY2025"}).json()["results"]
    assert validations and all(v["status"] in ("passed", "failed") for v in validations)


def test_unknown_bank_and_kpi_404(client):
    assert client.get("/api/banks/9999/years").status_code == 404
    assert client.get("/api/benchmarking",
                      params={"kpi_code": "nope", "fiscal_year": "FY2025"}).status_code == 404


def test_document_upload_roundtrip(client, tmp_path):
    """The flagship E2E: synthetic annual report PDF → extraction → derivation
    → validation, all through the public API."""
    import make_sample_pdf

    pdf_path = tmp_path / "pinnacle_fy2025.pdf"
    make_sample_pdf.build(str(pdf_path))

    bank_id = client.get("/api/banks").json()["banks"][0]["id"]
    resp = client.post(
        "/api/documents/upload",
        data={"bank_id": bank_id, "doc_type": "annual_report", "fiscal_year": "FY2026"},
        files={"file": ("pinnacle_fy2025.pdf", pdf_path.read_bytes(), "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "processed"
    assert body["extracted_count"] >= 12  # table + narrative figures

    kpis = client.get(f"/api/banks/{bank_id}/kpis",
                      params={"fiscal_year": "FY2026"}).json()["kpis"]
    by_code = {k["kpi_code"]: k for k in kpis}
    # Table figures land with current-year column values
    assert by_code["gnpa"]["value"] == 5400.0
    assert by_code["cet1_ratio"]["value"] == 14.2
    # Narrative-text figures are captured by the rule-based extractor
    assert by_code["nim"]["value"] == 3.95
    # Ratios not in the document are derived from extracted components
    assert by_code["casa_ratio"]["lineage"]["extraction_method"] == "derived"
    assert by_code["casa_ratio"]["value"] == pytest.approx(40.7, abs=0.2)
    # Lineage points back at the uploaded document
    assert by_code["gnpa"]["lineage"]["document_id"] == body["document_id"]
    assert by_code["gnpa"]["lineage"]["page"] is not None


def test_exports_produce_valid_files(client):
    bank_id = client.get("/api/banks").json()["banks"][0]["id"]
    params = {"bank_id": bank_id, "fiscal_year": "FY2025"}

    excel = client.get("/api/exports/excel", params=params)
    assert excel.status_code == 200 and excel.content[:2] == b"PK"
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(excel.content))
    assert "Validated KPIs" in wb.sheetnames and "Benchmarking" in wb.sheetnames

    pptx = client.get("/api/exports/pptx", params=params)
    assert pptx.status_code == 200 and pptx.content[:2] == b"PK"
    from pptx import Presentation
    deck = Presentation(io.BytesIO(pptx.content))
    assert sum(1 for _ in deck.slides) >= 8

    pdf = client.get("/api/exports/pdf", params=params)
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
