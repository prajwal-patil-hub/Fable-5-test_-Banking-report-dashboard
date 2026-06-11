"use client";

import { useMemo, useState } from "react";
import { api, type Bank, type KpiValue } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useBank } from "@/context/BankContext";
import { humanize } from "@/lib/format";
import { Card, PageHeading, SectionLabel } from "@/components/ui/Card";
import {
  KpiCardSkeleton,
  PanelSkeleton,
  Skeleton,
} from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { KpiCard } from "@/components/kpi/KpiCard";
import { LineageDrawer } from "@/components/kpi/LineageDrawer";
import { PageGate } from "@/components/PageGate";

const HERO_CODES = [
  "roe",
  "roa",
  "nim",
  "cost_to_income",
  "gnpa_ratio",
  "cet1_ratio",
] as const;

function ValidationStrip({ bank, fiscalYear }: { bank: Bank; fiscalYear: string }) {
  const state = useApi(
    () => api.getValidations(bank.id, fiscalYear),
    [bank.id, fiscalYear],
  );

  if (state.loading) return <Skeleton className="h-16 w-full" />;
  if (state.error)
    return <ErrorState message={state.error} onRetry={state.retry} compact />;
  if (!state.data) return null;

  const results = state.data.results;
  const passed = results.filter((r) => r.status === "passed").length;
  const failed = results.filter(
    (r) => r.status === "failed" && r.severity === "error",
  ).length;
  const warnings = results.length - passed - failed;

  const cells: { label: string; value: number; dot: string }[] = [
    { label: "Checks Passed", value: passed, dot: "bg-success" },
    { label: "Warnings", value: warnings, dot: "bg-warning" },
    { label: "Failed", value: failed, dot: "bg-risk" },
  ];

  return (
    <Card className="flex items-stretch divide-x divide-border">
      <div className="flex items-center px-7 py-5">
        <div>
          <SectionLabel>Data Assurance</SectionLabel>
          <div className="mt-1 text-sm text-text-secondary">
            {results.length} validation rules evaluated · {fiscalYear}
          </div>
        </div>
      </div>
      {cells.map((cell) => (
        <div key={cell.label} className="flex flex-1 items-center gap-4 px-7 py-5">
          <span className={`size-2 rotate-45 ${cell.dot}`} />
          <div>
            <div className="font-serif text-3xl text-text-primary">
              {cell.value}
            </div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary">
              {cell.label}
            </div>
          </div>
        </div>
      ))}
    </Card>
  );
}

function OverviewBody({ bank, fiscalYear }: { bank: Bank; fiscalYear: string }) {
  const [selectedKpi, setSelectedKpi] = useState<KpiValue | null>(null);

  const kpisState = useApi(
    () => api.getKpis(bank.id, fiscalYear),
    [bank.id, fiscalYear],
  );
  const narrativeState = useApi(
    () => api.getNarrative(bank.id, fiscalYear),
    [bank.id, fiscalYear],
  );

  const heroKpis = useMemo(() => {
    const all = kpisState.data?.kpis ?? [];
    return HERO_CODES.map((code) => all.find((k) => k.kpi_code === code)).filter(
      (k): k is KpiValue => k !== undefined,
    );
  }, [kpisState.data]);

  return (
    <>
      {/* Headline KPIs */}
      <section className="mb-10">
        <SectionLabel className="mb-4">
          Headline Indicators · {fiscalYear}
        </SectionLabel>
        {kpisState.loading ? (
          <div className="grid grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <KpiCardSkeleton key={i} />
            ))}
          </div>
        ) : kpisState.error ? (
          <ErrorState message={kpisState.error} onRetry={kpisState.retry} />
        ) : heroKpis.length === 0 ? (
          <Card className="p-8 text-sm text-text-secondary">
            No headline indicators available for {fiscalYear}.
          </Card>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {heroKpis.map((kpi) => (
              <KpiCard
                key={kpi.kpi_code}
                kpi={kpi}
                onSelect={setSelectedKpi}
                hero
              />
            ))}
          </div>
        )}
      </section>

      {/* Executive summary + section headlines */}
      <section className="mb-10">
        <SectionLabel className="mb-4">Executive Summary</SectionLabel>
        {narrativeState.loading ? (
          <PanelSkeleton lines={6} />
        ) : narrativeState.error ? (
          <ErrorState
            message={narrativeState.error}
            onRetry={narrativeState.retry}
            compact
          />
        ) : narrativeState.data ? (
          <div className="grid gap-4 xl:grid-cols-5">
            <Card className="p-7 xl:col-span-3">
              <h3 className="mb-5 font-serif text-2xl text-text-primary">
                The Year in Brief
              </h3>
              <ul className="space-y-4">
                {narrativeState.data.executive_summary.map((bullet, i) => (
                  <li key={i} className="flex gap-4">
                    <span className="select-none font-serif text-xl leading-6 text-gold">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="text-sm leading-relaxed text-text-secondary">
                      {bullet}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
            <Card className="p-7 xl:col-span-2">
              <SectionLabel className="mb-5">Across the Modules</SectionLabel>
              <ul className="space-y-5">
                {narrativeState.data.sections.map((section) => (
                  <li key={section.module}>
                    <div className="mb-1 text-[10px] uppercase tracking-[0.25em] text-bronze">
                      {humanize(section.module)}
                    </div>
                    <div className="font-serif text-base leading-snug text-text-primary">
                      {section.headline}
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        ) : null}
      </section>

      {/* Validation status strip */}
      <section>
        <ValidationStrip bank={bank} fiscalYear={fiscalYear} />
      </section>

      <LineageDrawer kpi={selectedKpi} onClose={() => setSelectedKpi(null)} />
    </>
  );
}

export default function OverviewPage() {
  const { bank } = useBank();
  return (
    <>
      <PageHeading
        label="Intelligence · Overview"
        title="Executive Overview"
        subtitle={
          bank
            ? `${bank.name} — annual report intelligence at a glance: headline returns, risk posture and data assurance.`
            : "Annual report intelligence at a glance: headline returns, risk posture and data assurance."
        }
      />
      <PageGate>
        {(bank, fiscalYear) => (
          <OverviewBody
            key={`${bank.id}-${fiscalYear}`}
            bank={bank}
            fiscalYear={fiscalYear}
          />
        )}
      </PageGate>
    </>
  );
}
