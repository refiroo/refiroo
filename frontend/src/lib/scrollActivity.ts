/**
 * Whether anything on the page scrolled a moment ago (0.12 LS1, D373). Rows moving under a still
 * pointer fire `pointerover` as a list scrolls; a table reads this to leave those alone, acting on
 * the pointer's own movement instead. One passive listener for the page, added on first use.
 */

const SCROLL_QUIET_MS = 200;

let last = Number.NEGATIVE_INFINITY;
let listening = false;

function listen() {
  if (listening || typeof window === "undefined") return;
  listening = true;
  window.addEventListener(
    "scroll",
    () => {
      last = performance.now();
    },
    { capture: true, passive: true },
  );
}

export function recentlyScrolled(): boolean {
  listen();
  return performance.now() - last < SCROLL_QUIET_MS;
}

/** Starts noting scrolls before the first question, so the first rows scrolled past count too. */
export function watchScrolling() {
  listen();
}
