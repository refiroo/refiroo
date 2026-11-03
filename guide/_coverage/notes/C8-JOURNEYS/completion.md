# C8-JOURNEYS completion

## Delivery

Eight Markdown pages under `guide/src/content/docs/journeys/`: index, look-after-data,
change-with-approval, shape-a-model, integrate-a-system, manage-access, run-the-service,
receive-notices. The sidebar lists all eight. The coverage file maps 47 current journeys to
rendered section anchors. Its nine `after 0.16` rows and retired J09 disposition are unchanged.

The seven categories follow the coverage file's existing task groups: everyday data work,
coordinated publication, model and workspace design, integration, access, operation and notices.
This keeps a journey in one home while its links connect work across reader sections. J42 belongs
with publication; J44 and J45 with everyday work; J57 with notices, as the coverage file specifies.
No dedicated deferred assistant pages exist to link. The nine deferred rows stay open by instruction.

## Sources and review

Read guide/AGENTS.md, the wave brief, COMPLETE-COMMON.md, coverage/journeys.md and the current
(non-AI) sections of docs/product-functionality/USER_JOURNEYS.md. Read relevant current guide
pages for records, change sets, approvals, hierarchy restructuring, mapping grids, migrations,
cross-model moves, mail, notifications, security and startup recovery. Checked the sample world
against guide/samples/README.md and SOURCES.md. No actual data rows or private domain examples
are reproduced. Inspected current frontend approval and notice labels and notification backend
following and digest eligibility. Source/code disagreements were resolved using the current
UI or existing guide, rather than repeating delivery-history wording in the catalogue.

No steering file existed at any unit boundary. Each saved page has a timestamped progress entry.
No git state-changing command, commit, reference-instance mutation or application server was run.
No subagent was used. Only the wave's permitted source and working-note paths were edited;
build artifacts use the expressly required isolated output directory.

## Checks

- `GUIDE_OUT=_build/C8-JOURNEYS npm run verify` from guide/: build PASS (224 pages, 3.12 seconds),
  terms/brand PASS (224 source pages), global link check FAIL on 20 missing screenshot references
  outside the journeys pages. No journey-page link failure was reported.
- `node --check guide/sidebar/journeys.mjs`: PASS.
- Read-only rendered-output audit: all 47 coverage links resolve to existing Markdown and
  actual rendered anchors; index has all 47 distinct journey links; eight front-matter reader
  values are valid; no journey page introduces a screenshot reference.
- Initial build failed because the predeclared `journeys/index` sidebar slug is shortened by
  Starlight's default index handling. Explicit `slug: journeys/index` in the allowed index page
  fixes entry identity while the built page is still `/docs/journeys/`. No shared config changed.
- The build emits the existing nonfatal 404 route-conflict warning.

No application test suites or browser flow tests were run for this documentation-only work.
Verification describes documentation/build evidence, not runtime acceptance.

## Screenshot dependencies outside this wave

No screenshots were requested or added by C8; these pages connect tasks rather than repeating
screen-level instructions. No screens-wanted file was edited (outside this wave's allowed files).
The global link gate reports these missing references in other pages:

1. administer/mail: admin-mail-settings.png
2. administer/mail: admin-mail-messages.png
3. administer/webhooks: admin-webhook-new.png
4. administer/webhooks: admin-webhook-deliveries.png
5. guide/administer/add-a-sign-in-provider: admin-signin-provider.png
6. guide/administer/create-a-webhook: admin-webhook-new.png
7. guide/administer/find-out-why-a-webhook-paused: admin-webhook-resume.png
8. guide/administer/help-someone-who-lost-a-device: admin-person-second-factor.png
9. guide/administer/link-a-provider-person: admin-person-link-provider.png
10. guide/administer/manage-a-group: admin-group-members.png
11. guide/administer/rotate-a-webhook-key: admin-webhook-rotate.png
12. guide/administer/set-up-mail: admin-mail-settings.png
13. guide/administer/turn-off-local-sign-in: admin-local-signin-off.png
14. guide/model/migrate-a-workspace: model-migration-stale.png
15. guide/model/raise-a-model-language-version: model-language-raise-review.png
16. guide/use/open-a-retired-or-unavailable-workspace: workspace-cannot-open.png
17. guide/use/propose-a-change: contributor-propose-change.png
18. run/background-jobs: run-jobs.png
19. use/importing-and-exporting: import-preview-columns.png
20. use/notifications-settings: notification-email-digest.png

## Uncertainty and product findings

J47 is explicitly an automated assurance journey in the source, not a product feature. Its public
section therefore gives a security-review reading path and explicitly claims no checking screen.
No missing supporting documentation page was found among the current journeys' links. No runtime
product defect was established. Missing screenshot assets above are documentation gaps and remain
for their owning waves. Deferred assistant content was not reopened.
