# Sovereign — Banking Annual Report Intelligence Platform

Transforms unstructured banking documents (annual reports, Basel disclosures,
ESG reports) into a validated KPI warehouse, peer benchmarking, executive
narrative, an interactive dashboard, and boardroom-ready deliverables
(PDF report, PowerPoint deck, Excel data pack).

**Document → Data → Analytics → Insight → Decision** — not document → AI summary.
Extraction, validation, derivation, benchmarking and narrative are all
deterministic and fully traceable: every number on every surface carries
lineage (source document, page, extraction method, confidence).

## Architecture (modular product, not project)

| Module | Location | Responsibility |
|---|---|---|
| Document Intelligence | `backend/app/modules/document_intelligence/` | PDF → candidates (table + rule-based extractors, pluggable LLM seam) → resolved facts with lineage |
| KPI Warehouse | `backend/app/modules/kpi_warehouse/` | KPI registry (single source of KPI semantics), calculation engine, query layer |
| Validation Engine | `backend/app/modules/validation/` | Banking-specific structural, consistency and plausibility rules |
| Benchmarking Engine | `backend/app/modules/benchmarking/` | Peer ranking, percentiles, distribution stats |
| Narrative Engine | `backend/app/modules/narrative/` | Deterministic consulting-grade commentary & recommendations |
| Export Engine | `backend/app/modules/export/` | Excel / PPTX / PDF — all reading the same warehouse services |
| Dashboard | `frontend/` | Next.js executive dashboard ("Old Money" design system) |

See `docs/ARCHITECTURE.md` for design decisions and `docs/API_CONTRACT.md`
for the HTTP contract between frontend and backend.

## Quick start

Backend (Python 3.11+):

```bash
cd backend
python -m venv .venv && .venv/bin/pip install -e ".[dev]"   # or: uv venv && uv pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload --port 8000
```

First boot creates a SQLite database and seeds four synthetic demo banks ×
three fiscal years (clearly flagged `is_demo`). Set
`SOVEREIGN_DATABASE_URL=postgresql+psycopg://...` for PostgreSQL and
`SOVEREIGN_SEED_DEMO_DATA=false` to disable seeding. API docs: http://localhost:8000/docs

Frontend (Node 20+):

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

## Try the full pipeline

Generate a synthetic annual report PDF and upload it through the dashboard's
Documents page (or `POST /api/documents/upload`):

```bash
cd backend && .venv/bin/python scripts/make_sample_pdf.py
```

Watch extraction → unit normalisation → derived KPIs → validation run, then
open the bank's dashboard for the new fiscal year and download the exports
from the Reports page.

## Tests

```bash
cd backend && .venv/bin/python -m pytest        # 27 tests incl. PDF→export E2E
cd frontend && npm run build                    # type-check + production build
```
