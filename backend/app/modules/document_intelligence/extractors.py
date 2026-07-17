"""Extraction strategies for the hybrid document-intelligence pipeline.

Strategy hierarchy (deterministic first — accuracy, auditability and
repeatability beat novel AI usage):

1. TableExtractor      — structured tables, highest confidence (0.9 base)
2. RuleBasedExtractor  — labelled key-figure lines in running text (0.75 base)
3. LlmExtractor        — pluggable fallback for layouts the deterministic
                         extractors cannot parse; disabled by default and
                         intentionally capped at lower confidence so a
                         deterministic hit always outranks an LLM guess.

All extractors emit Candidate objects; the pipeline resolves competing
candidates per KPI by confidence. Nothing reaches the warehouse without
lineage (page, method, source text, confidence).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.modules.document_intelligence.normalize import NUMBER_RE, normalize_value
from app.modules.kpi_warehouse.registry import KPI_REGISTRY, alias_index


@dataclass(frozen=True)
class Candidate:
    kpi_code: str
    value: float
    page: int
    method: str  # table | rule_based | llm
    confidence: float
    source_text: str


@dataclass(frozen=True)
class PageContent:
    """Extractor-agnostic page representation produced by the PDF reader."""
    number: int
    text: str
    tables: list[list[list[str | None]]]  # tables -> rows -> cells
    # Crore multiplier declared by the page's "₹ in lakh/crore/..." caption;
    # applied to bare monetary numbers (explicit unit words override it).
    scale_hint: float | None = None


_SENTENCE_SPLIT = re.compile(r"(?<=[.;:])\s+")


class RuleBasedExtractor:
    """Matches registry aliases followed by a nearby number in running text.

    'Net Interest Income of ₹12,345 crore' / 'GNPA Ratio: 2.31%' style figures.
    Scans both raw lines and whitespace-rejoined sentences: PDFs hard-wrap
    paragraphs, so a label and its number frequently land on different lines
    ('Net Interest Margin was\\n3.95%'). Sentence matches carry slightly lower
    confidence than single-line matches — the narrower the scope, the safer
    the label→number association — and resolution keeps the best candidate.
    """

    method = "rule_based"
    line_confidence = 0.75
    sentence_confidence = 0.70

    def extract(self, pages: list[PageContent]) -> list[Candidate]:
        aliases = alias_index()
        out: list[Candidate] = []
        for page in pages:
            segments = [(line, self.line_confidence) for line in page.text.splitlines()]
            rejoined = page.text.replace("\n", " ")
            segments += [(s, self.sentence_confidence)
                         for s in _SENTENCE_SPLIT.split(rejoined)]
            for segment, base_confidence in segments:
                lowered = segment.lower()
                # One sentence often names several KPIs ("Total Deposits grew
                # to X, of which CASA Deposits were Y — a CASA Ratio of Z%"),
                # so every alias gets a chance — but a consumed label span
                # blocks its own sub-strings ("gross npa ratio" ⊃ "gross npa")
                # from double-matching the same text.
                consumed: list[tuple[int, int]] = []
                for alias, code in aliases:
                    idx = lowered.find(alias)
                    if idx < 0:
                        continue
                    span = (idx, idx + len(alias))
                    if any(span[0] < end and span[1] > start for start, end in consumed):
                        continue
                    consumed.append(span)
                    tail = segment[idx + len(alias):]
                    kpi = KPI_REGISTRY[code]
                    matches = [x for x in NUMBER_RE.finditer(tail)
                               if x.start() <= 40 and x.group(1).strip("()-,. ")]
                    if not matches:
                        continue
                    # "NIM improved by 25 bps to 3.85%": for percent KPIs an
                    # explicit %-marked figure is the level; a bps figure is a
                    # movement. Prefer the % match over positional order.
                    m = None
                    if kpi.unit == "percent":
                        m = next((x for x in matches
                                  if x.group(2).lower().replace(" ", "").rstrip(".")
                                  in ("%", "percent")), None)
                    if m is None:
                        m = matches[0]
                    gap = m.start()
                    value = normalize_value(m.group(1), m.group(2), kpi.unit,
                                            scale_hint=page.scale_hint)
                    if value is None:
                        continue
                    confidence = round(base_confidence - min(gap, 30) * 0.005, 3)
                    out.append(Candidate(code, value, page.number, self.method,
                                         confidence, segment.strip()[:300]))
        return out


class TableExtractor:
    """Matches KPI aliases in the first cell of a table row, takes the last
    numeric cell in that row (annual-report convention: current year is the
    final column)."""

    method = "table"
    base_confidence = 0.9

    def extract(self, pages: list[PageContent]) -> list[Candidate]:
        aliases = alias_index()
        out: list[Candidate] = []
        for page in pages:
            for table in page.tables:
                for row in table:
                    cells = [(c or "").strip() for c in row]
                    if len(cells) < 2 or not cells[0]:
                        continue
                    label = cells[0].lower()
                    code = next((c for a, c in aliases if a in label), None)
                    if code is None:
                        continue
                    kpi = KPI_REGISTRY[code]
                    for cell in reversed(cells[1:]):
                        m = NUMBER_RE.fullmatch(cell.replace("₹", "").strip())
                        if not m or not m.group(1).strip("()-,. "):
                            continue
                        unit_hint = m.group(2) or ("%" if "%" in cells[0] or "ratio" in label else "")
                        value = normalize_value(m.group(1), unit_hint, kpi.unit,
                                                scale_hint=page.scale_hint)
                        if value is None:
                            continue
                        out.append(Candidate(code, value, page.number, self.method,
                                             self.base_confidence,
                                             " | ".join(filter(None, cells))[:300]))
                        break
        return out


class LlmExtractor:
    """LLM fallback extractor — OFF by default (see Settings.llm_extraction_enabled).

    Two providers, selected by ``Settings.llm_provider``:

    - ``anthropic`` — Claude via the anthropic SDK (needs ANTHROPIC_API_KEY
      and ``pip install -e ".[llm]"``);
    - ``ollama`` — a local model served by Ollama (http://localhost:11434 by
      default). No API key, no extra Python dependency (stdlib HTTP), fully
      offline — suited to a MacBook running e.g. ``llama3.1:8b``.

    Targets layouts the deterministic strategies miss (narrative-embedded
    figures, exotic table structures). Trust constraints, enforced here and
    non-negotiable regardless of provider:

    - every value must cite a page number and a verbatim quote;
    - the quote is verified to actually appear on the cited page — a value
      with a fabricated or paraphrased quote is dropped;
    - confidence is capped at ``max_confidence`` (0.6), below the table
      extractor (0.9) and rule-based extractor (~0.75), so a deterministic
      hit always outranks an LLM reading of the same figure;
    - any API/parsing failure degrades to "no candidates", never breaks the
      deterministic pipeline.
    """

    method = "llm"
    max_confidence = 0.6
    max_pages = 40
    max_chars_per_page = 4000

    ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-5"
    OLLAMA_DEFAULT_MODEL = "llama3.1:8b"
    OPENAI_COMPAT_DEFAULT_MODEL = "glm-4-flash"  # Zhipu GLM's economical tier

    def __init__(self, client=None, model: str | None = None):
        # client injectable for tests; lazily built from the anthropic SDK
        # (optional dependency: pip install -e ".[llm]") when enabled.
        self._client = client
        self._model = model

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import anthropic
            self._client = anthropic.Anthropic()
        except Exception:
            return None
        return self._client

    def _resolve_model(self, settings) -> str:
        if self._model:
            return self._model
        if settings.llm_model:
            return settings.llm_model
        if settings.llm_provider == "ollama":
            return self.OLLAMA_DEFAULT_MODEL
        if settings.llm_provider == "openai_compatible":
            return self.OPENAI_COMPAT_DEFAULT_MODEL
        return self.ANTHROPIC_DEFAULT_MODEL

    def _post_json(self, url: str, payload: dict, headers: dict | None = None) -> dict:
        """One JSON POST (stdlib HTTP; the seam tests monkeypatch).
        Local models are slow on first token — generous timeout."""
        import urllib.request
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", **(headers or {})})
        with urllib.request.urlopen(req, timeout=300) as resp:  # noqa: S310
            return json.loads(resp.read().decode())

    def _complete_ollama(self, prompt: str, settings) -> str | None:
        payload = {
            "model": self._resolve_model(settings),
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",  # constrain local models to valid JSON
            "options": {"temperature": 0},
        }
        data = self._post_json(
            f"{settings.ollama_base_url.rstrip('/')}/api/chat", payload)
        return (data.get("message") or {}).get("content")

    def _complete_openai_compatible(self, prompt: str, settings) -> str | None:
        """Any /chat/completions endpoint — e.g. Zhipu GLM
        (https://open.bigmodel.cn/api/paas/v4, model glm-4-plus)."""
        if not settings.llm_base_url:
            return None
        payload = {
            "model": self._resolve_model(settings),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "stream": False,
        }
        headers = ({"Authorization": f"Bearer {settings.llm_api_key}"}
                   if settings.llm_api_key else {})
        data = self._post_json(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions", payload, headers)
        choices = data.get("choices") or []
        if not choices:
            return None
        return (choices[0].get("message") or {}).get("content")

    def _complete(self, prompt: str) -> str | None:
        from app.core.config import settings
        # An injected client (tests) always wins; otherwise route by provider.
        if self._client is None and settings.llm_provider == "ollama":
            return self._complete_ollama(prompt, settings)
        if self._client is None and settings.llm_provider == "openai_compatible":
            return self._complete_openai_compatible(prompt, settings)
        client = self._get_client()
        if client is None:
            return None
        response = client.messages.create(
            model=self._resolve_model(settings),
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _prompt(self, pages: list[PageContent]) -> str:
        kpi_lines = "\n".join(
            f"- {k.code}: {k.name} (unit: {k.unit})" for k in KPI_REGISTRY.values())
        page_blocks = "\n\n".join(
            f"[PAGE {p.number}]\n{p.text[:self.max_chars_per_page]}"
            for p in pages[:self.max_pages] if p.text.strip())
        return (
            "You extract banking KPIs from annual-report text. Return ONLY a JSON "
            "array; no prose. Each element: {\"kpi_code\": one of the codes below, "
            "\"value\": number, \"unit\": the unit word as printed (e.g. \"crore\", "
            "\"%\", \"bps\", or \"\"), \"page\": page number, \"quote\": VERBATIM "
            "sentence or table-row fragment containing the figure}. Only include "
            "figures explicitly present in the text for the CURRENT reporting year; "
            "never estimate, never compute.\n\nKPI codes:\n"
            f"{kpi_lines}\n\nDocument pages:\n{page_blocks}"
        )

    def extract(self, pages: list[PageContent]) -> list[Candidate]:
        if not pages:
            return []
        try:
            raw = self._complete(self._prompt(pages))
            if not raw:
                return []
            start, end = raw.find("["), raw.rfind("]")
            items = json.loads(raw[start:end + 1])
        except Exception:
            return []

        page_texts = {p.number: " ".join(p.text.split()) for p in pages}
        out: list[Candidate] = []
        for item in items if isinstance(items, list) else []:
            try:
                code = item["kpi_code"]
                page_no = int(item["page"])
                quote = str(item.get("quote", "")).strip()
            except (KeyError, TypeError, ValueError):
                continue
            kpi = KPI_REGISTRY.get(code)
            page_text = page_texts.get(page_no)
            if kpi is None or page_text is None or not quote:
                continue
            if " ".join(quote.split()) not in page_text:
                continue  # fabricated/paraphrased citation — reject
            value = normalize_value(str(item.get("value", "")), str(item.get("unit", "")),
                                    kpi.unit)
            if value is None:
                continue
            out.append(Candidate(code, value, page_no, self.method,
                                 self.max_confidence, quote[:300]))
        return out


DEFAULT_EXTRACTORS = (TableExtractor(), RuleBasedExtractor())


def resolve(candidates: list[Candidate]) -> dict[str, Candidate]:
    """Pick the winning candidate per KPI: highest confidence, then earliest
    page (key-figures sections precede appendix restatements)."""
    best: dict[str, Candidate] = {}
    for cand in sorted(candidates, key=lambda c: (-c.confidence, c.page)):
        best.setdefault(cand.kpi_code, cand)
    return best
