# R-OPS: reconcile the documentation with its source, section by section

Read `guide/AGENTS.md` and `_waves/COMPLETE-COMMON.md`.

The person who owns refiroo finds the documentation incomplete and, in places, not correct: pages name a
topic but leave out what a reader needs (example: automatic HTTPS without Let's Encrypt, Caddy, the ACME
challenge, the certificate volume, renewal and what to do when it fails). Naming things is not enough: the
pages must carry the full, correct content of the product's own documents for their readers.

**Sources:** `docs/OPERATIONS.md` (all of it), then `compose.yml`, `compose.acme.yml`, `caddy/Caddyfile`, `.env.example`, `backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx/`, `backend/app/config.py`, `backend/app/cli/`.

**Pages you own:** Run refiroo (`run/`), and the administrator side of sign-in, mail, webhooks and clients in Administer access (`administer/`, `guide/administer/`).

Work through each source **heading by heading, in order**. For each heading:
1. Read the section and list every fact a reader of your pages needs from it: what it is, how it works, every
   setting, default, limit, command, message, file, port, name, version, rule, state, exception and
   procedure.
2. Find each fact on the pages. Missing → write it where it belongs. Wrong or out of date → correct the page,
   after checking the code (the code wins over the document; where they disagree, say so in your ledger).
   Present but too thin to act on → expand it to the standard of AGENTS.md.
3. Facts that are not for readers (delivery history, decision numbers, internal design, plans not built) are
   skipped, and the ledger says why in a few words.
4. Write the ledger row and the page changes **before the next heading**: `_waves/reconcile/R-OPS.md`, one row
   per source heading: heading, facts found, where each is now (page and heading), added / corrected /
   expanded / already there / skipped (why). A stop must lose at most one heading.

Keep the structure: add pages only where a fact has no home, in the fitting group of the section's
sidebar file. Readers in the browser never see JSON or API paths (AGENTS.md rule 2); operators and
integrators get commands and payloads. AI features of 0.16 stay out (after 0.16).

## Files you may edit

- `src/content/docs/run/*.md` (except `ai.md` and `set-up-ai.md`)
- `src/content/docs/administer/*.md`
- `src/content/docs/guide/administer/*.md`
- `sidebar/run.mjs`
- `sidebar/administer.mjs`
- `_waves/reconcile/R-OPS.md`

## Report

The headings reconciled, counts of facts added, corrected and expanded per page, the code-versus-document
disagreements, and anything in refiroo that looked wrong.
