# C5: complete "Run refiroo"

Read `guide/AGENTS.md`, then `_waves/COMPLETE-COMMON.md`. Reader: operators. Pages carry the commands an
operator types and the settings that matter, each with what it changes, its default and when to change it.

The section was written last and has not been checked against the record. Check every page against its
sources (`OUTLINE.md` section 5, `docs/OPERATIONS.md`, `compose.yml`, `.env.example`,
`backend/Dockerfile`, `backend/app/config.py`, the commands in `backend/app/cli/`) and correct what is
wrong. Then cover every `run` row (in `_waves/coverage/run.md`): every setting, command, startup refusal and
message an operator meets. The section's groups in `sidebar/run.mjs` (Install, Configure, Operate,
Maintain, Before going live) are set; a new page goes in the fitting group.

The pages link to screenshots `run-jobs`, `run-backup-rehearsal`, `run-deployment` and `run-operations`
that do not exist yet: add them to `_waves/screens-wanted/C5-RUN.md`. `npm run check:links` lists pages linked but not
written: write them or remove the link. `run/ai.md` and `run/set-up-ai.md` belong to the AI wave after
0.16: link to them, do not rewrite them.

## Files you may edit

- `src/content/docs/run/*.md` (except `ai.md` and `set-up-ai.md`)
- `sidebar/run.mjs`
- `_waves/coverage/run.md`
- `_waves/screens-wanted/C5-RUN.md`
- `_coverage/notes/C5-RUN/**` (working notes)

## Report

As `COMPLETE-COMMON.md` says.
