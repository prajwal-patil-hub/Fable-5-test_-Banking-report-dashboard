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
                for alias, code in aliases:
                    idx = lowered.find(alias)
                    if idx < 0:
                        continue
                    tail = segment[idx + len(alias):]
                    m = NUMBER_RE.search(tail)
                    if not m or not m.group(1).strip("()-,. "):
                        continue
                    gap = m.start()
                    if gap > 40:  # number too far from label to trust the association
                        continue
                    kpi = KPI_REGISTRY[code]
                    value = normalize_value(m.group(1), m.group(2), kpi.unit)
                    if value is None:
                        continue
                    confidence = round(base_confidence - min(gap, 30) * 0.005, 3)
                    out.append(Candidate(code, value, page.number, self.method,
                                         confidence, segment.strip()[:300]))
                    break  # longest-alias-first index: first hit per segment wins
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
                        value = normalize_value(m.group(1), unit_hint, kpi.unit)
                        if value is None:
                            continue
                        out.append(Candidate(code, value, page.number, self.method,
                                             self.base_confidence,
                                             " | ".join(filter(None, cells))[:300]))
                        break
        return out


class LlmExtractor:
    """Pluggable LLM fallback — OFF by default.

    Integration point for a Claude-based extractor targeting layouts the
    deterministic strategies miss (narrative-embedded figures, exotic table
    structures). Contract for any future implementation:

    - prompt with the registry's KPI definitions and the page text;
    - require page number + verbatim source quote for every value (lineage);
    - cap confidence at ``max_confidence`` so deterministic hits always win;
    - validate the quote actually appears on the cited page before accepting.

    Kept as an explicit no-op rather than deleted: the pipeline composes
    extractors, and this preserves the seam where AI earns its place only
    after the deterministic baseline is exhausted.
    """

    method = "llm"
    max_confidence = 0.6

    def extract(self, pages: list[PageContent]) -> list[Candidate]:
        return []


DEFAULT_EXTRACTORS = (TableExtractor(), RuleBasedExtractor())


def resolve(candidates: list[Candidate]) -> dict[str, Candidate]:
    """Pick the winning candidate per KPI: highest confidence, then earliest
    page (key-figures sections precede appendix restatements)."""
    best: dict[str, Candidate] = {}
    for cand in sorted(candidates, key=lambda c: (-c.confidence, c.page)):
        best.setdefault(cand.kpi_code, cand)
    return best
