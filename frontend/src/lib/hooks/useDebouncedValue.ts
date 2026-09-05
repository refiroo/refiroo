import { useEffect, useState } from "react";

/**
 * The value, held back until it has stopped changing for `delayMs`.
 *
 * Used to keep a search box responsive while the request it drives fires once the user pauses.
 * The first value is returned immediately, so a component renders its initial query without
 * waiting out the delay.
 */
export function useDebouncedValue<T>(value: T, delayMs = 250): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
