# R-CONSUMER: reconcile the documentation with its source, section by section

Read `guide/AGENTS.md` and `_waves/COMPLETE-COMMON.md`.

The person who owns refiroo finds the documentation incomplete and, in places, not correct: pages name a
topic but leave out what a reader needs (example: automatic HTTPS without Let's Encrypt, Caddy, the ACME
challenge, the certificate volume, renewal and what to do when it fails). Naming things is not enough: the
pages must carry the full, correct content of the product's own documents for their readers.

**Sources:** `docs/CONSUMER_API.md` (all of it; its "Reference implementation" example is not used, examples come from the reference data's `stops` consumer API), `docs/COMPATIBILITY.md`, then `docs/INTEGRATION_API.md` and the concept sections of `docs/API.md` (principles, security, identifiers, paging, versions, errors, batches, jobs, change feed, model authoring and workspace models; not the per-operation reference, which `/docs/api` holds).

**Pages you own:** Integrate (`integrate/`, `guide/integrate/`) and `model/consumer-apis.md` with its guides.

Work through each source **heading by heading, in order**. For each heading:
1. Read the section and list every fact a reader of your pages needs from it: what it is, how it works, every
   setting, default, limit, command, message, file, port, name, version, rule, state, exception and
   procedure.
2. Find each fact on the pages. Missing → write it where it belongs. Wrong or out of date → correct the page,
   after checking the code (the code wins over the document; where they disagree, say so in your ledger).
   Present but too thin to act on → expand it to the standard of AGENTS.md.
3. Facts that are not for readers (delivery history, decision numbers, internal design, plans not built) are
   skipped, and the ledger says why in a few words.
4. Write the ledger row and the page changes **before the next heading**: `_waves/reconcile/R-CONSUMER.md`, one row
   per source heading: heading, facts found, where each is now (page and heading), added / corrected /
   expanded / already there / skipped (why). A stop must lose at most one heading.

Keep the structure: add pages only where a fact has no home, in the fitting group of the section's
sidebar file. Readers in the browser never see JSON or API paths (AGENTS.md rule 2); operators and
integrators get commands and payloads. AI features of 0.16 stay out (after 0.16).

## Files you may edit

- `src/content/docs/integrate/*.md`
- `src/content/docs/guide/integrate/*.md`
- `src/content/docs/model/consumer-apis.md`
- `src/content/docs/guide/model/define-a-consumer-api.md`
- `src/content/docs/guide/model/see-a-consumer-apis-documents.md`
- `sidebar/integrate.mjs`
- `_waves/reconcile/R-CONSUMER.md`

## Report

The headings reconciled, counts of facts added, corrected and expanded per page, the code-versus-document
disagreements, and anything in refiroo that looked wrong.
