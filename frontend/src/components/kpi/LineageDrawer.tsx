"use client";

import type { KpiValue } from "@/lib/api";
import {
  formatConfidence,
  formatValue,
  humanize,
} from "@/lib/format";
import { Drawer } from "@/components/ui/Drawer";
import { ValidationBadge } from "@/components/ui/Badge";
import { DeltaArrow } from "./KpiCard";

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="border-b border-border/60 pb-4">
      <div className="mb-1.5 text-[10px] uppercase tracking-[0.25em] text-bronze">
        {label}
      </div>
      <div className="text-sm text-text-primary">{children}</div>
    </div>
  );
}

/** "Source & Lineage" panel — full traceability for a single KPI value. */
export function LineageDrawer({
  kpi,
  onClose,
}: {
  kpi: KpiValue | null;
  onClose: () => void;
}) {
  return (
    <Drawer
      open={kpi !== null}
      onClose={onClose}
      label="Source & Lineage"
      title={kpi?.name ?? ""}
    >
      {kpi ? (
        <div className="space-y-4">
          {/* Headline value */}
          <div className="border border-border bg-card/80 p-5">
            <div className="mb-1 text-xs uppercase tracking-[0.2em] text-text-secondary">
              {kpi.fiscal_year} · {humanize(kpi.category)}
            </div>
            <div className="font-serif text-4xl text-text-primary">
              {formatValue(kpi.value, kpi.unit)}
            </div>
            <div className="mt-2">
              <DeltaArrow kpi={kpi} />
            </div>
          </div>

          <Field label="Validation Status">
            <ValidationBadge status={kpi.validation_status} />
          </Field>

          <Field label="Source Document">
            {kpi.lineage.document_title ?? (
              <span className="text-text-secondary">Not on record</span>
            )}
          </Field>

          <Field label="Page">
            {kpi.lineage.page !== null ? (
              <>Page {kpi.lineage.page}</>
            ) : (
              <span className="text-text-secondary">—</span>
            )}
          </Field>

          <Field label="Extraction Method">
            {humanize(kpi.lineage.extraction_method)}
          </Field>

          <Field label="Extraction Confidence">
            <div className="flex items-center gap-3">
              <span className="font-serif text-xl text-gold">
                {formatConfidence(kpi.lineage.confidence)}
              </span>
              <div className="h-1 flex-1 bg-ink">
                <div
                  className="h-full bg-gradient-to-r from-bronze to-gold"
                  style={{
                    width: `${Math.round(
                      Math.min(Math.max(kpi.lineage.confidence, 0), 1) * 100,
                    )}%`,
                  }}
                />
              </div>
            </div>
          </Field>

          <div>
            <div className="mb-1.5 text-[10px] uppercase tracking-[0.25em] text-bronze">
              Source Text
            </div>
            {kpi.lineage.source_text ? (
              <blockquote className="border-l-2 border-gold/60 bg-ink/60 px-4 py-3 font-serif text-sm italic leading-relaxed text-text-secondary">
                “{kpi.lineage.source_text}”
              </blockquote>
            ) : (
              <div className="text-sm text-text-secondary">
                No source excerpt recorded for this value.
              </div>
            )}
          </div>
        </div>
      ) : null}
    </Drawer>
  );
}
