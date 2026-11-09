# D-ABOUT depth review

## Inventory and scope

All nine existing inventory JSON files were inspected for section `about`: zero entries. The uncovered inventory likewise has no About entries. The 45 source-record coverage rows remain the evaluator scope; C0038 is an existing test-matrix exclusion, not a code inventory item. No inventory generation or new exclusion is needed.

Instructions read on disk: guide/AGENTS.md, D-ABOUT.md, COMPLETE-COMMON.md, DEPTH-COMMON.md. Top-level agent instructions do not apply by explicit assignment. No memory used.

Baseline word counts are in before.json. Existing About and journey pages have been read. Other sections have first been surveyed by page and heading; targeted page and source reads follow for additions. The initial oversized combined read was truncated and the relevant pages were reread in bounded batches.

About owns evaluator explanations and links; setup, literal errors, lifecycle recovery and removal procedures remain on their reader-specific pages. This follows the settled section structure, rather than duplicating operator or administrator steps on evaluator pages.

## src/content/docs/about/what-is-refiroo.md
Definition and purpose: overview, fit and responsibilities retained; capability catalogue added. Setup/change/failure/access: routed to owning capability pages and journeys; absence reasons explained. Expiry/recovery/removal: no overview-specific lifecycle; links delegate to the concrete capability. Sources: other Use pages and task guides, copying-and-moving.md, applications.md; transfer staging verified in backend/app/engine/moves/move_load.py. No open depth question.

## src/content/docs/about/how-it-works.md
Purpose/setup/change: model editor, view declarations, page design and validation linked. Recovery/removal: immutable releases and migrations explain effects; hiding is distinguished from deleting. Permissions: model-administrator ownership, with details on model pages. Expiry: not applicable to definitions; language window linked through releases. Sources: model/record-pages-and-tables.md, model/json-view.md, applications-and-views.md and model task guides; frontend/src/features/model-editor/operations.ts and TypePreview.tsx confirm navigation and layout actions. No open question.

## src/content/docs/about/three-kinds-of-change.md
Purpose/change/removal: all three change paths plus availability and retirement distinguished. Setup/access/failure/recovery: retained links to record, approval, release, migration and backup owners. Expiry: business validity is separate from scheduling. Sources: guide/use/stop-offering-a-value.md; run/model-releases-and-rollback.md; model/managing-workspaces.md. No open question.

## src/content/docs/about/data-quality-rules.md
Rules, conflicts, refusal recovery, deletion impact, atomic versus independent outcomes and history already covered. Added limits and human review boundary. Setup/change of rules belongs to model administrator pages; expiry/removal of a rule follows model release/migration, not an independent lifecycle. Sources: backend/app/engine/records/rules.py; use/lists-and-filters.md, changing-many-records.md, copying-and-moving.md. No open question.

## src/content/docs/about/sharing-data-with-other-systems.md
Purpose/read states/consumer grants/file exchange/feed expiry and webhook duplication already covered. Added discovery, precise reads, access, versions, jobs, approval, model operations, compatibility and assistants. Literal requests, errors, defaults and recovery remain with Integrate; About contains no API paths, tokens or payloads. Sources: integrate overview and journey pages, reading-records, workspaces-contexts-and-models, assistant-tasks, assistants-and-agents. No open question.

## src/content/docs/about/people-and-access.md
Purpose/permissions and next-request revocation covered; added setup/change/removal and lockout safeguards with links. Expiry/rotation: signing keys and client credentials linked; recovery: provider and lost-device procedures linked. Sources: administer pages and custom-role/local-sign-in task guides; backend/app/engine/authorization/administration.py and engine/identity/providers.py confirm safeguards. No open question.

## src/content/docs/about/security-and-trust.md
Access, credentials, HTTPS renewal, attribution, sharing, optional AI send levels, review, retention, cost and revocation reviewed. Corrected port 80 requirement against compose.acme.yml and caddy/Caddyfile. Saved-profile/session distinction checked in integrate/assistant-tasks.md. Setup/recovery/key rotation/removal remain with the Run, Administer and AI pages linked here. No new product defect established; prior guide wording was wrong.

## src/content/docs/about/how-it-is-built.md
Architecture/technology/standards/local documentation/processes/jobs/readiness retained. Setup/change/growth/renewal/recovery/removal: links to the specific Run owners added; capacity explicitly unmeasured. Sources: run/overview.md, model-releases-and-rollback.md, production-checklist.md; compose.acme.yml and caddy/Caddyfile. No open question.

## src/content/docs/about/compatibility-and-licence.md
Purpose/versions/default source offer/compatibility window reviewed. Access and diagnostics linked. Change/removal/expiry apply to deprecation and language support rather than licence controls; existing language/recovery, upgrades and source-offer links supply procedures. Legal texts linked as original policy, no new interpretation. Sources: administer/deployment-pages.md, model/model-language-versions.md and integrate/compatibility.md. No open question.

## src/content/docs/about/accessibility.md
Purpose/setup/change/defaults/reset covered; no privilege beyond signed-in personal preferences. Preferences have no expiry; browser storage loss resets them. Keyboard alternatives, drawn-list search limitation and lack of recorded screen-reader user testing retained. Sources: frontend/src/features/settings/AppearancePage.tsx and use/appearance-and-devices.md. Existing list-phone.png retained; no new screenshot necessary. No new accessibility test or conformance claim.

## src/content/docs/journeys/look-after-data.md
All existing daily-data journeys reviewed. Added missing file/transfer/availability/navigation/display tasks from Use guides; exact access and move order verified in copying-and-moving.md and move_load.py. Default and removal consequences explained where relevant. No new screenshots: linked task pages already own them. No open depth question.

## src/content/docs/journeys/change-with-approval.md
Existing proposal/review/approval/model-pin/publication journeys retained and reviewed. Added growth/lifetime, abandonment and ambiguous-result recovery from integrate/changes-approvals-and-publication.md, checked against the consumer-facing Use lifecycle. No exact error quoted without a source. No open question.

## src/content/docs/journeys/shape-a-model.md
Depth applied across existing model journeys and new tasks: setup, change effects, preview/refusal, permission, release language, recovery and removal all linked to owner guides. Sources: model pages, model task guides read in this run; frontend/src/features/model-editor/operations.ts and TypePreview.tsx. Specialist workbench linked without exposing document syntax in browser prose. No open question.

## src/content/docs/journeys/manage-access.md
Setup/rotation/removal/next-request changes/recovery and administrator lockout safeguards addressed across each access capability. Existing client and key journeys retained. Sources: administer pages and task guides; engine/authorization/administration.py and engine/identity/providers.py. No new screen required; linked guides own screenshots. No open question.

## src/content/docs/journeys/run-the-service.md
All Run capability owners linked; setup/change/renewal/growth/failure/recovery/move/removal/access addressed as applicable. Sources: Run overview, production checklist, model rollback, HTTPS, configuration and backup owners; compose.acme.yml confirms 443-only certificate route. No new commands or settings invented. No open question beyond workload sizing already explicitly unmeasured.

## src/content/docs/journeys/integrate-a-system.md
Existing read/filter/bulk/job/feed/file/consumer/lookup/webhook journeys held against depth. Added missing automation ownership and ambiguous-result recovery. Sources: integrate/assistant-tasks.md, changes-approvals-and-publication.md, model-and-release-operations.md and transfer task guide. Defaults, literal errors and request schemas remain in linked contracts. No open question.

## src/content/docs/journeys/work-with-an-assistant.md
All AI capabilities previously present reviewed: access/send-level/cost/retention/failure and human review covered. Added saved-layout activation exception and lifecycle off-switches. Sources: integrate/assistant-tasks.md and Use AI pages; no new AI behavior inferred. Existing screenshots retained, no new image request.

## src/content/docs/journeys/receive-notices.md
Purpose/setup/default Off/time-zone schedule/50-item digest/permissions/failure/retry/stop and retained preferences already covered. Sources: use/notifications-settings.md, administer/mail.md and integration notification sequence. No added settings or claims. No open question.

## src/content/docs/journeys/index.md
Navigation index: each link derived from an actual journey heading, keeping the established section order. No independent setup/lifecycle/permissions apply; those belong to the linked journeys. Built anchor checks will verify targets. No open question.

## src/content/docs/index.md
Landing page reviewed for all readers; purpose and entry points kept short, with no repeated task instructions. New links target existing documentation owners. No independent expiry/recovery/removal applies. No open question.

## src/content/docs/about/how-it-is-built.md
Editorial correction only; no behavior change.

## src/content/docs/about/sharing-data-with-other-systems.md
Editorial correction only; no behavior change.

## _waves/screens-wanted/D-ABOUT.md
Screenshot unit: existing illustrations remain attached to their original explanations. New content links to the owning task pages. No added placeholder or requested image.

## _waves/coverage/about.md
Coverage accounting: 45 rows, 44 reader-facing covered, 1 existing non-reader row, 0 open; 0 code-inventory About entries. No edits to global exclusions required. Depth review is page-based, not a claim that inventory matching alone establishes documentation quality.

## src/content/docs/about/sharing-data-with-other-systems.md
Final reader-language review; link destination unchanged.

## src/content/docs/about/how-it-is-built.md
Applied guide rule 2 in the final reader-language review; named protocols and technologies remain where relevant.

## src/content/docs/about/how-it-works.md
Editorial agreement correction; no behavior change.

## src/content/docs/about/security-and-trust.md
Label verified against backend/app/management/routers/ai_tasks.py permission checks and linked guide terminology.

## _coverage/notes/D-ABOUT/report.md
Final evidence: 252 built pages; all 911 inventory entries accounted for (902 covered, 9 excluded). No About inventory items and no open About coverage rows. All D-ABOUT page links pass. The full link gate remains open solely for eight out-of-scope images. No browser, runtime or visual acceptance claimed; no processes started.
