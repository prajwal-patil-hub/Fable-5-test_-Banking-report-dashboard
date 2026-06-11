import type { KpiUnit, KpiValue } from "./api";

const inrFmt = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
const inrFmtSmall = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2,
});
const countFmt = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

/** ₹ crore with Indian digit grouping, e.g. "₹1,23,456 Cr". */
export function formatINRCrore(value: number): string {
  const fmt = Math.abs(value) < 100 ? inrFmtSmall : inrFmt;
  return `₹${fmt.format(value)} Cr`;
}

/** "14.2%" — one decimal by default. */
export function formatPercent(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

export function formatCount(value: number): string {
  return countFmt.format(value);
}

export function formatRatio(value: number): string {
  return `${value.toFixed(2)}x`;
}

export function formatValue(value: number | null, unit: KpiUnit): string {
  if (value === null || Number.isNaN(value)) return "—";
  switch (unit) {
    case "inr_crore":
      return formatINRCrore(value);
    case "percent":
      return formatPercent(value);
    case "count":
      return formatCount(value);
    case "ratio":
      return formatRatio(value);
  }
}

/** Signed YoY delta in the KPI's own unit, e.g. "+0.4 pp" / "−₹1,234 Cr". */
export function formatDelta(value: number, unit: KpiUnit): string {
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  const abs = Math.abs(value);
  switch (unit) {
    case "inr_crore":
      return `${sign}${formatINRCrore(abs)}`;
    case "percent":
      return `${sign}${abs.toFixed(1)} pp`;
    case "count":
      return `${sign}${formatCount(abs)}`;
    case "ratio":
      return `${sign}${abs.toFixed(2)}x`;
  }
}

export type DeltaTone = "success" | "risk" | "neutral";

/**
 * Whether the YoY move is favourable, respecting the KPI's `direction`.
 * E.g. a falling GNPA ratio (lower_is_better) is a success.
 */
export function deltaTone(kpi: KpiValue): DeltaTone {
  if (kpi.yoy_change === null || kpi.yoy_change === 0) return "neutral";
  if (kpi.direction === "neutral") return "neutral";
  const improved =
    kpi.direction === "higher_is_better"
      ? kpi.yoy_change > 0
      : kpi.yoy_change < 0;
  return improved ? "success" : "risk";
}

/** Confidence 0..1 → "92%". */
export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

const LABELS: Record<string, string> = {
  rule_based: "Rule-based",
  table: "Table extraction",
  llm: "LLM extraction",
  manual: "Manual entry",
  derived: "Derived",
  financial: "Financial Performance",
  asset_quality: "Asset Quality",
  capital: "Capital Adequacy",
  liquidity: "Liquidity",
  operations: "Operations",
  esg: "ESG",
  benchmarking: "Benchmarking",
};

export function humanize(token: string): string {
  return (
    LABELS[token] ??
    token
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ")
  );
}
