"use client";

import { useMemo, useState } from "react";
import { api, type KpiCategory, type KpiValue, type Bank } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useBank } from "@/context/BankContext";
import { Card, PageHeading, SectionLabel } from "@/components/ui/Card";
import {
  ChartSkeleton,
  KpiCardSkeleton,
  PanelSkeleton,
} from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { KpiCard } from "@/components/kpi/KpiCard";
import { LineageDrawer } from "@/components/kpi/LineageDrawer";
import { TrendChart } from "@/components/charts/TrendChart";
import { NarrativePanel } from "@/components/narrative/NarrativePanel";
import { PageGate } from "@/components/PageGate";

export interface ModulePageConfig {
  category: Exclude<KpiCategory, "esg">;
  label: string; // tracked eyebrow label
  title: string; // serif page title
  subtitle: string;
  /** Preferred KPI codes for the multi-year trend chart (first 3 found are used). */
  trendCodes: string[];
}

function ModuleBody({
  bank,
  fiscalYear,
  config,
}: {
  bank: Bank;
  fiscalYear: string;
  config: ModulePageConfig;
}) {
  const { category, trendCodes } = config;
  const [selectedKpi, setSelectedKpi] = useState<KpiValue | null>(null);
  const { currency } = useBank();

  const kpisState = useApi(
    () => api.getKpis(bank.id, fiscalYear, currency),
    [bank.id, fiscalYear, currency],
  );
  const narrativeState = useApi(
    () => api.getNarrative(bank.id, fiscalYear),
    [bank.id, fiscalYear],
  );

  const categoryKpis = useMemo(
    () => kpisState.data?.kpis.filter((k) => k.category === category) ?? [],
    [kpisState.data, category],
  );

  // Pick 2–3 KPI codes for the trend chart: preferred codes first,
  // then any other percent-unit KPIs of the category.
  const chartCodes = useMemo(() => {
    if (categoryKpis.length === 0) return [];
    const available = new Set(categoryKpis.map((k) => k.kpi_code));
    const picked = trendCodes.filter((c) => available.has(c));
    for (const k of categoryKpis) {
      if (picked.length >= 3) break;
      if (!picked.includes(k.kpi_code) && k.unit === "percent") {
        picked.push(k.kpi_code);
      }
    }
    return picked.slice(0, 3);
  }, [categoryKpis, trendCodes]);

  const chartKey = chartCodes.join(",");
  const historyState = useApi(
    chartCodes.length > 0
      ? () =>
          Promise.all(
            chartCodes.map((c) => api.getKpiHistory(bank.id, c, currency)),
          )
      : null,
    [bank.id, chartKey, currency],
  );

  const section = narrativeState.data?.sections.find(
    (s) => s.module === category,
  );

  return (
    <>
      {/* KPI grid */}
      <section className="mb-10">
        <SectionLabel className="mb-4">
          Key Indicators · {fiscalYear}
        </SectionLabel>
        {kpisState.loading ? (
          <div className="grid grid-cols-3 gap-4 xl:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <KpiCardSkeleton key={i} />
            ))}
          </div>
        ) : kpisState.error ? (
          <ErrorState message={kpisState.error} onRetry={kpisState.retry} />
        ) : categoryKpis.length === 0 ? (
          <Card className="p-8 text-sm text-text-secondary">
            No indicators recorded for this module in {fiscalYear}.
          </Card>
        ) : (
          <div className="grid grid-cols-3 gap-4 xl:grid-cols-4">
            {categoryKpis.map((kpi) => (
              <KpiCard key={kpi.kpi_code} kpi={kpi} onSelect={setSelectedKpi} />
            ))}
          </div>
        )}
      </section>

      {/* Multi-year trend */}
      <section className="mb-10">
        <SectionLabel className="mb-4">Multi-Year Trend</SectionLabel>
        {kpisState.loading || historyState.loading ? (
          <ChartSkeleton className="h-96" />
        ) : historyState.error ? (
          <ErrorState
            message={historyState.error}
            onRetry={historyState.retry}
            compact
          />
        ) : historyState.data && historyState.data.length > 0 ? (
          <Card className="p-6 pb-10">
            <TrendChart series={historyState.data} />
          </Card>
        ) : !kpisState.error ? (
          <Card className="p-8 text-sm text-text-secondary">
            No trend history available.
          </Card>
        ) : null}
      </section>

      {/* Narrative */}
      <section>
        <SectionLabel className="mb-4">Intelligence Brief</SectionLabel>
        {narrativeState.loading ? (
          <PanelSkeleton lines={6} />
        ) : narrativeState.error ? (
          <ErrorState
            message={narrativeState.error}
            onRetry={narrativeState.retry}
            compact
          />
        ) : section ? (
          <NarrativePanel section={section} />
        ) : (
          <Card className="p-8 text-sm text-text-secondary">
            No commentary drafted for this module in {fiscalYear}.
          </Card>
        )}
      </section>

      <LineageDrawer kpi={selectedKpi} onClose={() => setSelectedKpi(null)} />
    </>
  );
}

/** Shared page for the five analytical modules. */
export function ModulePage({ config }: { config: ModulePageConfig }) {
  const { bank } = useBank();
  return (
    <>
      <PageHeading
        label={config.label}
        title={config.title}
        subtitle={
          bank ? `${bank.name} — ${config.subtitle}` : config.subtitle
        }
      />
      <PageGate>
        {(bank, fiscalYear) => (
          <ModuleBody
            key={`${bank.id}-${fiscalYear}`}
            bank={bank}
            fiscalYear={fiscalYear}
            config={config}
          />
        )}
      </PageGate>
    </>
  );
}
