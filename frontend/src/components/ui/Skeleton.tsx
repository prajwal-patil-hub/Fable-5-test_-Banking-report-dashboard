export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`shimmer border border-border/50 ${className}`} />;
}

export function KpiCardSkeleton() {
  return (
    <div className="border border-border bg-card/80 p-5">
      <Skeleton className="mb-4 h-3 w-2/3" />
      <Skeleton className="mb-3 h-9 w-1/2" />
      <Skeleton className="h-3 w-1/3" />
    </div>
  );
}

export function PanelSkeleton({ lines = 4 }: { lines?: number }) {
  return (
    <div className="border border-border bg-card/80 p-6">
      <Skeleton className="mb-5 h-3 w-40" />
      <div className="space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton key={i} className="h-3.5 w-full" />
        ))}
      </div>
    </div>
  );
}

export function ChartSkeleton({ className = "h-72" }: { className?: string }) {
  return (
    <div className={`border border-border bg-card/80 p-6 ${className}`}>
      <Skeleton className="mb-5 h-3 w-48" />
      <Skeleton className="h-[calc(100%-2.5rem)] w-full" />
    </div>
  );
}
