/**
 * After a new deployment the hashed chunks an open tab still points at are gone, so a code-split page
 * (Settings, notifications, change set review) fails to load. Vite reports that as `vite:preloadError`:
 * the page is reloaded once to fetch the new build. A marker in session storage stops a reload loop when
 * the chunk is missing for another reason; it is cleared once the page has stayed up.
 */

const MARKER = "refiroo.staleChunkReload";
const SETTLE_MS = 10_000;

export function reloadOnStaleChunk(reload: () => void = () => window.location.reload()) {
  const onError = (event: Event) => {
    try {
      if (window.sessionStorage.getItem(MARKER) !== null) return;
      window.sessionStorage.setItem(MARKER, String(Date.now()));
    } catch {
      // Without storage a loop cannot be guarded: leave the error to the error boundary.
      return;
    }
    event.preventDefault();
    reload();
  };
  window.addEventListener("vite:preloadError", onError);
  const timer = window.setTimeout(() => {
    try {
      window.sessionStorage.removeItem(MARKER);
    } catch {
      // Nothing to clear.
    }
  }, SETTLE_MS);
  return () => {
    window.removeEventListener("vite:preloadError", onError);
    window.clearTimeout(timer);
  };
}
