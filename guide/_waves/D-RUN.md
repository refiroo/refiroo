# D-RUN: "Run refiroo" documented in full

Read `guide/AGENTS.md`, `_waves/COMPLETE-COMMON.md` and `_waves/DEPTH-COMMON.md`, in that order. Reader: operators, who install, run, upgrade and back up refiroo for their organisation and are not its developers.

Your scope: the entries of section `run` in `_coverage/inventory/*.json` (those still in `_coverage/inventory/uncovered.md`
first), then every page of the section and its guides, each held against the depth questions of `DEPTH-COMMON.md`.

**Also in this wave.** The owner confirmed on their own server on 2026-11-06 that port 443 alone gets the Let's Encrypt certificate (TLS-ALPN): only 443 must be reachable; port 80 only redirects people who type `http://` and may be left closed. Correct every page that says 80 and 443 must be open (`run/https.md`, `run/install-with-compose.md` and any other). The Compose and Caddy file comments and `docs/OPERATIONS.md` are corrected by Claude, not by you.

Typical depth gaps to look for, as examples only: certificate renewal and its failure, key and secret rotation, database growth and pruning, job files and their volume, upgrading between releases and rolling back, moving to a new server, restoring a backup to a new host, log and metric retention, what each Compose variable does (`POSTGRES_*`, `ENGINE_UPSTREAM`) and each Caddyfile directive.

## Files you may edit

- `src/content/docs/run/**`
- `sidebar/run.mjs`
- `_waves/coverage/run.md`
- `_coverage/exclusions.md` (only lines for section `run`)
- `_waves/screens-wanted/D-RUN.md`
- `_coverage/notes/D-RUN/**` (working notes)

## Report

As `DEPTH-COMMON.md` says.
