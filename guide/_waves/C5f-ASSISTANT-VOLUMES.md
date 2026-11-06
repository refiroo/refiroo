# C5f: the assistant's volumes in Docker installations

Read `guide/AGENTS.md`. Reader: an operator running refiroo with Docker Compose.

`compose.yml` now puts the assistant's task folders (`assistant`, at `data/assistant`) and its Claude Code configuration
and session logs (`assistant-claude`, at `data/assistant-claude`) on named volumes next to `job-files`
(`backend/Dockerfile` VOLUME; `docs/OPERATIONS.md`, image table, the mounts under `data/` and the Backups paragraph,
are the facts). Before, a recreated container lost every open assistant task's folder, so the task could not go on.

Bring every page under `src/content/docs/run/` that lists Compose's volumes, or says what a backup, an upgrade or
`docker compose down -v` keeps or loses, in line with the files: which volumes exist, what each holds, that a backup
need not include the two assistant volumes (losing them loses open tasks' folders and session logs, not records), and
that an upgrade keeps them. Find the pages with grep (`job-files`, `volume`). Keep everything else as it is.

## Files you may edit

- `src/content/docs/run/*.md`
- `_coverage/notes/C5f-ASSISTANT-VOLUMES/**`
- `_waves/progress/C5f-ASSISTANT-VOLUMES.md`

## Report

Pages changed and what each now says; anything unsure.
