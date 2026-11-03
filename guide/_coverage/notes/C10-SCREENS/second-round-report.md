# Second-round capture handoff

Current inventory: 25 missing page-image names; 10 have recipes, 15 are excluded with prerequisites below. Existing recipes are preserved; use --only to avoid retaking completed pictures. No reference-instance calls were made in this round.

## Capture next

`admin-api-reference,admin-consumer-apis,admin-webhook-new,admin-about,admin-mail-settings,admin-mail-messages,admin-grant-consumer-api,admin-grant-narrowed,hierarchy-restructure-plan,replace-related-records`

| Image | Required screen/state |
| --- | --- |
| replace-related-records.png | Modes relationship set of Chur Wiesental: existing Train ticked and counted, candidate Tram matched by a search for Tr. No checkboxes changed, so Save is disabled; cancel. Search retains Train because it matches Tr. Select the row first so keyboard focus keeps its edit controls mounted; selection is browser state only. Reset display restores the relationship column; a wider viewport keeps it in view. Clicking the row checkbox explicitly gives it focus even if already selected. No relationship is changed. |
| hierarchy-restructure-plan.png | Insert a Mode level above Road in the dedicated C10 change set: Type of the new level, name, plan counts and the By record tab; missing Mode code input is shown if required. Nothing applied. This preview demonstrates insertion, not a type conversion; values without a place may be zero. Open the node’s Actions (Shift+F10) trigger; right-clicking the row alone does not open TreeView’s action menu. |
| admin-api-reference.png | Settings Integration > API reference: Sources lists Management API and Stops API with versions and OpenAPI document links. Read only. |
| admin-consumer-apis.png | Active reference release and Stops API v1, Base URL and OpenAPI document copy controls, operation descriptions and Change feed retention. Read only. |
| admin-about.png | About scrolled to Engine and Active model release, including reference-model name/version and Open release. Read only. |
| admin-grant-consumer-api.png | Existing Stops reader (guide) client: cancelled Grant dialog on Consumer APIs, API/workspace grid and already granted Graubünden cell. No grant submitted; requested newly selected cell/permission sentence needs another eligible ungranted workspace and is not assumed. |
| admin-grant-narrowed.png | Rita Approver: cancelled Grant dialog for Data steward in Graubünden only, narrowed to Stop. Shows reading is never narrowed and permission sentence. Does not change her existing Data owner grant. |
| admin-webhook-new.png | Unsaved New webhook for the reference Stops API in Graubünden, stops-changed selected and a municipality filter. Fictional local receiver URL is never saved or contacted. Name and URL are cleared before Cancel so no dirty-dialog confirmation blocks cleanup. |
| admin-mail-settings.png | Actual unconfigured Mail page: empty Mail server form, Application address and disabled Test message. No server saved, no test sent; this replaces the unavailable successful-test request. Capture review must confirm the unconfigured state. |
| admin-mail-messages.png | Mail Messages section filtered to Waiting, showing its real empty state and state counts. No messages generated, sent or stopped. The requested retry rows need a configured test outbox and are not manufactured. |

## Left out

| Image | Reason |
| --- | --- |
| model-migration-stale.png | The stale notice is raised when a migration confirmation is refused. Triggering it requires pressing Migrate after an intervening edit; this wave forbids migration/activation confirmations. No stale-state fixture or screenshot is fabricated. |
| model-language-raise-review.png | Requires a workspace on a historical schema-language release outside the supported read window. The documented reference workspaces use readable releases; no isolated historical-release fixture is supplied. Do not corrupt or replace the running release to manufacture it. |
| workspace-cannot-open.png | The requested administrator repair card requires schemaLeftWindow on a real workspace. An unknown workspace or retired workspace does not show that state. Shares the missing historical-release fixture prerequisite with model-language-raise-review. |
| contributor-propose-change.png | The runner supports only the reference admin and Rita Approver. Earlier capture notes give Rita Data owner, not Contributor. Producing the Contributor-only Live band would require creating/changing an account or grant, which this wave forbids. |
| notification-email-digest.png | Earlier reference captures document mail unavailable. The requested enabled email/digest state needs configured mail and an account destination. Neither is verified available, and no deployment/account setting is changed to invent this state. Reassess if the external capture confirms mail has since been configured. |
| run-jobs.png | The requested single image contains queued, running and finished work together. Existing finished/cancelled jobs and the prepared export are not that state. The runner cannot hold a worker or deterministically pause jobs; the small reference jobs can finish before capture. No large artificial workload or worker disruption is introduced for a picture. |
| import-preview-columns.png | Requires an exported For people workbook with saved import metadata and a deliberate invalid cell. No such local fixture is supplied; the runner has no download/save-download action to recover the prepared export. The ordinary supplier workbook or a JSON Lines refusal would not show Read as exported plus the required column report. Supply the actual exported workbook for a subsequent preparation pass; do not substitute an unrelated preview. |
| admin-webhook-deliveries.png | Needs an existing reference subscription with retained retrying and succeeded deliveries. No subscription/receiver fixture is identified in the capture records. Creating and driving one would confirm a dialog and send network requests; no subscription or event is fabricated. |
| admin-webhook-rotate.png | The rotate dialog can safely be cancelled, but needs an existing reference webhook. No saved webhook ID/name is supplied; the new-webhook recipe intentionally cancels. Do not create a subscription or rotate a key to manufacture this state. |
| admin-webhook-resume.png | Needs an existing suspended reference webhook with diagnostic findings. No suspended fixture is supplied; do not create, suspend or break a receiver or confirm Resume to stage a screenshot. |
| admin-person-link-provider.png | Needs a configured test identity provider and a provider-created fictional person eligible for linking. No such fixture is identified. Configuring a provider or changing identities/security for a picture is forbidden. |
| admin-group-members.png | Earlier ADMIN capture records an empty groups list. No populated local test group is identified. Creating a group and adding fictional members would change access/security settings, which this wave forbids. |
| admin-person-second-factor.png | Requested fictional person must already have an authenticator and passkey. Reference account captures show no configured authenticator; no suitable person is identified. Enrolling factors or making/removing passkeys changes security settings and cannot be done for this picture. |
| admin-local-signin-off.png | Requested local-account Off state needs an existing working provider and an authorised security setup. Earlier reference captures use local sign-in. Never turn it off or alter the provider/security settings for a picture. |
| admin-signin-provider.png | Requires an already saved fictional test provider with redirect/sign-out addresses and a sealed secret. No configured test provider is identified; creating or saving one changes security settings. The existing New provider dialog image does not show a saved provider. |

## Corrections this round

- Three Use-page corrections from steering applied: phone drawer caption, Accept / Ignore workbook controls and blocked loading, two-stop deletion caption.
- Hierarchy waits by accessible region name rather than looking for undrawn text. Relationship capture restores columns, explicitly focuses the row, widens the viewport and hovers its Train cell; its runtime success is pending.
- Added eight Administer recipes: About, API reference, Consumer APIs, New webhook, two Grant dialogs and two Mail views. Mail captions now describe unconfigured/empty states rather than an unsent test or nonexistent retries.
- Narrowed grant uses the existing Rita identity, Data steward and Stop in Graubünden; it changes only local dialog choices and cancels. Existing broader grants remain. Consumer grid shows already-held access; a newly selected ungranted cell is not assumed.

## Review limits

No new images were captured or inspected this round. The earlier image findings remain in recapture-report.md. These new recipes require external capture and visual review, especially dialog heights, the relationship edit control, empty mail state and saved test fixtures. Omitted states are prerequisites, not confirmed defects in refiroo. A build checks documentation compilation, not browser correctness.
