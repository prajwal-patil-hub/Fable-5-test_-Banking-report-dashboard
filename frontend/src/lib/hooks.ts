"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  retry: () => void;
}

/**
 * Minimal client-side data hook around a fetcher. Pass `null` to skip
 * (e.g. while the bank/year selection has not loaded yet).
 *
 * `deps` should capture everything the fetcher closes over.
 */
export function useApi<T>(
  fetcher: (() => Promise<T>) | null,
  deps: readonly unknown[],
): ApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(fetcher !== null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    const fn = fetcherRef.current;
    if (!fn) {
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }
    let alive = true;
    setLoading(true);
    setError(null);
    fn()
      .then((result) => {
        if (!alive) return;
        setData(result);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (!alive) return;
        setData(null);
        setError(err instanceof Error ? err.message : String(err));
        setLoading(false);
      });
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick, fetcher === null]);

  const retry = useCallback(() => setTick((t) => t + 1), []);

  return { data, loading, error, retry };
}
