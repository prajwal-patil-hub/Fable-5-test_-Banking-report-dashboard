"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, type Bank, type Currency } from "@/lib/api";

interface BankContextValue {
  banks: Bank[];
  bank: Bank | null;
  years: string[];
  fiscalYear: string | null;
  /** Display currency for monetary KPIs (₹ crore by default). */
  currency: Currency;
  setBankId: (id: number) => void;
  setFiscalYear: (fy: string) => void;
  setCurrency: (currency: Currency) => void;
  /** True while loading the bank list or year list. */
  loading: boolean;
  /** Error loading banks/years (typically: backend down). */
  error: string | null;
  retry: () => void;
}

const BankContext = createContext<BankContextValue | null>(null);

export function BankProvider({ children }: { children: ReactNode }) {
  const [banks, setBanks] = useState<Bank[]>([]);
  const [bankId, setBankId] = useState<number | null>(null);
  const [years, setYears] = useState<string[]>([]);
  const [fiscalYear, setFiscalYear] = useState<string | null>(null);
  const [currency, setCurrency] = useState<Currency>("inr");
  const [loadingBanks, setLoadingBanks] = useState(true);
  const [loadingYears, setLoadingYears] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  // Load banks (once, retried via tick)
  useEffect(() => {
    let alive = true;
    setLoadingBanks(true);
    setError(null);
    api
      .getBanks()
      .then((res) => {
        if (!alive) return;
        setBanks(res.banks);
        // Default to the first bank if nothing selected yet.
        setBankId((current) =>
          current !== null && res.banks.some((b) => b.id === current)
            ? current
            : (res.banks[0]?.id ?? null),
        );
        setLoadingBanks(false);
      })
      .catch((err: unknown) => {
        if (!alive) return;
        setError(err instanceof Error ? err.message : String(err));
        setLoadingBanks(false);
      });
    return () => {
      alive = false;
    };
  }, [tick]);

  // Load fiscal years whenever the bank changes
  useEffect(() => {
    if (bankId === null) {
      setYears([]);
      setFiscalYear(null);
      return;
    }
    let alive = true;
    setLoadingYears(true);
    api
      .getYears(bankId)
      .then((res) => {
        if (!alive) return;
        setYears(res.fiscal_years);
        // Default to the latest year (list is ascending).
        setFiscalYear((current) =>
          current !== null && res.fiscal_years.includes(current)
            ? current
            : (res.fiscal_years[res.fiscal_years.length - 1] ?? null),
        );
        setLoadingYears(false);
      })
      .catch((err: unknown) => {
        if (!alive) return;
        setError(err instanceof Error ? err.message : String(err));
        setLoadingYears(false);
      });
    return () => {
      alive = false;
    };
  }, [bankId, tick]);

  const retry = useCallback(() => setTick((t) => t + 1), []);

  const value = useMemo<BankContextValue>(() => {
    const bank = banks.find((b) => b.id === bankId) ?? null;
    return {
      banks,
      bank,
      years,
      fiscalYear,
      currency,
      setBankId: (id: number) => setBankId(id),
      setFiscalYear: (fy: string) => setFiscalYear(fy),
      setCurrency: (c: Currency) => setCurrency(c),
      loading: loadingBanks || loadingYears,
      error,
      retry,
    };
  }, [
    banks,
    bankId,
    years,
    fiscalYear,
    currency,
    loadingBanks,
    loadingYears,
    error,
    retry,
  ]);

  return <BankContext.Provider value={value}>{children}</BankContext.Provider>;
}

export function useBank(): BankContextValue {
  const ctx = useContext(BankContext);
  if (!ctx) throw new Error("useBank must be used within <BankProvider>");
  return ctx;
}
