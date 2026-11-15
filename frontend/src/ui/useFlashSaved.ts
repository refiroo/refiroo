import { useCallback, useEffect, useState } from "react";

/** How long a "Saved" stays beside what was saved (SR-D2: the same everywhere). */
export const SAVED_FLASH_MS = 2500;

/**
 * A confirmation that is news for a moment (SR5): `flash(value)` shows `value` until it goes by itself or
 * `clear` is called. A value that names what was saved (a cell's key, a sentence) lets one flash serve several
 * places; `flash()` alone is a plain yes. A new flash restarts the time.
 */
export function useFlashSaved<T = true>() {
  const [saved, setSaved] = useState<{ value: T } | undefined>();
  useEffect(() => {
    if (!saved) return;
    const timer = window.setTimeout(() => setSaved(undefined), SAVED_FLASH_MS);
    return () => window.clearTimeout(timer);
  }, [saved]);
  const flash = useCallback((value: T = true as T) => setSaved({ value }), []);
  const clear = useCallback(() => setSaved(undefined), []);
  return { saved: saved?.value, flash, clear };
}
