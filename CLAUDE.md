# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Sovereign — an Indian Banking Annual Report Intelligence Platform (₹ crore
units, RBI/Basel III India conventions, Indian FY). PDF banking documents → validated KPI warehouse → benchmarking/narrative analytics →
dashboard + PDF/PPTX/Excel deliverables. Monorepo: FastAPI backend
(`backend/`), Next.js 15 frontend (`frontend/`).

## Commands

Backend (from `backend/`, venv at `backend/.venv`):

```bash
uv venv .venv && uv pip install -p .venv/bin/python -e ".[dev]"  # setup
.venv/bin/python -m pytest                  # all tests (27, incl. E2E)
.venv/bin/python -m pytest tests/test_validation.py -k roe   # single test
.venv/bin/uvicorn app.main:app --reload --port 8000          # run API
.venv/bin/python scripts/make_sample_pdf.py  # synthetic annual report for pipeline testing
.venv/bin/python scripts/make_stress_pdf.py  # hostile-pattern PDF backing the extraction quality gate
```

Frontend (from `frontend/`):

```bash
npm install
npm run dev      # dev server on :3000 (expects API on :8000)
npm run build    # production build + type-check + lint — must pass
```

First backend boot creates SQLite (`backend/sovereign.db`, gitignored) and
seeds 4 demo banks × 3 fiscal years. Delete the file to reseed.

## Architecture — what you must not break

Read `docs/ARCHITECTURE.md` for rationale. The load-bearing rules:

1. **`docs/API_CONTRACT.md` governs the frontend↔backend boundary.** Change
   the contract doc first, then both sides. Frontend types in
   `frontend/src/lib/api.ts` mirror it verbatim.
2. **KPI semantics live ONLY in `backend/app/modules/kpi_warehouse/registry.py`**
   (code, name, unit, direction, extraction aliases, derivation formula,
   benchmarkable flag). To add a KPI, add one registry entry — extraction,
   derivation, benchmarking, narrative and exports pick it up automatically.
3. **Single calculation path.** Exports (`modules/export/`), narrative and the
   API all read via `kpi_warehouse/service.py`. Never compute KPI values
   inside an export or frontend component.
4. **Every warehouse fact carries lineage** (document, page, method,
   confidence, source text). Any new write path must populate it; the
   dashboard's lineage drawer and the PDF appendix depend on it.
5. **Reported values beat derived ones.** `derive_missing()` only backfills
   gaps; divergence is flagged by validation rules, never auto-corrected.
6. **Deterministic-first extraction.** The `LlmExtractor` seam in
   `modules/document_intelligence/extractors.py` is intentionally a capped
   (max confidence 0.6), disabled-by-default fallback. Don't promote LLM
   extraction above deterministic strategies.
7. **Module boundaries**: document_intelligence, kpi_warehouse, validation,
   benchmarking, narrative, export are independent; cross-module imports go
   through service/engine entry points, and the API layer (`app/api/routes.py`)
   stays thin.

## Conventions

- Canonical units: ₹ crore (`inr_crore`), percent, count. Unit conversion
  happens only in `document_intelligence/normalize.py`.
- Validation rules are pure functions appended to `RULES` in
  `modules/validation/engine.py`; each declares the `kpi_codes` it badges.
- Demo/seed data is synthetic and flagged `is_demo` — never seed real banks'
  figures.
- Frontend design system ("Old Money — Daylight", light ivory/gold) lives as
  Tailwind theme tokens in `frontend/src/app/globals.css` plus chart constants
  in `frontend/src/components/charts/theme.ts`. Exports
  (`backend/app/modules/export/theme.py`) deliberately keep the dark boardroom
  variant of the same palette.
- Frontend data fetching is client-side only (`npm run build` must succeed
  with no backend running).
