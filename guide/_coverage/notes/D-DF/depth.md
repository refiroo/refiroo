# D-DF depth review

Scope: the three delivered capabilities. Continued the first run’s nine concept pages and
completed its pending task guides. Rechecked facts against current code. The guide-specific
writing instructions govern this assignment. No steering file existed at any unit boundary.

| Page under src/content/docs | Applicable depth questions answered |
| --- | --- |
| administer/webhooks.md | Purpose, permissions, both Events from sources, three workspace events, no-consumer creation, hidden controls, immutable source, future/live delivery, retained-version state, suspension/resume, rotation, deletion and operator/receiver recovery links. |
| guide/administer/create-a-webhook.md | Exact controls for both sources, authorised active workspace, selected events, hidden options, Requests/Format, receiver refusal, one-time key, future-only delivery and recovery links. |
| guide/administer/find-out-why-a-webhook-paused.md | Retained/stopped contract distinction, Accepted/Served now, receiver review, missing declarations, workspace source, normal resume and expired-event reset with fresh baseline. |
| administer/clients.md | Active/inactive rotation, identity/grant preservation, overlap from rotation, leak recovery, restore/issued-access caveat, lost-secret replacement and backup link. First-run text retained after source recheck. |
| guide/administer/rotate-a-client-secret.md | Routine handover, one-time copy, deactivate/rotate/restore, Stop it now, no automatic restoration, overlap spent inactive, older-secret deadlines and issued-access caveat. |
| model/consumer-apis.md | Retained shape over current data, base-release preservation after edits, unserved-version exception, reference validation, dates, stop/undo, activation, removal/recovery and notice ownership. |
| guide/model/raise-a-contract-version.md | Prerequisites, menu/edit/notice actions, retained row, base-release definition, dates, documents, activation, deliberate non-retention, undo and refusals. |
| guide/model/stop-serving-an-earlier-contract-version.md | New task: choose earlier version, announce/withdraw sunset, notice ownership, stop confirmation/cancel/undo, Schema warning, workspace activation, webhook handover and service restoration. |
| guide/model/define-a-consumer-api.md | Released-contract refinement, retained shape and sources, base-release preservation, notice/date/removal links and access separation; existing setup retained. |
| guide/model/see-a-consumer-apis-documents.md | Current draft documents versus each served version’s document, deprecated marking, sunset, handover and grants; existing example/data distinction retained. |
| guide/model/install-and-activate-a-release.md | Retained versions in active release, kept-contract refusal, Schema stop warning, install-summary omission, destination-specific checks and webhook effects. |
| guide/model/change-a-workspaces-model.md | Installed target release checks, source restoration, retained continuity, deliberate removal, per-workspace effects, cancellation and immutable-release recovery. |
| integrate/consumer-apis.md | Declaration/version/date rules, base-release preservation, live data, index/OpenAPI, headers and date fallback, removal/read error, servedContractVersions, kept-contract refusal and stop warning. Existing complete business objects linked; migration illustrative. |
| integrate/consumer-events-and-webhooks.md | Workspace creation and hidden/unsupported choices; retained feed derivation/object composition, explicit contractVersion, complete illustrative create request and refusal, exact suspension message and resume. Existing full events/webhook examples retained. |
| guide/integrate/subscribe-a-webhook-and-verify-it.md | Earlier-version creation, accepted-version retention, stopped-version review; existing signing, delivery, rotation, reset and move recovery retained. |
| guide/integrate/read-through-a-consumer-api.md | Discovery, deprecated versus stopped, notice headers, deliberate parser migration, version error and publication limitation. |
| integrate/model-and-release-operations.md | Kept-version refusal versus stopped-version warning, recovery, retained subscriptions and reference links. |
| integrate/compatibility.md | Rechecked and retained: software notice versus administrator-chosen consumer notice, explicit removal, non-enforced sunset, header standards. |
| integrate/api-reference.md | Rechecked and retained: per-version documents, workspace, deprecated operations, index and removal. |
| integrate/reading-business-objects.md | Rechecked and retained: earlier shape over live data, version/workspace checkpoint, current-route and publication-definition requirements, removal recovery. |
| about/compatibility-and-licence.md | Rechecked and retained: consumer notice ownership and explicit removal in reader-level language. |

## Sources checked

- Frontend: WebhookDialog.tsx, webhookText.ts, WebhooksPage.tsx, ClientsPage.tsx;
  ConsumerApis.tsx, operations.ts, OperationDialog.tsx, InstallDialog.tsx and ActivateDialog.tsx.
- Backend: identity/clients.py; events/subscriptions.py, subscription_rules.py and delivery.py;
  model/consumer_definitions.py, consumer_contract.py, consumer_openapi.py,
  authoring/consumer.py, validation/consumer_api_rules.py; models/schema.py;
  reads/consumer_objects.py, consumer_events.py, consumer/router.py and common/pagination.py.
  Event plan/deriver/dispatcher version references were searched; not read in full.
- DF section in BASE_0_13_IMPLEMENTATION_PLAN.md, COMPATIBILITY.md,
  guide/samples/README.md, SOURCES.md and the stops declaration in model.json.

## Not applicable and limits

No new backup/export controls belong to these features. Instance backup and receiver-state
recovery remain on the linked operator/integrator pages. Contracts do not renew or expire on
the sunset day; explicit removal/restoration is covered. Secrets keep their existing rotation
lifecycle. No additional exclusion is needed.

No applicable question was left unanswered by guessing. Screenshot appearance and live
end-to-end behavior remain unverified: this is source-backed documentation work. The install
summary’s omitted removal warning is recorded in report.md.
