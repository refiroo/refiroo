# C4-ADMIN final report

## Pages written or changed

15 new pages and guides; 11 existing pages revised. The section now has 12 documentation pages and 20 task guides. All 32 are already listed in `guide/sidebar/administer.mjs`; no sidebar edit was necessary. The absent Agent access page remains explicitly deferred and is skipped by the existing sidebar loader.

### New documentation pages

- `guide/src/content/docs/administer/mail.md`
- `guide/src/content/docs/administer/webhooks.md`
- `guide/src/content/docs/administer/api-reference-and-consumer-api-pages.md`
- `guide/src/content/docs/administer/jobs-and-limits.md`
- `guide/src/content/docs/administer/deployment-pages.md`

### New task guides

- `guide/src/content/docs/guide/administer/set-up-mail.md`
- `guide/src/content/docs/guide/administer/create-a-webhook.md`
- `guide/src/content/docs/guide/administer/rotate-a-webhook-key.md`
- `guide/src/content/docs/guide/administer/find-out-why-a-webhook-paused.md`
- `guide/src/content/docs/guide/administer/create-a-custom-role.md`
- `guide/src/content/docs/guide/administer/narrow-a-grant-to-record-types.md`
- `guide/src/content/docs/guide/administer/grant-a-consumer-api-to-a-client.md`
- `guide/src/content/docs/guide/administer/link-a-provider-person.md`
- `guide/src/content/docs/guide/administer/add-a-sign-in-provider.md`
- `guide/src/content/docs/guide/administer/turn-off-local-sign-in.md`

### Revised documentation pages

- `guide/src/content/docs/administer/people-and-groups.md`
- `guide/src/content/docs/administer/roles-and-grants.md`
- `guide/src/content/docs/administer/sign-in.md`
- `guide/src/content/docs/administer/clients.md`
- `guide/src/content/docs/administer/approval-policies.md`
- `guide/src/content/docs/administer/audit.md`
- `guide/src/content/docs/administer/signing-keys.md`

### Revised task guides

- `guide/src/content/docs/guide/administer/add-a-person.md`
- `guide/src/content/docs/guide/administer/manage-a-group.md`
- `guide/src/content/docs/guide/administer/grant-a-role.md`
- `guide/src/content/docs/guide/administer/help-someone-who-lost-a-device.md`

## Coverage

All 289 ledger rows reviewed: 238 have page pointers, 9 are excluded as internal/test methods, and 31 retain their existing “after 0.16” classification. Eleven pre-existing open rows also concern explicitly deferred AI tasks, assistant tools or explanations; their row text was left unchanged as instructed:

C2318, C2321, C2335, C2342, C2345, C2359, C2374, C2385, C2386, C2473, C2476.

There are no remaining non-AI open rows. Incorrect old pointers to the roles page were replaced by the relevant page. Workspace lifecycle and model-editor tasks point into Model; personal tasks and collection screens point into Use; integration contracts point into Integrate. Those other sections were not edited. Existing deferred and internal rows were preserved. New working notes and progress are confined to the authorised wave paths.

## Screenshots

16 captures are requested in `guide/_waves/screens-wanted/C4-ADMIN.md`. Each entry identifies the page, screen, state and visible controls:

- `admin-mail-settings.png`
- `admin-mail-messages.png`
- `admin-webhook-new.png`
- `admin-webhook-deliveries.png`
- `admin-webhook-rotate.png`
- `admin-webhook-resume.png`
- `admin-api-reference.png`
- `admin-consumer-apis.png`
- `admin-about.png`
- `admin-grant-narrowed.png`
- `admin-grant-consumer-api.png`
- `admin-person-link-provider.png`
- `admin-signin-provider.png`
- `admin-local-signin-off.png`
- `admin-group-members.png`
- `admin-person-second-factor.png`

Existing screenshots were reused for People, Groups, Roles, Grants, Clients, Sign-in, Account sessions, approvals, signing keys, audit, Jobs, Deployment and Operations. No screenshot was fabricated or captured in this wave. New pages retain the required image references for the later capture wave.

## Validation actually exercised

- `GUIDE_OUT=_build/C4-ADMIN npm run verify` in `guide/`: build passed (216 pages); terms and branding passed.
- The same command’s link stage failed with 28 findings: 18 image references on C4 pages point to the 16 requested screenshots; 9 screenshots and the `/docs/journeys/` destination are missing outside C4. Every C4 page destination now resolves. Full output is `guide/_coverage/notes/C4-ADMIN/verify.log`.
- Sidebar membership check: every one of the 32 current Administer pages is listed; only the explicitly deferred Agent access slug is absent.
- Coverage pointer check: all newly reconciled target Markdown files exist. The 11 deferred open AI rows were intentionally preserved.
- No live browser, provider sign-in, SMTP delivery or webhook receiver was exercised. This is documentation/source and build evidence, not application acceptance. Captures and their appearance remain unverified.

The required isolated build passes. Full verify cannot pass before the requested captures exist and the out-of-scope link/asset findings are resolved. No changes were made to application code, tests, other sections, public image assets or shared check configuration. No commit or state-changing git command was run.

## Uncertainty and discrepancies

- The disabled-state message in `frontend/src/features/settings/WebhooksPage.tsx` still tells the operator to set `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`. The current deployment setting is `SECRETS_ENCRYPTION_KEY`; startup refuses the old name. The guide directs access administrators to their operator and Deployment without repeating the stale setting. The product defect was not edited.
- The coverage inventory describes a Description field in New role, but the current creation dialog has Name and Start from. Description is edited in the matrix after creation; the guide follows that code.
- Notification email is the current Settings navigation label, distinct from the Notifications inbox. The mail pages use the current label, despite older source prose naming Settings › Notifications.
- UI flows whose state is absent from current captures (configured factors, provider linking, mail and webhooks) were written from their components and engine rules. They still need reference-instance screenshots; no live success was assumed.
