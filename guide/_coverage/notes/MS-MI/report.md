# MS-MI evidence and handoff

## Read and used

- Complete guide/AGENTS.md and guide/_waves/MS-MI.md; both assigned pages as they existed on disk.
- frontend/src/features/settings/MailPage.tsx: SignInFields, MicrosoftNotes, EntraChecklist, form order and cloud-section initial state; mailText.ts: SIGN_IN and SIGN_IN_ORDER.
- backend/app/engine/mail/graph.py: direct token branch, federated client assertion, cloud audiences, host discovery and failures, AADSTS explanations, send failure classification.
- backend/app/engine/mail/settings.py: managed identity saves, secret/certificate clearing and saved credential retention; backend/app/models/commands.py: MailSettingsUpdate fields and validation.
- docs/OPERATIONS.md: Microsoft 365 setup and complete managed identity subsection. Copied PowerShell, federated JSON, CLI and consent placeholders from this source.
- docs/API.md: Mail section; CHANGELOG.md: Microsoft 365 entry; targeted Microsoft 365 plan search.
- backend/app/engine/mail/sender.py: retry decision; smtp.py: MailError default permanent=False.

The initial combined page/source output was truncated; the operator mail section and managed identity Operations section were subsequently read in smaller chunks. No product or architecture changes were needed; the top-level agent instructions were excluded as directed. No MS-MI steering file or earlier progress file was present.

## Per-page changes and preserved passages

- administer/mail.md: replaced obsolete Credential layout with the four Sign in with entries and their conditional fields; explained both folds, managed identity hosting requirements, clearing credentials and safe recovery from identity refusals. Preserved SMTP setup, Sent Items and bounces, test acceptance meaning, retry windows, removal, password links and notices/digests, and the existing screenshot reference.
- run/sign-in-and-mail-setup.md: retained the client-secret/certificate setup and added full direct and federated setup, role commands, mailbox restriction, federated credential JSON/CLI, customer consent, cloud audiences, host discovery, caching, no stored credential/renewal, AKS exclusion, and refusal recovery. Updated the former Credential label. Retained existing public-address, OAuth and provider examples, secret resealing/renewal, Sent Items and bounces, digest text, screenshot and caption.

## Screenshot requests (shared by both pages)

No Microsoft 365 screenshots exist in guide/public/screens. Existing admin-mail-settings.png is retained as requested; it is an unconfigured SMTP image and cannot illustrate the Microsoft 365 form. No screenshot pixels were inspected in this wave.

1. Settings > Integration > Mail, Microsoft 365 selected, Sign in with menu expanded: all four labels and Send mail through visible.
2. Client secret selected: description, Tenant ID, Application (client) ID, masked secret field, Sending mailbox, both folded section headings and Application address. No credential visible.
3. Saved certificate selected: thumbprint and expiry visible, private-key field empty; no private key visible.
4. Managed identity – this tenant: optional Identity client ID, Azure/no-secret note, no tenant/application fields, and its expanded Entra checklist visible.
5. Managed identity – hosted in another tenant: customer Tenant ID, multitenant Application (client) ID, required Identity client ID, Azure note and its expanded Entra checklist visible.
6. Other Microsoft clouds expanded on a saved non-default configuration: both service-address fields and Application address visible.
7. Managed identity test failure: The login was refused heading and safe no-Azure-host explanation, with no credentials or tokens visible.

## Limitations and discrepancies

- No unsupported wave behavior was found in the application branches checked. Microsoft tenant-side rules, PowerShell/Azure CLI commands and portal procedures are supported by Operations, not demonstrated by local Python code or exercised against a live Azure tenant. No actual mail delivery or successful Azure token exchange was tested.
- Operations still says Credential > Managed identity (refiroo runs in Azure), while the screen now uses Sign in with and two managed identity entries. This file is outside the edit scope.
- Preserved existing failure tables in both assigned pages say an unknown Microsoft 365 mailbox fails the queued message immediately (also repeated in the operator diagnostic table). graph._send_failure returns SENDER with default permanent=False; sender._deliver retries it. The administrator Messages and retries paragraph already states that it waits. Left these existing passages intact because the wave explicitly asks to keep the existing failure/retry text; report for correction by the owner.
- The build emitted a /404 route-conflict warning and completed successfully.

## Validation

- GUIDE_OUT=_build/MS-MI npm run build: passed, 257 pages, 4.31 seconds.
- GUIDE_OUT=_build/MS-MI npm run check: passed terms and brand for 257 pages.
- GUIDE_OUT=_build/MS-MI npm run check:links: passed, 75,802 local links/sources in 257 pages.
- git diff --check limited to the assigned pages and progress path: passed. Git commands were read-only; no commit or staging.
