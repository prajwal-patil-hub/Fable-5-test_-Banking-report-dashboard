/**
 * Typed API client for the Banking Annual Report Intelligence Platform.
 * Mirrors docs/API_CONTRACT.md exactly. All fetching happens client-side
 * at runtime; the backend may not be running, in which case every call
 * rejects with a friendly ApiError.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const BACKEND_UNAVAILABLE =
  "Backend unavailable — start the API at localhost:8000";

// ---------------------------------------------------------------------------
// Shared shapes (verbatim from the contract)
// ---------------------------------------------------------------------------

export type ExtractionMethod =
  | "rule_based"
  | "table"
  | "llm"
  | "manual"
  | "derived";

export type ValidationStatus = "passed" | "warning" | "failed" | "unvalidated";

export interface Lineage {
  document_id: number | null;
  document_title: string | null;
  page: number | null;
  extraction_method: ExtractionMethod;
  confidence: number; // 0..1
  source_text: string | null;
}

export type KpiCategory =
  | "financial"
  | "asset_quality"
  | "capital"
  | "liquidity"
  | "operations"
  | "esg";

/**
 * `usd_mn` appears only in the currency display layer: with `currency=usd`
 * the warehouse converts monetary `inr_crore` values to US$ million for
 * display (percent/count/ratio KPIs are untouched).
 */
export type KpiUnit = "inr_crore" | "usd_mn" | "percent" | "count" | "ratio";

export type Currency = "inr" | "usd";

/** Peer-cohort tag carried by each bank. */
export type BankSegment = "private" | "public" | "sfb" | "foreign" | "universal";

export type KpiDirection = "higher_is_better" | "lower_is_better" | "neutral";

export interface KpiValue {
  kpi_code: string;
  name: string;
  category: KpiCategory;
  unit: KpiUnit;
  direction: KpiDirection;
  value: number | null;
  fiscal_year: string;
  yoy_change: number | null;
  yoy_change_pct: number | null;
  lineage: Lineage;
  validation_status: ValidationStatus;
}

// ---------------------------------------------------------------------------
// Endpoint payloads
// ---------------------------------------------------------------------------

export interface Bank {
  id: number;
  code: string;
  name: string;
  segment: BankSegment;
  is_demo: boolean;
  /** False until at least one document/figure exists for this institution. */
  has_data: boolean;
}

export interface BanksResponse {
  banks: Bank[];
}

export interface YearsResponse {
  fiscal_years: string[]; // ascending
}

export interface BankRef {
  id: number;
  code: string;
  name: string;
}

export interface KpisResponse {
  bank: BankRef;
  fiscal_year: string;
  currency: Currency;
  kpis: KpiValue[];
}

export interface KpiHistoryPoint {
  fiscal_year: string;
  value: number | null;
}

export interface KpiHistoryResponse {
  kpi_code: string;
  name: string;
  unit: KpiUnit;
  direction: KpiDirection;
  series: KpiHistoryPoint[];
}

export interface BenchmarkPeer {
  bank_id: number;
  bank_code: string;
  bank_name: string;
  value: number | null;
  rank: number; // 1 = best given direction
  percentile: number; // 0..100, 100 = best
}

export interface BenchmarkStats {
  min: number;
  max: number;
  median: number;
  mean: number;
}

export interface BenchmarkingResponse {
  kpi_code: string;
  name: string;
  unit: KpiUnit;
  direction: KpiDirection;
  fiscal_year: string;
  segment: BankSegment | null; // null when unfiltered
  peers: BenchmarkPeer[];
  stats: BenchmarkStats;
}

export interface BenchmarkingSummaryKpi {
  kpi_code: string;
  name: string;
  unit: KpiUnit;
  direction: KpiDirection;
  peers: BenchmarkPeer[];
  stats: BenchmarkStats;
}

export interface BenchmarkingSummaryResponse {
  fiscal_year: string;
  segment: BankSegment | null; // null when unfiltered
  kpis: BenchmarkingSummaryKpi[];
}

export type NarrativeModule =
  | "financial"
  | "asset_quality"
  | "capital"
  | "liquidity"
  | "operations"
  | "benchmarking";

export interface NarrativeSection {
  module: NarrativeModule;
  headline: string;
  commentary: string;
  takeaways: string[];
  recommendations: string[];
}

export interface NarrativeResponse {
  bank: BankRef;
  fiscal_year: string;
  executive_summary: string[];
  sections: NarrativeSection[];
}

export type ValidationSeverity = "error" | "warning" | "info";

export interface ValidationResult {
  rule_code: string;
  rule_name: string;
  severity: ValidationSeverity;
  status: "passed" | "failed";
  message: string;
  kpi_codes: string[];
}

export interface ValidationsResponse {
  results: ValidationResult[];
}

export interface DocumentRecord {
  id: number;
  bank_id: number;
  title: string;
  doc_type: string;
  fiscal_year: string;
  pages: number;
  status: string;
  uploaded_at: string;
}

export interface DocumentsResponse {
  documents: DocumentRecord[];
}

export interface UploadResponse {
  document_id: number;
  status: string;
  extracted_count: number;
  validation: { passed: number; warnings: number; failed: number };
}

export interface HealthResponse {
  status: string;
  version: string;
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { cache: "no-store", ...init });
  } catch {
    // Network-level failure: backend not running / unreachable.
    throw new ApiError(BACKEND_UNAVAILABLE, 0);
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      // non-JSON error body; keep default detail
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

export const api = {
  // Banks & periods
  getBanks: () => request<BanksResponse>("/api/banks"),
  createBank: (name: string, segment: BankSegment) =>
    request<Bank>("/api/banks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, segment }),
    }),
  getYears: (bankId: number) =>
    request<YearsResponse>(`/api/banks/${bankId}/years`),

  // KPI warehouse
  getKpis: (bankId: number, fiscalYear: string, currency: Currency = "inr") =>
    request<KpisResponse>(
      `/api/banks/${bankId}/kpis?fiscal_year=${encodeURIComponent(fiscalYear)}${
        currency === "usd" ? "&currency=usd" : ""
      }`,
    ),
  getKpiHistory: (
    bankId: number,
    kpiCode: string,
    currency: Currency = "inr",
  ) =>
    request<KpiHistoryResponse>(
      `/api/banks/${bankId}/kpis/${encodeURIComponent(kpiCode)}/history${
        currency === "usd" ? "?currency=usd" : ""
      }`,
    ),

  // Benchmarking (always ₹; optional peer-cohort filter)
  getBenchmarking: (
    kpiCode: string,
    fiscalYear: string,
    segment?: BankSegment | null,
  ) =>
    request<BenchmarkingResponse>(
      `/api/benchmarking?kpi_code=${encodeURIComponent(kpiCode)}&fiscal_year=${encodeURIComponent(fiscalYear)}${
        segment ? `&segment=${encodeURIComponent(segment)}` : ""
      }`,
    ),
  getBenchmarkingSummary: (fiscalYear: string, segment?: BankSegment | null) =>
    request<BenchmarkingSummaryResponse>(
      `/api/benchmarking/summary?fiscal_year=${encodeURIComponent(fiscalYear)}${
        segment ? `&segment=${encodeURIComponent(segment)}` : ""
      }`,
    ),

  // Narrative
  getNarrative: (bankId: number, fiscalYear: string) =>
    request<NarrativeResponse>(
      `/api/banks/${bankId}/narrative?fiscal_year=${encodeURIComponent(fiscalYear)}`,
    ),

  // Validation
  getValidations: (bankId: number, fiscalYear: string) =>
    request<ValidationsResponse>(
      `/api/banks/${bankId}/validations?fiscal_year=${encodeURIComponent(fiscalYear)}`,
    ),

  // Documents & ingestion
  getDocuments: () => request<DocumentsResponse>("/api/documents"),
  uploadDocument: (form: FormData) =>
    request<UploadResponse>("/api/documents/upload", {
      method: "POST",
      body: form,
    }),

  // Health
  getHealth: () => request<HealthResponse>("/api/health"),
};

/** Direct download URL for the export endpoints (used in plain <a href>). */
export function exportUrl(
  kind: "excel" | "pptx" | "pdf",
  bankId: number,
  fiscalYear: string,
): string {
  return `${API_BASE}/api/exports/${kind}?bank_id=${bankId}&fiscal_year=${encodeURIComponent(fiscalYear)}`;
}
