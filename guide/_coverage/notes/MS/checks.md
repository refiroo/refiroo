# MS writing evidence

Read `guide/AGENTS.md` first, then `guide/_waves/MS.md`. Neither progress nor steering existed at the start. Rechecked steering before the operator page and the final checks; none existed. Only the two assigned pages, this note and MS progress were authored. The required build generated its separate `_build/MS` output and cache. No commits or Git state-changing commands were run.

## Sources checked

- `frontend/src/features/settings/MailPage.tsx`: method choice, Microsoft fields, Entra box, saved-credential text, sending mailbox and test response. `mailText.ts`: exact failure headings and SMTP connection labels.
- `backend/app/engine/mail/graph.py`: certificate validation, client credentials, RS256 assertions, cached tokens, MIME delivery, Sent Items limitation, bounce limitation, safe failure wording and retry classification.
- `backend/app/engine/mail/settings.py`: method replacement, credential retention, sealing and saved-setting concurrency. `transport.py`: one method per send, no fallback. `sender.py`: shared failures within a sending round, retry delay, expiry and message erasure.
- `backend/app/models/commands.py`, `MailSettingsUpdate`: per-method fields and validation. `backend/app/management/schemas/mail.py`: write-only credentials, certificate metadata and failure kinds.
- `backend/app/engine/identity/resealing.py` and `backend/app/cli/reseal_secrets.py`: both Microsoft credential entries and key-change procedure.
- Targeted sections in `docs/OPERATIONS.md` (Microsoft 365 delivery and changing the encryption key), `docs/API.md` (Mail), `USER_JOURNEYS.md` (J46.11), `CURRENT_FUNCTIONALITY.md` (Send mail), and the MS changelog entry. Entra portal and Exchange Online preparation steps are supported by the operations document and UI instructions; no real tenant was exercised.

## Passages retained

- Administrator page: SMTP connection choices and password rules, existing image, password-link behavior, notice/digest preferences, stop-sending and address-change recovery. Shared retry and removal paragraphs were extended only for Microsoft 365. The linked Set up mail task is still SMTP-specific, so its link now says so.
- Operator page: existing sign-in, client and recovery examples; SMTP ports, trust and password guidance; digest behavior; existing SMTP diagnostic fragments and screenshot/caption. Preparation now explicitly selects SMTP; general references to configured mail now allow either method. Existing fenced examples and image references on both pages were compared with HEAD and are identical.

## Source discrepancy and limits

The wave says any other Graph refusal fails immediately. `_send_failure` in `graph.py` uses `permanent=status != 409`, so HTTP 409 is retried. Both pages follow the code. No product defect was confirmed; live Entra consent, Exchange policy enforcement, certificate expiry at Microsoft and actual delivery were not exercised. Certificate expiry is checked locally on saving; after saving the documented login failure depends on Microsoft's response, and an already cached token may remain usable until refreshed.

## Missing pictures

Both pages retain `/docs/screens/admin-mail-settings.png` and the operator caption unchanged. Neither supplies a Microsoft 365 form picture. Capture Settings › Integration › Mail with Microsoft 365 selected: method selector, Entra preparation box, tenant/application fields, Credential choice, Sending mailbox, Application address and both service addresses visible. Also capture a saved Certificate state with the SHA-1 thumbprint and expiry visible; show no secret or private key. These are requests for later reference-instance capture; no new image link was inserted.

## Checks

- `GUIDE_OUT=_build/MS npm run build` in `guide/`: passed, 257 pages in 3.51 s. Warning: `/404` from the catch-all route conflicts with the higher-priority `/404` route.
- `GUIDE_OUT=_build/MS npm run check`: passed terms and brand checks, 257 pages.
- `GUIDE_OUT=_build/MS npm run check:links`: passed, 75,786 local links and sources in 257 built pages.
- Scoped `git diff --check`: passed. Existing fenced examples and screenshot references unchanged on both pages.
- No application servers or background services were started. No application test suites were run for this documentation-only assignment.
