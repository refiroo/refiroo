## 2026-11-04T02:40:57+01:00 — source checks complete

Checked the command paths, settings and People labels for `src/content/docs/run/install-with-compose.md`; evidence is in `_coverage/notes/C5d-DEPLOY/evidence.md`. No steering file existed. The page needs readiness as well as liveness checks, a paused-write backup pair, and wording that allows Caddy’s ZeroSSL fallback.

## 2026-11-04T02:41:52+01:00 — steps 1–4 written

`src/content/docs/run/install-with-compose.md` now covers prerequisites, a tagged checkout, optional GitHub App access and generated settings with off-server key protection. No steering file exists. Private-repository readers are directed to authenticate before cloning; the system route is spelled `/api/v1/system`, as served by the application. Live GitHub authentication remains untested.

## 2026-11-04T02:43:07+01:00 — deployment page and sidebar complete

Finished `src/content/docs/run/install-with-compose.md` steps 5–8: persistent shell overlay selection, automatic HTTPS, readiness, first administrator and People links, consistent backup pair and tagged upgrade. Preserved the existing settings, alternate environment, image paths and safe-stop guidance; updated `sidebar/run.mjs` to the new title. No steering file existed. Real certificate issuance and production backup/upgrade commands have not been run.

## 2026-11-04T02:44:22+01:00 — validation complete

`src/content/docs/run/install-with-compose.md` and `sidebar/run.mjs` are complete. The isolated `GUIDE_OUT=_build/C5d-DEPLOY npm run build` passed (247 pages); sidebar syntax, diff whitespace, 20 Bash blocks, exact token script, secret formats, 17 internal links and the rendered eight steps passed. No steering file existed; no screenshots are needed. Live deployment, App authentication, certificate issuance and backup/upgrade execution remain unverified; evidence and the build log are under `_coverage/notes/C5d-DEPLOY/`.

Build warnings: `run/https.md` uses unrecognised `caddyfile` syntax highlighting (falls back to plain text), and `/404` has a route conflict. Both are outside this wave’s edit scope and the build passed.
