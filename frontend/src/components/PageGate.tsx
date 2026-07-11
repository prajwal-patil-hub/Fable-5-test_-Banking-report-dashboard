"use client";

import type { ReactNode } from "react";
import { useBank } from "@/context/BankContext";
import { ErrorState } from "@/components/ui/ErrorState";
import { KpiCardSkeleton, PanelSkeleton } from "@/components/ui/Skeleton";
import type { Bank } from "@/lib/api";

/**
 * Gates a page on the global bank/year selection being available.
 * Shows skeletons while loading and a retryable error when the
 * backend is unreachable.
 */
export function PageGate({
  children,
}: {
  children: (bank: Bank, fiscalYear: string) => ReactNode;
}) {
  const { bank, fiscalYear, years, loading, error, retry } = useBank();

  if (error && (!bank || !fiscalYear)) {
    return <ErrorState message={error} onRetry={retry} />;
  }
  // Roster institution with no ingested documents yet: an explicit empty
  // state, not an endless skeleton.
  if (!loading && bank && years.length === 0) {
    return (
      <div className="border border-border bg-card px-8 py-16 text-center">
        <div className="font-serif text-xl text-text-primary">
          No data yet for {bank.name}
        </div>
        <p className="mx-auto mt-3 max-w-lg text-sm text-text-secondary">
          Upload this institution&apos;s annual report on the Documents page —
          extraction, validation and analytics run automatically, and every
          figure keeps a link back to its source page.
        </p>
      </div>
    );
  }
  if (loading || !bank || !fiscalYear) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <KpiCardSkeleton key={i} />
          ))}
        </div>
        <PanelSkeleton lines={5} />
      </div>
    );
  }
  return <>{children(bank, fiscalYear)}</>;
}
