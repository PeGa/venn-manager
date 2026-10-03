/**
 * Debounce a fast-changing value before it reaches a query key.
 *
 * Every keystroke in a search box would otherwise fire a request, and the
 * backend does the filtering server-side (API_SURFACE.md § GET /records).
 */
import { useEffect, useState } from "preact/hooks";

export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
