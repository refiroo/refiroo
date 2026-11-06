# Fourth-round capture handoff

60 recipes; 34 missing images: 27 planned, 7 deferred.

No reference-instance request or screenshot capture ran in this preparation turn. Existing files in public/screens were inventoried, not newly visually reviewed. Provider outcomes, timing, actual data changes and image framing await external capture.

## Missing page images

| Image | Page(s) | Coverage |
| --- | --- | --- |
| `admin-agent-access-enabled.png` | `administer/agent-access.md` | Recipe ready; inspect the real result. |
| `admin-agent-calls.png` | `administer/agent-access.md` | Recipe ready; inspect the real result. |
| `admin-ai-settings.png` | `administer/ai.md` | Recipe ready; inspect the real result. |
| `admin-ai-calls.png` | `administer/ai.md` | Recipe ready; inspect the real result. |
| `admin-ai-test-answered.png` | `guide/administer/check-the-ai-provider.md` | Recipe ready; inspect the real result. |
| `admin-ai-test-failed.png` | `guide/administer/check-the-ai-provider.md` | No controlled failure exists. Do not alter provider/security configuration or deliberately cause an outage for a picture. |
| `admin-agent-new-client.png` | `guide/administer/manage-agent-access.md` | Recipe ready; inspect the real result. |
| `admin-agent-register.png` | `guide/administer/manage-agent-access.md` | Recipe ready; inspect the real result. |
| `admin-agent-block.png` | `guide/administer/manage-agent-access.md` | No saved fictional reference assistant is identified. Registration/access changes are prohibited; do not block a real assistant or invent its affected-session count. |
| `integrate-agent-access-connect.png` | `guide/integrate/connect-an-assistant.md` | Recipe ready; inspect the real result. |
| `model-assistant-change-dialog.png` | `guide/model/change-a-model-with-the-assistant.md` | Recipe ready; inspect the real result. |
| `model-assistant-whole-type-move.png` | `guide/model/change-a-model-with-the-assistant.md` | Needs an additional whole-type model-change task/accepted model. The single task is used for workbook loading; no pre-existing accepted move is identified. |
| `model-assistant-partial-move.png` | `guide/model/change-a-model-with-the-assistant.md` | Needs another model-change task and the first release already activated. Only one workbook task is requested; release activation is prohibited. |
| `model-account-before-request.png` | `guide/model/explain-a-model-change.md` | Recipe ready; inspect the real result. |
| `model-account-facts.png` | `guide/model/explain-a-model-change.md`, `journeys/shape-a-model.md` | Recipe ready; inspect the real result. |
| `model-account-provider-failure.png` | `guide/model/explain-a-model-change.md` | No naturally failed account request exists. Do not invent the provider result or create an outage. |
| `model-assistant-workbook-proposal.png` | `guide/model/review-an-assistants-workbook-design.md` | Recipe ready; inspect the real result. |
| `model-assistant-workbook-loaded.png` | `guide/model/review-an-assistants-workbook-design.md` | Recipe ready; inspect the real result. |
| `use-ask-filters.png` | `guide/use/ask-a-list-in-words.md`, `journeys/work-with-an-assistant.md` | Recipe ready; inspect the real result. |
| `use-assistant-words.png` | `guide/use/change-records-with-the-assistant.md` | Needs a separate words-only task. The one allowed task uses a workbook; a file-backed proposal cannot honestly illustrate this state. |
| `use-assistant-stopped.png` | `guide/use/continue-an-assistant-task.md` | Recipe ready; inspect the real result. |
| `use-assistant-reload.png` | `guide/use/continue-an-assistant-task.md` | Recipe ready; inspect the real result. |
| `use-record-history-explained.png` | `guide/use/explain-a-period-in-history.md` | Recipe ready; inspect the real result. |
| `use-assistant-workbook.png` | `guide/use/load-a-workbook-with-the-assistant.md` | Recipe ready; inspect the real result. |
| `use-assistant-loaded.png` | `guide/use/load-a-workbook-with-the-assistant.md` | Recipe ready; inspect the real result. |
| `use-mapping-proposal-result.png` | `guide/use/propose-targets.md` | Recipe ready; inspect the real result. |
| `use-assistant-proposal.png` | `journeys/work-with-an-assistant.md`, `use/loading-with-the-assistant.md` | Recipe ready; inspect the real result. |
| `run-ai-settings.png` | `run/ai.md` | Recipe ready; inspect the real result. |
| `run-ai-provider-calls.png` | `run/ai.md` | Recipe ready; inspect the real result. |
| `use-ask-partial.png` | `use/ask-in-words.md` | Recipe ready; inspect the real result. |
| `use-history-explained.png` | `use/history.md` | Recipe ready; inspect the real result. |
| `use-history-assistant.png` | `use/history.md` | Needs an existing published AI-authored change and distinct publisher. No such fixture is identified; publication is prohibited for screenshots. |
| `use-mapping-proposed.png` | `use/mapping-grids.md` | Recipe ready; inspect the real result. |
| `notification-email-digest.png` | `use/notifications-settings.md` | Recipe ready; inspect the real result. |

## External execution order

Run only the missing-image batch below; running the entire manifest repeats older setup and charged requests. The runner uses manifest order, not the order supplied to --only. Dependent entries use identical width, height and identity and must be in the same invocation.

```sh
node guide/tools/screens.mjs --file C10.screens.json --only admin-agent-access-enabled,admin-agent-calls,admin-ai-settings,admin-ai-test-answered,admin-agent-new-client,admin-agent-register,integrate-agent-access-connect,model-assistant-change-dialog,model-account-before-request,model-account-facts,model-assistant-workbook-proposal,model-assistant-workbook-loaded,use-ask-filters,use-assistant-stopped,use-assistant-reload,use-record-history-explained,use-assistant-workbook,use-assistant-loaded,use-mapping-proposal-result,use-assistant-proposal,run-ai-settings,run-ai-provider-calls,use-ask-partial,use-history-explained,use-mapping-proposed,notification-email-digest
node guide/tools/screens.mjs --file C10.screens.json --only admin-ai-calls
```

The Calls retake follows the task so it can include assistant turns. Allow roughly 20 minutes for the complete batch because provider recipes have explicit waits (the runner has no waitFor timeout option). These commands are a handoff, not commands executed here. Do not retry charged operations blindly. On a failed prerequisite, inspect the actual task/result and retain its identifiers before editing recipes.

## Deferred requests with no current page reference

C10-LATER is outside the allowed edit list. Its owner should remove notification-email-digest only after the new read-only recipe succeeds and its actual state is accepted. The requested on/mixed/digest/next-time/followed-workspace state is not created: account email and saved preferences remain prerequisites. The stale contributor row is already absent from the current C10-LATER file.

Webhooks are enabled but reference/README.md explicitly says the switch does not subscribe a receiver. URL rules allow HTTP only on literal loopback hosts; no valid established local receiver or saved subscription is identified. Do not start a receiver, create security/integration settings or expose a new signing key. New webhook is covered by the corrected existing recipe; deliveries, rotate and paused/resume remain deferred pending an existing receiver/subscription (and a suspended fixture for Resume). Do not remove those C10-LATER rows.

Other C10-LATER fixtures (migration staleness/old-language recovery, unavailable workspace, held jobs, invalid import, provider-person link, local group members, authenticators, sign-in provider and local-sign-in-off) remain unchanged. AI/mail/webhook switches do not supply them.

Requested companion details without distinct filenames (phone mapping Why?, idle history disclosure, claimed external-assistant history) have no separate recipe: phone result depends on the actual generated proposals; the latter published-history fixture is absent. These details remain unverified, not fabricated.

## Changes and limits

New recipes, planned persistence and cancellation are recorded in C10.data-changes.md. Restored notification-email-digest on use/notifications-settings.md; changed the stopped-task caption to the honest person-stopped state. Earlier resumed work already corrected enabled webhook and activation-account captions. No C10-LATER file was edited. No product defect is established by this source-only preparation.

## Validation

`python3 guide/_coverage/notes/C10-SCREENS/validate-fourth.py`: passed; 60 unique recipes, supported actions, existing upload paths and all 34 missing references accounted for.

`GUIDE_OUT=_build/C10-SCREENS npm run build` in guide/: passed; 247 pages, 3.88 seconds. Log: `build-fourth-round.log`; no warning lines found. No live capture or visual acceptance was performed.
