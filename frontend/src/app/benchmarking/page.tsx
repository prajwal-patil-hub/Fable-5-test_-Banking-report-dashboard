"use client";

import { useEffect, useState } from "react";
import { api, type Bank, type BenchmarkingSummaryKpi } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useBank } from "@/context/BankContext";
import { formatValue } from "@/lib/format";
import { Card, PageHeading, SectionLabel } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ChartSkeleton, Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { PeerBarChart } from "@/components/charts/PeerBarChart";
import { PageGate } from "@/components/PageGate";

function SummaryTile({
  kpi,
  bankId,
  active,
  onSelect,
}: {
  kpi: BenchmarkingSummaryKpi;
  bankId: number;
  active: boolean;
  onSelect: (code: string) => void;
}) {
  const own = kpi.peers.find((p) => p.bank_id === bankId);
  return (
    <Card
      className={`cursor-pointer p-5 transition-colors hover:border-gold/60 ${
        active ? "border-gold/70" : ""
      }`}
      onClick={() => onSelect(kpi.kpi_code)}
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <span className="text-xs uppercase tracking-[0.2em] text-text-secondary">
          {kpi.name}
        </span>
        {own ? <Badge tone="gold">Rank {own.rank}</Badge> : null}
      </div>
      <PeerBarChart
        peers={kpi.peers}
        selectedBankId={bankId}
        unit={kpi.unit}
        height={Math.max(120, kpi.peers.length * 26)}
      />
    </Card>
  );
}

function DetailSection({
  bank,
  fiscalYear,
  kpiCode,
}: {
  bank: Bank;
  fiscalYear: string;
  kpiCode: string;
}) {
  const state = useApi(
    () => api.getBenchmarking(kpiCode, fiscalYear),
    [kpiCode, fiscalYear],
  );

  if (state.loading) return <ChartSkeleton className="h-[28rem]" />;
  if (state.error)
    return <ErrorState message={state.error} onRetry={state.retry} compact />;
  if (!state.data) return null;

  const data = state.data;
  const sorted = [...data.peers].sort((a, b) => a.rank - b.rank);
  const statCells = [
    { label: "Best", value: data.direction === "lower_is_better" ? data.stats.min : data.stats.max },
    { label: "Median", value: data.stats.median },
    { label: "Mean", value: data.stats.mean },
    { label: "Worst", value: data.direction === "lower_is_better" ? data.stats.max : data.stats.min },
  ];

  return (
    <div className="grid gap-4 xl:grid-cols-5">
      <Card className="p-6 xl:col-span-3">
        <div className="mb-4 flex items-baseline justify-between">
          <h3 className="font-serif text-xl text-text-primary">{data.name}</h3>
          <span className="text-[10px] uppercase tracking-[0.2em] text-text-secondary">
            {data.fiscal_year} ·{" "}
            {data.direction === "lower_is_better"
              ? "Lower is better"
              : data.direction === "higher_is_better"
                ? "Higher is better"
                : "Neutral"}
          </span>
        </div>
        <PeerBarChart
          peers={data.peers}
          selectedBankId={bank.id}
          unit={data.unit}
          height={Math.max(220, data.peers.length * 34)}
        />
        <div className="mt-5 grid grid-cols-4 divide-x divide-border border-t border-border pt-4">
          {statCells.map((cell) => (
            <div key={cell.label} className="px-4 first:pl-0">
              <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary">
                {cell.label}
              </div>
              <div className="mt-1 font-serif text-lg text-text-primary">
                {formatValue(cell.value, data.unit)}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card className="overflow-hidden xl:col-span-2">
        <div className="border-b border-border px-6 py-4">
          <SectionLabel>Peer Ranking</SectionLabel>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[10px] uppercase tracking-[0.2em] text-text-secondary">
              <th className="px-6 py-3 font-normal">Rank</th>
              <th className="px-3 py-3 font-normal">Institution</th>
              <th className="px-3 py-3 text-right font-normal">Value</th>
              <th className="px-6 py-3 text-right font-normal">Percentile</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((peer) => {
              const isOwn = peer.bank_id === bank.id;
              return (
                <tr
                  key={peer.bank_id}
                  className={`border-b border-border/50 last:border-0 ${
                    isOwn ? "bg-gold/10" : ""
                  }`}
                >
                  <td className="px-6 py-3 font-serif text-base text-gold">
                    {peer.rank}
                  </td>
                  <td
                    className={`px-3 py-3 ${
                      isOwn ? "text-gold" : "text-text-primary"
                    }`}
                  >
                    {peer.bank_name}
                    {isOwn ? (
                      <span className="ml-2 text-[9px] uppercase tracking-[0.2em] text-bronze">
                        Selected
                      </span>
                    ) : null}
                  </td>
                  <td className="px-3 py-3 text-right font-serif">
                    {formatValue(peer.value, data.unit)}
                  </td>
                  <td className="px-6 py-3 text-right text-text-secondary">
                    {peer.percentile.toFixed(0)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function BenchmarkingBody({
  bank,
  fiscalYear,
}: {
  bank: Bank;
  fiscalYear: string;
}) {
  const summaryState = useApi(
    () => api.getBenchmarkingSummary(fiscalYear),
    [fiscalYear],
  );
  const [selectedCode, setSelectedCode] = useState<string | null>(null);

  const kpis = summaryState.data?.kpis ?? [];
  const activeCode =
    selectedCode && kpis.some((k) => k.kpi_code === selectedCode)
      ? selectedCode
      : (kpis[0]?.kpi_code ?? null);

  // Reset detail selection when the year changes.
  useEffect(() => {
    setSelectedCode(null);
  }, [fiscalYear]);

  return (
    <>
      {/* Detailed single-KPI view with picker */}
      <section className="mb-10">
        <div className="mb-4 flex items-center justify-between gap-6">
          <SectionLabel>Detailed Comparison · {fiscalYear}</SectionLabel>
          {kpis.length > 0 ? (
            <label className="flex items-center gap-3">
              <span className="text-[10px] uppercase tracking-[0.25em] text-text-secondary">
                Indicator
              </span>
              <select
                className="sovereign-select min-w-56 border border-border bg-ink-2 px-3 py-1.5 pr-8 text-sm text-text-primary outline-none hover:border-gold/60 focus:border-gold"
                value={activeCode ?? ""}
                onChange={(e) => setSelectedCode(e.target.value)}
              >
                {kpis.map((k) => (
                  <option key={k.kpi_code} value={k.kpi_code}>
                    {k.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
        {summaryState.loading ? (
          <ChartSkeleton className="h-[28rem]" />
        ) : summaryState.error ? (
          <ErrorState
            message={summaryState.error}
            onRetry={summaryState.retry}
          />
        ) : activeCode ? (
          <DetailSection
            bank={bank}
            fiscalYear={fiscalYear}
            kpiCode={activeCode}
          />
        ) : (
          <Card className="p-8 text-sm text-text-secondary">
            No benchmarkable indicators for {fiscalYear}.
          </Card>
        )}
      </section>

      {/* Full summary grid */}
      <section>
        <SectionLabel className="mb-4">Peer Standing — All Indicators</SectionLabel>
        {summaryState.loading ? (
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-56 w-full" />
            ))}
          </div>
        ) : summaryState.error ? null : kpis.length > 0 ? (
          <div className="grid grid-cols-2 gap-4 xl:grid-cols-3">
            {kpis.map((kpi) => (
              <SummaryTile
                key={kpi.kpi_code}
                kpi={kpi}
                bankId={bank.id}
                active={kpi.kpi_code === activeCode}
                onSelect={setSelectedCode}
              />
            ))}
          </div>
        ) : null}
      </section>
    </>
  );
}

export default function BenchmarkingPage() {
  const { bank } = useBank();
  return (
    <>
      <PageHeading
        label="Market · Benchmarking"
        title="Peer Benchmarking"
        subtitle={
          bank
            ? `${bank.name} measured against its peer set — rankings, percentiles and distribution statistics.`
            : "Rankings, percentiles and distribution statistics across the peer set."
        }
      />
      <PageGate>
        {(bank, fiscalYear) => (
          <BenchmarkingBody
            key={`${bank.id}-${fiscalYear}`}
            bank={bank}
            fiscalYear={fiscalYear}
          />
        )}
      </PageGate>
    </>
  );
}
