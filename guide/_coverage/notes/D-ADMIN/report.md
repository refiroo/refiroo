# D-ADMIN completion report

Reviewed all 37 documentation pages and task guides in the section. Added the
permissions reference and expanded 19 existing pages. The sidebar now lists the new
reference under Roles and grants. All other existing page locations and groups remain.

## Pages and words

Words are whitespace-separated counts of each Markdown file, including front matter
and non-rendered inventory comments; the baseline was saved before edits in `before.json`.
The whole section grew from **25,496** to **29,841** words.
Seventeen existing pages were reviewed and retained without changes; see `depth.md`.

| Page written or changed | Before | After |
| --- | ---: | ---: |
| [administer/agent-access.md](../../../src/content/docs/administer/agent-access.md) | 1,265 | 1,497 |
| [administer/ai.md](../../../src/content/docs/administer/ai.md) | 1,517 | 1,788 |
| [administer/approval-policies.md](../../../src/content/docs/administer/approval-policies.md) | 699 | 904 |
| [administer/clients.md](../../../src/content/docs/administer/clients.md) | 983 | 1,230 |
| [administer/deployment-pages.md](../../../src/content/docs/administer/deployment-pages.md) | 646 | 775 |
| [administer/jobs-and-limits.md](../../../src/content/docs/administer/jobs-and-limits.md) | 545 | 708 |
| [administer/mail.md](../../../src/content/docs/administer/mail.md) | 1,090 | 1,454 |
| [administer/people-and-groups.md](../../../src/content/docs/administer/people-and-groups.md) | 1,215 | 1,443 |
| [administer/permissions-reference.md](../../../src/content/docs/administer/permissions-reference.md) | 0 | 1,275 |
| [administer/roles-and-grants.md](../../../src/content/docs/administer/roles-and-grants.md) | 1,781 | 1,802 |
| [administer/sign-in.md](../../../src/content/docs/administer/sign-in.md) | 1,851 | 2,208 |
| [administer/signing-keys.md](../../../src/content/docs/administer/signing-keys.md) | 412 | 481 |
| [administer/webhooks.md](../../../src/content/docs/administer/webhooks.md) | 1,176 | 1,493 |
| [guide/administer/link-a-provider-person.md](../../../src/content/docs/guide/administer/link-a-provider-person.md) | 350 | 395 |
| [guide/administer/manage-agent-access.md](../../../src/content/docs/guide/administer/manage-agent-access.md) | 975 | 1,035 |
| [guide/administer/require-a-second-factor.md](../../../src/content/docs/guide/administer/require-a-second-factor.md) | 435 | 481 |
| [guide/administer/rotate-a-client-secret.md](../../../src/content/docs/guide/administer/rotate-a-client-secret.md) | 399 | 491 |
| [guide/administer/rotate-a-webhook-key.md](../../../src/content/docs/guide/administer/rotate-a-webhook-key.md) | 341 | 386 |
| [guide/administer/set-an-approval-policy.md](../../../src/content/docs/guide/administer/set-an-approval-policy.md) | 435 | 478 |
| [guide/administer/set-up-mail.md](../../../src/content/docs/guide/administer/set-up-mail.md) | 532 | 668 |

## Coverage

- Current inventory: **172 covered, 0 excluded, 0 uncovered** in administer: 62 permissions,
  11 screens, 99 management operations. The 31 initially uncovered permission entries now
  have a home. The reference names all 16 groups, their actions, predefined role holders,
  reach, hidden controls, job access and the assistant ceiling.
- Management operation details stay in the generated API reference; browser task pages do
  not duplicate protocol fields. Inventory identifiers lacking human labels are only in
  HTML comments beside their prose explanations, not rendered to administrators.
- Historical coverage: 289 existing source rows retain their assigned homes, including the
  ten existing not-for-reader rows. No historical row was left open or newly excluded.
- Updated `_waves/coverage/administer.md` with an explicit row for every current entry.
  `_coverage/exclusions.md` was unchanged.
- Depth questions: no known factual question left open. Per-capability answers, applicable
  lifetime/removal/recovery limits and a ledger for every page are in `depth.md`.
- No D-ADMIN steering file existed on any unit's check, including final reporting.

## Screenshots

No new screenshots requested; `_waves/screens-wanted/D-ADMIN.md` records this. Every
referenced screenshot file exists. Existing screenshots and captions were retained.
Screens were not captured or visually inspected, and no live browser, mail, sign-in,
webhook or assistant exercise was performed in this writing wave. The evidence is source
inspection and documentation checks, not functional or visual acceptance of refiroo.

## Product defects and screen gaps

1. **Values is described as capped on the AI screen, but is not capped by the sample count.**
   `frontend/src/features/settings/aiText.ts:9-11` says up to the sample count per column;
   `backend/app/engine/proposals/context.py:47-52` returns all requested values at Values.
   The guide states the actual policy and explicitly tells administrators not to interpret
   that count as the Values ceiling. Source-confirmed; not tested with an external provider.
2. **Resolved: Workspace events can be created in the browser.** Rechecked by D-DF:
   `WebhookDialog.tsx` offers **Events from**, with Consumer API or Workspace events.
   `WebhooksPage.tsx` allows New webhook without any event-declaring consumer API;
   the dialog then offers only Workspace events. Both sources use the workspace selector.
   The documentation and creation guide now describe the actual form, with no API handoff.
3. **Resolved: deactivated clients can rotate secrets in the browser.** Rechecked by D-DF:
   `ClientsPage.tsx` shows Rotate secret for both active and deactivated clients. Its
   inactive-client note explains that the new secret takes effect on Restore and the
   overlap is counted from rotation. The guide covers deactivate, rotate with Stop it now,
   configure the replacement and restore. Previously issued unexpired access can become
   usable again on restore; rotation does not revoke that access.

D-ADMIN changed no application code. D-DF checked the later product changes against source;
these two screen gaps are resolved. See `../D-DF/report.md` for the current documentation
checks and screenshot requests. Registration expiry, job-summary retention, unlink effects
and decision rules were documentation corrections, not application fixes.

## Validation

- **Passed:** `GUIDE_OUT=_build/D-ADMIN npm run verify` in guide after final page corrections.
  This runs the required isolated build, terms, branding and built-site link/source checks:
  248 built pages, 70,269 checked local links/sources. Full output: `verify.log`.
- **Passed for administer:** the repository coverage checker found 62/62 permissions,
  11/11 screens and 99/99 management operations covered. The global command exits 1 for
  113 uncovered entries in other sections; no administer entry appears in its report.
  Output: `coverage.log`, `uncovered.md`.
- The coverage checker normally overwrites shared `_coverage/inventory/uncovered.md`,
  outside this wave's edit scope. `check-coverage.mjs` runs the unchanged checker with that
  single write redirected into this allowed notes directory. The shared report was not
  overwritten. Inventory already existed, so it was not regenerated.
- `git diff --check` on the allowed paths passed. No commits or git state-changing commands.
- No server, database or background service was started. Both build processes completed.

## Remaining uncertainties

No unresolved source contradiction was guessed into the pages. The code/screen mismatches
above remain in refiroo, outside this writing scope. Behaviour against the reference
instance and current screenshot appearance remain unverified; configuration changes and
external-provider/receiver handovers were not performed.
