# C11 fix: what the fresh reader got stuck on

Read `guide/AGENTS.md`. Readers: the guide's readers, as each page names.

## Why

A fresh reader (wave C11-READER, DOC11's weaker check) followed the quick start, every journey and the
production checklist using only the built guide. Their findings are in
`_coverage/notes/C11-READER/findings.md`.

## What to do

- Fix every finding that the guide's pages can fix, in the page where the reader got stuck, and check
  the fix against the product (`backend/app/`, `frontend/src/`, `docs/`): the code wins.
- A finding that is a product defect (the product does something the guide cannot honestly describe
  around) is not fixed in the page by working around it: list it in your report with the evidence.
- A finding you judge wrong (the page already says it, the reader misread): say why in the report.
- No new pages unless a finding cannot be fixed without one; no new pictures.

## Files you may edit

- `src/content/docs/**/*.md`
- `src/content/docs/**/*.mdx`
- `_coverage/notes/C11-FIX/**`
- `_waves/progress/C11-FIX.md`

## Report

Per finding (by its number): fixed (page and what changed), a product defect (evidence), or not
changed (why).
