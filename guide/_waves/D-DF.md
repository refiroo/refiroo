# D-DF: the guide for 0.13 DF (three new capabilities)

Read `guide/AGENTS.md`, `_waves/COMPLETE-COMMON.md` and `_waves/DEPTH-COMMON.md`, in that order. The spec is the
section "DF: Findings of the depth waves" in `../docs/BASE_0_13_IMPLEMENTATION_PLAN.md`; the code wins over every
document. Readers: administrators (DF1, DF2), model administrators and integrators (DF3).

Three capabilities were added after the D-* waves. The pages still describe the old behaviour. Document each to
working depth (every depth question of `DEPTH-COMMON.md` that applies), with labels exactly as the screens show them:

1. **Workspace events from the Webhooks screen** (`frontend/src/features/settings/WebhookDialog.tsx`,
   `webhookText.ts`; `backend/app/engine/events/subscriptions.py`): the "Events from" choice, Consumer API or
   Workspace events, what each delivers, the three workspace events, what is hidden for a workspace source.
2. **Rotating a deactivated client's secret** (`frontend/src/features/security/ClientsPage.tsx`;
   `backend/app/engine/identity/clients.py`): the recovery after a leaked secret: deactivate, rotate, restore; when
   the new secret takes effect and how the overlap is counted.
3. **Earlier contract versions of a consumer API** (`backend/app/models/schema.py` `ConsumerApiEarlierVersion`,
   `engine/model/consumer_definitions.py`, `consumer_contract.py`, `validation/consumer_api_rules.py`,
   `reads/consumer_objects.py`, `consumer/router.py`, `engine/events/`; editor `ConsumerApis.tsx`,
   `InstallDialog.tsx`, `authoring/consumer.py`): raising a version keeps the previous one served; the Earlier
   versions table, sunset day, Stop serving and its undo; "Raise and stop serving N"; the `Deprecation` and `Sunset`
   headers; the index and OpenAPI marking; subscriptions and the pull feed on a kept version, `contractVersion` on
   subscription create, suspension `CONTRACT_VERSION_CHANGED` when a version stops; every refusal and warning
   (`CONSUMER_KEPT_VERSION_CHANGED`, `CONSUMER_VERSION_STOPPED`, `CONTRACT_VERSION_NOT_FOUND` with
   `servedContractVersions`) exactly as refiroo shows it; who chooses the notice period (`../docs/COMPATIBILITY.md`).

Pages that state the old behaviour (fix every one; grep for more):

- `guide/model/raise-a-contract-version.md`, `guide/model/define-a-consumer-api.md`,
  `guide/model/see-a-consumer-apis-documents.md`, `model/consumer-apis.md`,
  `guide/model/install-and-activate-a-release.md`, `guide/model/change-a-workspaces-model.md`
- `integrate/consumer-events-and-webhooks.md`, `integrate/consumer-apis.md`, `integrate/reading-business-objects.md`,
  `integrate/compatibility.md`, `integrate/api-reference.md`, `about/compatibility-and-licence.md`
- `administer/webhooks.md`, `guide/administer/find-out-why-a-webhook-paused.md`, `guide/administer/create-a-webhook.md`
- `guide/administer/rotate-a-client-secret.md`

Add a how-to `guide/model/stop-serving-an-earlier-contract-version.md` if no page covers it, with its sidebar entry.
Update the stale findings in `_coverage/notes/D-ADMIN/report.md` (items 2, 3), `_coverage/notes/D-ADMIN/depth.md` and
`_coverage/notes/D-INTEGRATE/report.md` (item 2): they are fixed by DF.

## Files you may edit

- `src/content/docs/model/**`
- `src/content/docs/guide/model/**`
- `src/content/docs/integrate/**`
- `src/content/docs/guide/integrate/**`
- `src/content/docs/administer/**`
- `src/content/docs/guide/administer/**`
- `src/content/docs/about/compatibility-and-licence.md`
- `sidebar/model.mjs`
- `sidebar/integrate.mjs`
- `sidebar/administer.mjs`
- `_waves/screens-wanted/D-DF.md`
- `_coverage/exclusions.md`
- `_coverage/notes/D-DF/**`
- `_coverage/notes/D-ADMIN/**`
- `_coverage/notes/D-INTEGRATE/**`

**Second run.** The first run got a shortened list by mistake; the list above is complete. Finish the pages and notes it
left. The four code findings of the first run's report are fixed in the code since: re-read the code and describe
the fixed behaviour, removing the workarounds the first run wrote.

## Report

As `DEPTH-COMMON.md` says, plus the screenshots wanted for the Earlier versions table, the webhook "Events from"
choice and the inactive client's rotate dialog.
