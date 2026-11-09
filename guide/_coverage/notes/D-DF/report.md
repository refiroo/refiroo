# D-DF completion report

The writing assignment is complete across the first and second runs: 20 existing pages
updated and one task guide added. The new stop-serving guide is in the model sidebar.
The four first-run code findings were rechecked and their obsolete workarounds removed.
Only authorised files were edited; no commits or state-changing git commands were run.
Unrelated existing edits, including other sidebar entries, were preserved.

## Pages and words

Whitespace-separated counts include front matter, fenced examples and inventory comments.
For the nine first-run pages, Before is that run’s recorded pre-edit count; other pages use
this run’s saved baseline (`second-run-before.json`). The new page starts at zero. These
are wave counts, not a claim about every pre-existing working-tree edit.

**21 pages: 26,188 → 31,013 words.**

| Page under src/content/docs | Before | After |
| --- | ---: | ---: |
| `administer/webhooks.md` | 1,493 | 1,660 |
| `administer/clients.md` | 1,230 | 1,312 |
| `guide/administer/create-a-webhook.md` | 511 | 607 |
| `guide/administer/find-out-why-a-webhook-paused.md` | 563 | 651 |
| `guide/administer/rotate-a-client-secret.md` | 491 | 692 |
| `model/consumer-apis.md` | 2,629 | 3,286 |
| `guide/model/raise-a-contract-version.md` | 266 | 681 |
| `guide/model/stop-serving-an-earlier-contract-version.md` | 0 | 600 |
| `guide/model/define-a-consumer-api.md` | 1,577 | 1,733 |
| `guide/model/see-a-consumer-apis-documents.md` | 1,020 | 1,114 |
| `guide/model/install-and-activate-a-release.md` | 861 | 1,108 |
| `guide/model/change-a-workspaces-model.md` | 337 | 598 |
| `integrate/consumer-apis.md` | 4,086 | 4,760 |
| `integrate/consumer-events-and-webhooks.md` | 3,486 | 3,999 |
| `integrate/reading-business-objects.md` | 1,960 | 2,096 |
| `integrate/compatibility.md` | 766 | 813 |
| `integrate/api-reference.md` | 475 | 541 |
| `integrate/model-and-release-operations.md` | 2,225 | 2,286 |
| `guide/integrate/read-through-a-consumer-api.md` | 576 | 703 |
| `guide/integrate/subscribe-a-webhook-and-verify-it.md` | 1,078 | 1,149 |
| `about/compatibility-and-licence.md` | 558 | 624 |

Also updated sidebar/model.mjs, screens-wanted/D-DF.md, progress/D-DF.md, this wave’s
coverage/depth/report notes, D-ADMIN report items 2–3 and depth findings, and D-INTEGRATE
report item 2. Other sidebars and exclusions did not need changes.

## Coverage and depth

- Workspace-source webhook setup, all three change-set events, hidden consumer options,
  no-consumer creation, permission and source immutability are documented.
- Active and deactivated client rotation, overlap counted from creation, immediate old-secret
  ending, deactivate/rotate/restore, retained grants and issued-access limits are documented.
- Earlier contract retention from the draft’s base release, unserved-version exception,
  current-data reads, Earlier versions controls, sunset announcement/withdrawal, stop/undo,
  per-workspace activation, generated documents/index, Deprecation/Sunset, subscription create,
  retained pull/webhook shapes and stopped-version recovery are documented. Error codes and
  messages include CONSUMER_KEPT_VERSION_CHANGED, CONSUMER_VERSION_STOPPED,
  CONTRACT_VERSION_NOT_FOUND with servedContractVersions, and CONTRACT_VERSION_CHANGED.
- Consumer notice is chosen by the model administrator, distinct from refiroo’s own promise.
- Existing inventory: 911 total, 902 covered, nine existing exclusions, zero uncovered.
  Model: 381 total, 378 covered, three existing exclusions. Administer: 172 covered.
  Integrate: 53 covered. No new exclusions. The inventory existed, so it was not regenerated;
  counts describe that snapshot, not a new inventory of the DF controls. The new capabilities
  are mapped explicitly in depth.md. No scoped row or applicable depth question remains open.

See depth.md for each page’s applicable lifecycle, setup, change, failure, recovery,
removal, limits and permission questions. Backups remain instance/receiver responsibilities
linked to their owning pages; contracts have no automatic expiry or renewal.

## Screenshots wanted

See `guide/_waves/screens-wanted/D-DF.md` for all page references and capture states.

1. **admin-webhook-workspace-events.png** — New webhook, Events from set to Workspace events;
   workspace and all three change-set choices/descriptions, Requests and Format; consumer
   selector, Filters and Content absent. Also check the no-consumer declaration state.
2. **admin-client-inactive-rotate.png** — deactivated reference client’s rotate dialog, note
   about Restore and overlap counted from now, Stop it now and Make a new secret; no secret.
3. **model-consumer-earlier-versions.png** — reference Stops API draft on Types and related,
   current v2 and retained v1, Superseded, editable Sunset day and Stop serving.

These assets are awaiting capture. No fabricated screenshots or placeholder image files were
created; the authorised page references are present. The missing assets block link validation.

## Checks actually exercised

- `GUIDE_OUT=_build/D-DF NODE_OPTIONS='--import ./_coverage/notes/D-DF/preserve-coverage-report.mjs' npm run verify`
  in guide: isolated build passes, 253 pages; terms and brand pass; coverage passes.
  The pre-existing wrapper redirects only the checker’s generated shared uncovered report
  into this wave’s authorised notes. It does not suppress findings or alter page checking.
- Link validation reports **seven references to the three missing screenshot files above**;
  no other missing local link/anchor is reported. Full verify therefore does **not** pass.
  Exact output is in verify.log.
- Parsed all 16 JSON fenced examples in the authorised model, integration and administration
  sections: pass. Migration/subscription versions and dates newly added are illustrative.
- Read-only scoped `git diff --check`: pass. Changed task-guide/sidebar diff inspected;
  source/label and stale-wording searches performed across the allowed sections.
- Existing build warnings: unsupported caddyfile highlighting and conflicting /404 route.
  No files outside the assignment were changed to suppress them.

No application server, database, browser, receiver or HTTP workflow was started. No live
version migration, secret rotation, webhook delivery, screenshot capture or visual inspection
was performed. This is source-backed guide evidence, not application/release acceptance.

## Rechecked first-run findings

1. WebhooksPage now permits New webhook without an event-declaring consumer API;
   WebhookDialog offers only Workspace events in that case. Disabled-button workaround removed.
2. authoring/consumer.py raise_consumer_api_version freezes the definition from context.base,
   even after breaking draft edits; an unserved version leaves no earlier copy. Undo/reapply
   workaround removed from all affected pages.
3. subscription_rules.py definition_findings now includes servedContractVersions in the
   subscription-create refusal, alongside current contractVersion and pointer. Documentation
   preserves HTTP 400 for creation versus HTTP 404 for a consumer read.
4. consumer_openapi.py now states that sunset is announced and service continues until the
   administrator removes the version. All pages explain explicit stopping.

## Remaining product finding and uncertainty

**The browser’s installation/activation summaries can conceal an earlier-version removal
warning.** `frontend/src/features/model-editor/InstallDialog.tsx:521` filters diagnostics to
errors for existing APIs and can render Compatible after a retained version is removed.
`frontend/src/features/model-admin/ActivateDialog.tsx:313` renders consumer diagnostics only
when contractsBreak is true. The engine produces CONSUMER_VERSION_STOPPED as a warning
(`backend/app/engine/model/consumer_contract.py:354`), so this deliberate stop does not make
that condition true. The Schema tab does render all contract diagnostics
(`frontend/src/features/model-editor/ConsumerApis.tsx:988`). The guide directs readers there
and explicitly describes the summary’s limit. No application code was edited.

No other source question was filled by guessing. Live behavior and screenshot appearance
remain unverified; the three capture requests are the only built-link blockers observed.
