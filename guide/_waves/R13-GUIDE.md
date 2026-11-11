# R13-GUIDE: one wrong row in the troubleshooting page

Read `guide/AGENTS.md`. Reader: an operator running refiroo in production.

The row `ENGINE_UNREACHABLE` in the browser in `src/content/docs/run/troubleshooting.md` (table "Requests and
startup") says that code in the browser means DNS, TLS or proxy trouble. That is not what an operator sees.

**What is true (code evidence).**

- `ENGINE_UNREACHABLE` exists only in the development server's proxy: `frontend/vite.config.ts` (the `proxy.on("error")`
  handler writes `502` with `{"error": {"code": "ENGINE_UNREACHABLE", ...}}` when `npm run dev` cannot reach the engine).
  Nothing in `backend/` or in the production image produces it.
- In production the browser's requests to the engine's paths (`/api/`, `/oauth/`, `/mcp`, `/.well-known/`, `/docs`,
  `/openapi.json`, `/health`) go through the web container's nginx (`frontend/nginx/snippets/locations.inc.template`,
  `proxy_pass ${ENGINE_UPSTREAM}`; there is no `error_page`). When the engine is stopped, restarting or not reachable
  from web, nginx answers its own plain `502 Bad Gateway` page (HTML, not the engine's JSON error body); a `504 Gateway
  Time-out` when the engine accepts but does not answer within the proxy's time limit. With automatic HTTPS Caddy sits in
  front of web (`compose.acme.yml`, `caddy/`): if web itself is down, Caddy answers a `502`.
- If the browser cannot reach the site at all (DNS, TLS, no route), no refiroo code runs and the browser shows its own
  error page; that is a different symptom from the row.

**What to do.** Replace that row with the production symptom: a plain `502 Bad Gateway` (or `504`) page, or a failing
request with no engine error body, where the engine is down or web cannot reach it. Meaning and recovery: check the
engine's liveness (`/health/live` from the host or `docker compose ps` / logs for the engine service), that web's
upstream setting names the engine, and, after an upgrade, that the engine finished starting. Keep to what
`docs/OPERATIONS.md` and the Compose files say; use the page's existing wording style and links. Keep `ENGINE_UNREACHABLE`
out of the operator page (it belongs to `npm run dev`); if a developer-facing page in `src/content/docs/` already
describes the development server and its proxy, a one-line mention of the code there is right, otherwise add nothing.
Keep everything else as it is.

## Files you may edit

- `src/content/docs/run/troubleshooting.md`
- `_coverage/notes/R13-GUIDE/**`
- `_waves/progress/R13-GUIDE.md`

## Report

The row's new text; anything unsure.
