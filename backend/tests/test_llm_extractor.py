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


def test_deterministic_extraction_outranks_llm():
    table_page = PageContent(number=3, text="", tables=[[
        ["Particulars", "FY2025"], ["Gross NPA", "5,400"]]])
    table_cand = TableExtractor().extract([table_page])
    llm_cand = [Candidate("gnpa", 9999.0, 7, "llm", 0.6,
                          "Gross NPA stood at 5,400 crore")]
    best = resolve(table_cand + llm_cand)
    assert best["gnpa"].method == "table" and best["gnpa"].value == 5400.0
