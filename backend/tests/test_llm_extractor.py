"""LlmExtractor trust constraints, tested with a stubbed Anthropic client —
no network, no API key."""
import json

from app.modules.document_intelligence.extractors import (
    Candidate, LlmExtractor, PageContent, TableExtractor, resolve,
)

PAGE = PageContent(
    number=7,
    text=("The Bank's Return on Equity was 15.1% for the year.\n"
          "Gross NPA stood at 5,400 crore as on March 31, 2025."),
    tables=[],
)


class FakeClient:
    def __init__(self, payload):
        self._payload = payload
        self.messages = self

    def create(self, **kwargs):
        class Block:
            text = json.dumps(self._payload) if isinstance(self._payload, (list, dict)) \
                else self._payload
        Block.text = json.dumps(self._payload)

        class Response:
            content = [Block()]
        return Response()


def test_accepts_quote_verified_values():
    payload = [{"kpi_code": "roe", "value": 15.1, "unit": "%", "page": 7,
                "quote": "Return on Equity was 15.1% for the year."}]
    found = LlmExtractor(client=FakeClient(payload)).extract([PAGE])
    assert len(found) == 1
    cand = found[0]
    assert cand.kpi_code == "roe" and cand.value == 15.1 and cand.page == 7
    assert cand.method == "llm"
    assert cand.confidence == 0.6  # hard cap


def test_rejects_fabricated_quote():
    payload = [{"kpi_code": "roe", "value": 15.1, "unit": "%", "page": 7,
                "quote": "ROE reached a record 15.1% this fiscal."}]  # not in page text
    assert LlmExtractor(client=FakeClient(payload)).extract([PAGE]) == []


def test_rejects_wrong_page_unknown_kpi_and_bad_units():
    payload = [
        {"kpi_code": "roe", "value": 15.1, "unit": "%", "page": 99,
         "quote": "Return on Equity was 15.1% for the year."},
        {"kpi_code": "not_a_kpi", "value": 1, "unit": "", "page": 7,
         "quote": "Return on Equity was 15.1% for the year."},
        # percent where ₹ crore is required → unit-incompatible, dropped
        {"kpi_code": "gnpa", "value": 5400, "unit": "%", "page": 7,
         "quote": "Gross NPA stood at 5,400 crore as on March 31, 2025."},
    ]
    assert LlmExtractor(client=FakeClient(payload)).extract([PAGE]) == []


def test_malformed_response_degrades_to_nothing():
    class BrokenClient:
        def __init__(self):
            self.messages = self

        def create(self, **kwargs):
            raise RuntimeError("api down")

    assert LlmExtractor(client=BrokenClient()).extract([PAGE]) == []


def test_ollama_provider_path(monkeypatch):
    """provider=ollama routes through the local HTTP seam — same trust
    constraints, no anthropic SDK involved."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_model", None)

    good = {"kpi_code": "roe", "value": 15.1, "unit": "%", "page": 7,
            "quote": "Return on Equity was 15.1% for the year."}
    fabricated = {"kpi_code": "gnpa", "value": 5400, "unit": "crore", "page": 7,
                  "quote": "GNPA printed a record low this fiscal."}  # not on page
    captured = {}

    def fake_request(self, url, payload):
        captured["url"] = url
        captured["payload"] = payload
        return {"message": {"content": json.dumps([good, fabricated])}}

    monkeypatch.setattr(LlmExtractor, "_ollama_request", fake_request)

    found = LlmExtractor().extract([PAGE])
    assert [c.kpi_code for c in found] == ["roe"]  # fabricated quote rejected
    assert found[0].confidence == 0.6  # cap holds for local models too
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["payload"]["model"] == LlmExtractor.OLLAMA_DEFAULT_MODEL
    assert captured["payload"]["stream"] is False


def test_ollama_server_down_degrades_to_nothing(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "llm_provider", "ollama")

    def broken(self, url, payload):
        raise OSError("connection refused")

    monkeypatch.setattr(LlmExtractor, "_ollama_request", broken)
    assert LlmExtractor().extract([PAGE]) == []


def test_deterministic_extraction_outranks_llm():
    table_page = PageContent(number=3, text="", tables=[[
        ["Particulars", "FY2025"], ["Gross NPA", "5,400"]]])
    table_cand = TableExtractor().extract([table_page])
    llm_cand = [Candidate("gnpa", 9999.0, 7, "llm", 0.6,
                          "Gross NPA stood at 5,400 crore")]
    best = resolve(table_cand + llm_cand)
    assert best["gnpa"].method == "table" and best["gnpa"].value == 5400.0
