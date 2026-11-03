# Steering for C11 (2026-11-03)

- `admin-mail-messages.png` could not be captured: remove its reference from its page (the text must say what
  the screen shows) and add it to `_waves/screens-wanted/C10-LATER.md` in that file's form.
- At the end, `GUIDE_OUT=_build/C11-FINAL npm run verify` must pass completely: no missing link or image.
- The build warns about a `/404` route conflict: check whether Starlight's own 404 and `src/content/docs/404.md`
  clash, and resolve it so the page served for a missing address is ours.

**Name the concrete things, in every section.** The person who owns refiroo finds pages that describe
mechanisms generically and leave out the names a reader recognises (automatic HTTPS without "Let's Encrypt",
sign-in without "OpenID Connect", passkeys without "WebAuthn", and so on). As part of the final check, go
through every section and name what refiroo actually uses where the reader meets it: technologies,
standards, protocols, formats, file formats (xlsx, CSV, JSON), providers and their versions where refiroo
fixes one. Evaluators get the overview on `about/how-it-is-built.md` (the components, standards and
licences, from `THIRD_PARTY_NOTICES.md`, `compose*.yml`, the Dockerfiles and `backend/pyproject.toml`).
Take each name from the files; never name something refiroo does not use.

**Handoffs from the reconciliation jobs.** `_waves/reconcile/R-*.md` list facts each job found for pages it
did not own (R-FUNCTIONALITY in particular hands facts to Model, Administer, Run and Integrate). Write each
handed-off fact on its page, and mark it done in that ledger.
