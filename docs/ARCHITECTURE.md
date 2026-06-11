# Architecture & Design Decisions

## The shape of the system

```
Documents ──► Document Intelligence ──► KPI Warehouse ──► Analytics ──► Surfaces
 (PDF)         extract / normalize       facts + lineage    benchmarking   dashboard
               resolve / OCR-detect      registry           validation     PDF / PPTX
                                         calculation        narrative      Excel
```

Six modules, one warehouse, one calculation engine. The dashboard, PDF
report, PPT deck and Excel pack never compute anything — they render facts
that flowed through `kpi_warehouse.service`. That is what makes 100 → 10,000
reports a scaling problem rather than a consistency problem.

## Decisions and the reasoning behind them

### 1. Deterministic-first extraction; LLM as a capped, optional fallback
A consulting deliverable lives or dies on **auditability**. Table extraction
(base confidence 0.9) and rule-based labelled-figure extraction (0.70–0.75)
are repeatable, explainable and unit-tested. The `LlmExtractor` seam exists
but is off by default and its confidence is capped at 0.6 so a deterministic
hit always outranks an LLM guess. Any future LLM extractor must return a page
number and verbatim quote, verified against the page, before a value is
accepted. AI polishes; it does not originate facts.

### 2. Candidate → resolution model
Extractors emit *candidates*; the pipeline resolves one winner per KPI by
(confidence, earliest page). The warehouse stores resolved truth only —
ambiguity is handled in one place, upstream, not by every consumer.

### 3. The KPI registry is the only place KPI semantics live
`kpi_warehouse/registry.py` declares code, name, category, unit, direction,
extraction aliases, derivation formula and benchmarkability. Extraction,
calculation, validation, benchmarking, narrative, exports and the dashboard
all read it. Adding a KPI = one entry. This is the extensibility story.

### 4. Reported values beat derived values
A bank's published ROE reflects its official basis (e.g. average vs closing
equity). The calculation engine only backfills *missing* metrics; a validation
rule (`roe_consistency` etc.) flags material divergence between reported and
recomputed instead of silently overwriting. Trust > automation.

### 5. Validation badges individual facts, not just periods
Rules persist per bank-year results AND mark each involved KPI fact
(`passed`/`warning`/`failed`), so the dashboard can badge a single number.
Severity model: structural banking identities are errors (NNPA ≤ GNPA,
CET1 ≤ Tier 1 ≤ CRAR), consistency/plausibility are warnings, regulatory
context is info.

### 6. Narrative is computed, not generated
Every sentence in the Executive Intelligence layer traces to a number, a
threshold or a peer rank (the consulting storytelling ladder: headline →
diagnostic → benchmark → recommendation). This keeps the narrative engine
deterministic, testable, and safe for board material. An LLM phrasing-polish
layer can sit on top later without changing what is claimed.

### 7. SQLite by default, PostgreSQL by configuration
SQLAlchemy 2.0 throughout, no dialect-specific SQL. Zero-infrastructure demo;
`SOVEREIGN_DATABASE_URL` flips to Postgres for production.

### 8. Old Money design tokens are shared code
`backend/app/modules/export/theme.py` mirrors the frontend Tailwind theme, so
the dashboard and the exported deliverables are one visual system.

### 9. Synthetic demo data exercises the production write path
The seed runs upsert → derive → validate exactly like ingestion, and the four
fictional banks are distinct strategic archetypes (high-performer, legacy
giant, over-extended challenger, fortress) so benchmarking spread, validation
warnings and recommendations all have signal out of the box. No real bank's
figures are fabricated.

## Security posture (current vs production)

Current: optional shared-secret API key (`SOVEREIGN_API_KEY`), CORS
allow-list, audit log table, PDF-only upload validation, no secrets in repo.
Production requirements (deliberately not faked with toy implementations):
SSO/OIDC authentication, role-based access (analyst/reviewer/executive),
object-storage uploads with AV scanning, encryption at rest, per-tenant
isolation. These belong at the deployment/platform layer; the audit-log and
lineage foundations they need are already in the schema.

## Honest limitations / next iterations

- **Scanned PDFs**: detected and marked `ocr_required`; an OCR stage
  (Tesseract/textract) slots in front of the extractors. Not yet implemented.
- **Multi-column layouts**: pdfplumber's default text flow handles most
  annual reports; complex layout parsing (column detection) is the next
  extraction upgrade.
- **Fiscal-year inference**: the uploader declares the FY; cross-checking the
  declared FY against dates found in the document is a planned validation.
- **Benchmark universe**: peers = all banks in the warehouse. Peer-group
  curation (size/segment cohorts) becomes necessary beyond ~20 banks.
- **Workbook/report internationalisation**: ₹ crore is the canonical unit;
  a units layer (USD mn, configurable) is straightforward on top of the
  registry but not yet built.
