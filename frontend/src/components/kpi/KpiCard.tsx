"use client";

import type { KpiValue } from "@/lib/api";
import { deltaTone, formatDelta, formatValue } from "@/lib/format";
import { ValidationBadge } from "@/components/ui/Badge";

const TONE_CLASS = {
  success: "text-success",
  risk: "text-[#C98A8A]",
  neutral: "text-text-secondary",
} as const;

export function DeltaArrow({ kpi }: { kpi: KpiValue }) {
  if (kpi.yoy_change === null) {
    return <span className="text-xs text-text-secondary/70">— vs PY</span>;
  }
  const tone = deltaTone(kpi);
  const arrow = kpi.yoy_change > 0 ? "▲" : kpi.yoy_change < 0 ? "▼" : "■";
  return (
    <span className={`inline-flex items-baseline gap-1.5 text-xs ${TONE_CLASS[tone]}`}>
      <span className="text-[10px]">{arrow}</span>
      <span>{formatDelta(kpi.yoy_change, kpi.unit)}</span>
      {kpi.yoy_change_pct !== null && kpi.unit !== "percent" ? (
        <span className="text-text-secondary/70">
          ({kpi.yoy_change_pct > 0 ? "+" : ""}
          {kpi.yoy_change_pct.toFixed(1)}%)
        </span>
      ) : null}
      <span className="text-text-secondary/70">YoY</span>
    </span>
  );
}

/**
 * Engraved KPI tile. Clicking opens the Source & Lineage drawer
 * (traceability is a core product requirement).
 */
export function KpiCard({
  kpi,
  onSelect,
  hero = false,
}: {
  kpi: KpiValue;
  onSelect: (kpi: KpiValue) => void;
  hero?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => onSelect(kpi)}
      title="View source & lineage"
      className="group flex w-full flex-col items-start gap-3 border border-border bg-card/80 p-5 text-left transition-colors hover:border-gold/60 hover:bg-card"
    >
      <div className="flex w-full items-start justify-between gap-2">
        <span className="text-xs uppercase tracking-[0.2em] text-text-secondary">
          {kpi.name}
        </span>
        <ValidationBadge status={kpi.validation_status} />
      </div>
      <div
        className={`font-serif text-text-primary ${hero ? "text-4xl" : "text-3xl"}`}
      >
        {formatValue(kpi.value, kpi.unit)}
      </div>
      <div className="flex w-full items-center justify-between">
        <DeltaArrow kpi={kpi} />
        <span className="text-[10px] uppercase tracking-[0.2em] text-bronze opacity-0 transition-opacity group-hover:opacity-100">
          Lineage →
        </span>
      </div>
    </button>
  );
}
