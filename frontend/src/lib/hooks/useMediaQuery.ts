import { useSyncExternalStore } from "react";

/** The width below which the rail is a drawer and the shell is laid out for a phone. */
export const PHONE_WIDTH = "(max-width: 760px)";

/** Whether a CSS media query matches, following it as the window changes (false without `matchMedia`). */
export function useMediaQuery(query: string) {
  return useSyncExternalStore(
    (update) => {
      const list = window.matchMedia?.(query);
      list?.addEventListener("change", update);
      return () => list?.removeEventListener("change", update);
    },
    () => window.matchMedia?.(query).matches === true,
    () => false,
  );
}
