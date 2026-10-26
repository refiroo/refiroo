/**
 * The engine this browser application calls: the address the page was opened at, which forwards the
 * engine's paths (the Vite dev server, the `web` image, an organisation's proxy), unless `VITE_API_URL`
 * names an engine on another address when the frontend is built (0.12 DP1, D404).
 */
export const API_URL: string =
  import.meta.env.VITE_API_URL || (typeof window === "undefined" ? "http://localhost:8000" : window.location.origin);
