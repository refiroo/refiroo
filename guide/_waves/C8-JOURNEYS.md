# C8: write "User journeys"

Read `guide/AGENTS.md`, then `_waves/COMPLETE-COMMON.md`. Readers: everyone.

A new section, `journeys/`, already declared in `astro.config.mjs`; list its pages in `sidebar/journeys.mjs`. It lists every user journey of refiroo in categories, from the
`journeys` rows (in `_waves/coverage/journeys.md`) (source: `docs/product-functionality/USER_JOURNEYS.md`, all of
them except those marked after 0.16, which get a one-line entry saying so only if their pages exist).

- `journeys/index.md` ("All user journeys"): the categories, each with its journeys, one line each, linked.
- One documentation page per category (`journeys/<category>.md`), and in it each journey as a section:
  who does it and why, what happens from start to end in plain words (in the example world where it helps,
  marked as the example), and links to the documentation pages and guides it uses, in the order the reader
  meets them. A journey does not repeat its guides' steps; it connects them.

If a journey needs a page that does not exist, link the planned path only if it exists now; otherwise name
the gap in your report.

## Files you may edit

- `src/content/docs/journeys/*.md`
- `sidebar/journeys.mjs` (new)
- `_waves/coverage/journeys.md`
- `_coverage/notes/C8-JOURNEYS/**` (working notes)

## Report

As `COMPLETE-COMMON.md` says, plus the categories chosen and why.
