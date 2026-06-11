# API Contract — Banking Annual Report Intelligence Platform

This document is the **single source of truth** for the HTTP contract between the
FastAPI backend (`backend/`) and the Next.js frontend (`frontend/`). Both sides must
conform to it. Change it here first, then change code.

Base URL (dev): `http://localhost:8000`
All endpoints are prefixed with `/api`. All responses are JSON unless noted.

## Conventions

- `fiscal_year`: string, e.g. `"FY2024"`. Sorted lexicographically = chronologically.
- Monetary values are reported in **₹ crore** (`unit: "inr_crore"`); ratios in
  percent (`unit: "percent"`); counts as plain numbers (`unit: "count"`).
- Every KPI value carries **lineage** (where it came from) and a
  **validation_status**: `"passed" | "warning" | "failed" | "unvalidated"`.

### Shared shapes

```ts
type Lineage = {
  document_id: number | null;
  document_title: string | null;
  page: number | null;
  extraction_method: "rule_based" | "table" | "llm" | "manual" | "derived";
  confidence: number; // 0..1
  source_text: string | null; // raw text the value was extracted from
};

type KpiValue = {
  kpi_code: string;          // e.g. "roe", "gnpa_ratio", "cet1_ratio"
  name: string;              // display name, e.g. "Return on Equity"
  category: "financial" | "asset_quality" | "capital" | "liquidity" | "operations" | "esg";
  unit: "inr_crore" | "percent" | "count" | "ratio";
  direction: "higher_is_better" | "lower_is_better" | "neutral";
  value: number | null;
  fiscal_year: string;
  yoy_change: number | null;     // absolute change vs prior year (same unit)
  yoy_change_pct: number | null; // percent change vs prior year
  lineage: Lineage;
  validation_status: "passed" | "warning" | "failed" | "unvalidated";
};
```

## Endpoints

### Banks & periods

- `GET /api/banks`
  → `{ banks: [{ id, code, name, is_demo: boolean }] }`
- `GET /api/banks/{bank_id}/years`
  → `{ fiscal_years: string[] }` (ascending)

### KPI warehouse

- `GET /api/banks/{bank_id}/kpis?fiscal_year=FY2024`
  → `{ bank: {id, code, name}, fiscal_year, kpis: KpiValue[] }`
  All KPIs for the bank-year, across categories. Frontend groups by `category`.
- `GET /api/banks/{bank_id}/kpis/{kpi_code}/history`
  → `{ kpi_code, name, unit, direction, series: [{ fiscal_year, value }] }`

### Benchmarking

- `GET /api/benchmarking?kpi_code=roe&fiscal_year=FY2024`
  → ```
  { kpi_code, name, unit, direction, fiscal_year,
    peers: [{ bank_id, bank_code, bank_name, value, rank, percentile }],
    stats: { min, max, median, mean } }
  ```
  `rank` 1 = best given `direction`. `percentile` 0..100 (100 = best).
- `GET /api/benchmarking/summary?fiscal_year=FY2024`
  → `{ fiscal_year, kpis: [{ kpi_code, name, unit, direction, peers: [...] , stats: {...} }] }`
  One entry per benchmarkable KPI (a curated subset, ~12 KPIs).

### Narrative (Executive Intelligence)

- `GET /api/banks/{bank_id}/narrative?fiscal_year=FY2024`
  → ```
  { bank: {...}, fiscal_year,
    executive_summary: string[],          // 3–6 bullet takeaways
    sections: [{
      module: "financial" | "asset_quality" | "capital" | "liquidity" | "operations" | "benchmarking",
      headline: string,                    // consulting-style action title
      commentary: string,                  // 2–4 sentence diagnostic
      takeaways: string[],                 // bullets
      recommendations: string[]            // may be empty
    }] }
  ```

### Validation

- `GET /api/banks/{bank_id}/validations?fiscal_year=FY2024`
  → `{ results: [{ rule_code, rule_name, severity: "error"|"warning"|"info", status: "passed"|"failed", message, kpi_codes: string[] }] }`

### Documents & ingestion

- `GET /api/documents` → `{ documents: [{ id, bank_id, title, doc_type, fiscal_year, pages, status, uploaded_at }] }`
- `POST /api/documents/upload` (multipart: `file`, `bank_id`, `doc_type`, `fiscal_year`)
  → `{ document_id, status, extracted_count, validation: { passed, warnings, failed } }`

### Exports

All exports stream a file (`Content-Disposition: attachment`):

- `GET /api/exports/excel?bank_id=1&fiscal_year=FY2024` → `.xlsx`
- `GET /api/exports/pptx?bank_id=1&fiscal_year=FY2024` → `.pptx`
- `GET /api/exports/pdf?bank_id=1&fiscal_year=FY2024` → `.pdf`

### Health

- `GET /api/health` → `{ status: "ok", version }`

## Error shape

Non-2xx responses: `{ detail: string }` (FastAPI default).

## CORS

Backend allows `http://localhost:3000` in dev.
