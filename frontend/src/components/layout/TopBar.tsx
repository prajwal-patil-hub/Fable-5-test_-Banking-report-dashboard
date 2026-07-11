"use client";

import { useBank } from "@/context/BankContext";
import { Skeleton } from "@/components/ui/Skeleton";
import { SEGMENT_LABELS, SEGMENT_ORDER } from "@/lib/segments";

function SelectShell({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex items-center gap-3">
      <span className="text-[10px] uppercase tracking-[0.25em] text-text-secondary">
        {label}
      </span>
      {children}
    </label>
  );
}

const selectClass =
  "sovereign-select min-w-44 border border-border bg-ink-2 px-3 py-1.5 pr-8 text-sm text-text-primary outline-none transition-colors hover:border-gold/60 focus:border-gold";

export function TopBar() {
  const {
    banks, bank, years, fiscalYear, currency,
    setBankId, setFiscalYear, setCurrency, loading, error,
  } = useBank();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-ink/95 px-8 backdrop-blur">
      <div className="text-xs uppercase tracking-[0.25em] text-text-secondary">
        Annual Report Intelligence
        {bank ? (
          <span className="ml-3 text-gold">
            · {bank.name}
            {fiscalYear ? ` · ${fiscalYear}` : ""}
          </span>
        ) : null}
      </div>

      <div className="flex items-center gap-6">
        {error && banks.length === 0 ? (
          <span
            className="max-w-md truncate text-xs text-risk"
            title={error}
          >
            {error}
          </span>
        ) : loading && banks.length === 0 ? (
          <div className="flex items-center gap-6">
            <Skeleton className="h-8 w-44" />
            <Skeleton className="h-8 w-28" />
          </div>
        ) : (
          <>
            <SelectShell label="Institution">
              <select
                className={selectClass}
                value={bank?.id ?? ""}
                onChange={(e) => setBankId(Number(e.target.value))}
              >
                {SEGMENT_ORDER.filter((seg) =>
                  banks.some((b) => b.segment === seg),
                ).map((seg) => (
                  <optgroup key={seg} label={SEGMENT_LABELS[seg]}>
                    {banks
                      .filter((b) => b.segment === seg)
                      .map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.name}
                          {b.is_demo
                            ? " (demo)"
                            : b.has_data
                              ? ""
                              : " — no data yet"}
                        </option>
                      ))}
                  </optgroup>
                ))}
              </select>
            </SelectShell>
            <SelectShell label="Fiscal Year">
              <select
                className={`${selectClass} min-w-28`}
                value={fiscalYear ?? ""}
                onChange={(e) => setFiscalYear(e.target.value)}
                disabled={years.length === 0}
              >
                {[...years].reverse().map((fy) => (
                  <option key={fy} value={fy}>
                    {fy}
                  </option>
                ))}
              </select>
            </SelectShell>
            <div
              className="flex items-center border border-border"
              role="group"
              aria-label="Display currency"
            >
              {([["inr", "₹ Cr"], ["usd", "$ mn"]] as const).map(([code, label]) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => setCurrency(code)}
                  className={`px-3 py-1.5 text-xs tracking-wide transition-colors ${
                    currency === code
                      ? "bg-gold/15 text-gold"
                      : "text-text-secondary hover:text-text-primary"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </header>
  );
}
