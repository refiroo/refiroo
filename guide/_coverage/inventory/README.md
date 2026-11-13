# Inventory

What refiroo can do, read from the code, and the check that the guide names each item (CP).

    backend/.venv/bin/python guide/tools/inventory.py    # writes <kind>.json and gaps.md; needs node, no database, no server
    cd guide && node tools/check.mjs coverage             # prints counts per kind and section; writes uncovered.md; exit 1 while any is uncovered

`inventory.py` calls `guide/tools/inventory-ts.mjs` for the frontend (it uses the TypeScript compiler in
`frontend/node_modules`). Run the inventory again after code changes, then the check. An entry is covered when its key,
alias or a label stands on a page under `src/content/docs` (see the comment above `coverage` in `tools/check.mjs`);
an item the guide deliberately omits gets a line `kind key — reason` in `../exclusions.md`.
The coverage check is not part of `npm run verify` yet.

Kinds added by R17-F31: `mail-kind` (message kinds in `engine/mail/templates.py`), `search-field` (a Find/Search box
of the frontend) and `build-arg` (Dockerfile `ARG`s). Text inside headings counts for no label, and a label that is one
common word counts only on a page that also names one of the entry's `commonContext` words.
