import { useEffect, useRef, useState } from "react";

/**
 * Loads data from the backend.
 *   const { data, error, loading, updatedAt, reload } = useApi(() => api.buildings(), [], { interval: 5000 });
 * - `deps`     : when these change the request runs again
 * - `interval` : optional polling in ms (used for near-real-time pages)
 * - `enabled`  : set to false to skip the request (data is reset to null)
 * `loading` is only true until the first answer; during polling the old data stays visible.
 */
export function useApi(fetcher, deps = [], { interval = 0, enabled = true } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: enabled, updatedAt: null });
  const [tick, setTick] = useState(0);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  useEffect(() => {
    if (!enabled) {
      setState({ data: null, error: null, loading: false, updatedAt: null });
      return undefined;
    }
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));

    const run = async () => {
      try {
        const data = await fetcherRef.current();
        if (!cancelled) setState({ data, error: null, loading: false, updatedAt: new Date() });
      } catch (error) {
        if (!cancelled) setState((s) => ({ ...s, error, loading: false }));
      }
    };
    run();
    const timer = interval ? setInterval(run, interval) : null;
    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, interval, enabled, tick]);

  return { ...state, reload: () => setTick((t) => t + 1) };
}
