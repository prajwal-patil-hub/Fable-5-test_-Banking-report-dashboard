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
  const { bank, fiscalYear, loading, error, retry } = useBank();

  if (error && (!bank || !fiscalYear)) {
    return <ErrorState message={error} onRetry={retry} />;
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
