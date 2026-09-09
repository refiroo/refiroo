# Technical documentation reconciliation — ADR-027

**Updated:** 2026-09-08. **Scope:** Documentation and planning only, against working-tree base
`60b99d3` plus pre-existing uncommitted implementation. The user accepted GAP-01–GAP-08 in
[the product handoff](product-functionality/PLANNING_HANDOFF.md) and authorized this update.

This replaces the earlier 2026-09-07 cross-document discrepancy checklist. Its historical 312-test,
Ruff and frontend-build report is not fresh validation and did not establish all authority boundaries.
The conclusions below distinguish documentary reconciliation from outstanding runtime work.

## Reconciliation of prior findings

| Prior finding | Documentary resolution | Runtime/evidence status |
| --- | --- | --- |
| A: live data authority contradicted by revision-projection language | Current product, architecture, status, roadmap and Base 0.6 contracts now use live rows for current data and revisions for immutable history | Live paths exist; all-live model compatibility remains WP8.1-A |
| B: ADR-024/025 and older relation/containment decisions contradicted ADR-026 | Canonical clauses consolidated directly; ADR-027 records accepted user answers and earlier decisions link to the amendments | No per-record lifecycle or new API introduced by docs |
| C: cursors claimed model/active-revision binding not present in code | API, architecture, decisions and UI distinguish current live query tokens from explicit draft/history identities | Stronger future guarantees require implementation; live cursors remain non-snapshot reads |
| D: deletion error spelling and payload differed from code | API documents `object_has_dependants`, actual dependent rows, legacy `objectsToRetire`, concise relationship rows and counts | Source checked; no delete regression test executed in this pass |
| E: WP9 and release plan required drafts for all writes | Current plan requires normal live CRUD and optional drafts; old WP0–WP8 bodies are explicitly historical records | WP9 UI completion and WP10 composed evidence remain pending |
| F: status/README handed off a draft-only UI | Both point to WP8.1 → WP9 → WP10 and separate actual availability from intended browser tasks | No new runtime completion claim |
| G: API payloads described only draft writes | Route-specific live/draft fields, claims, read tokens and response nullability documented | Current omitted context enforcement is identified for correction; no undocumented payload field added |
| Low cluster: release wording, amendment layering, forward milestones and command divergence | Product/roadmap bodies rewritten; unreleased changelog distinguishes docs from code; plan owns canonical validation commands; specialists preserve live maintenance | All runtime and release checks remain executable obligations |

Historical/rejected material remains labelled in ADR-020, the WP0–WP8 record, Base 0.5/refactor plans
and the changelog. It is not a competing instruction for the next package. Source-analysis next-step
wording now points to the current roadmap rather than instructing premature mapping implementation.

## Accepted product decisions and remaining delivery

| Area | Accepted direction | Implementation owner |
| --- | --- | --- |
| Daily browser use | Preserve workspace context, complete coherent live editing, keep drafts optional | WP9; SC-01–SC-04 |
| Current-live draft base | Copy actual live records/fields/edges and model/record versions, including no publication | WP8.1-B; SC-05 |
| Historical source | Named immutable revision; authored changes only, never direct restore | WP8.1/WP9; SC-08 |
| Publication retirement | Remove current-publication designation; retain live access and history | WP8.1-C complete; WP9 UI; SC-08 |
| History order | Newest first, deterministic bounded paging | WP8.1-C complete; WP9 UI |
| Model/history authority | All live data constrains current model; pinned supported model interprets history | WP8.1-A; SC-12/SC-13 current-boundary variants |
| Historical schema incompatibility | Preview loss and confirm exact migration or cancel; separate data/model drafts and workspace assignment | Product 0.10; US-P07/SC-13 migration variants |
| Validation and simple flows | Actual composed journey evidence, two configurations, preserved input and explicit complexity comparison | WP10 and each later release |

The historical migration is not a force flag. Base 0.6 preserves incompatible drafts and refuses
activation. The 0.10 plan must transform/validate data and switch only the selected workspace model
assignment atomically after a fresh reviewed confirmation. Cancel, stale review and failure change
nothing; immutable history and other workspaces remain unaffected. Unsupported schema languages still
require parser/runtime support.

## Review and checks performed for this documentation update

- A final read-only architecture/plan review passed the authority and release boundaries after one
  clarification: migration targets a named installed immutable release, normally the historical pin,
  for one workspace only. The preview cannot ambiguously mean silently repinning the historical draft.
- Reused targeted read-only API discovery and architecture analysis; checked the actual route/model
  declarations where inputs, response nullability, initial relationships or cursor claims differed.
- Checked local Markdown links and anchors, table column counts, code fences and whitespace across
  changed documents. Checked all 60 story IDs against the product validation matrix and retained IDs.
- Searched canonical documents for stale draft-required, live-revision-authority, direct-history-restore
  and next-package wording. Superseded text remains only where explicitly historical or quoted as a
  regression pattern/user decision.
- Compared hashes of backend source/tests, frontend source and model files with the pre-edit snapshot;
  this task changed none of those files. User-owned pre-existing implementation remains intact.
- Ran `git diff --check`. No backend/frontend/browser/migration suites ran for this documentation task.

The temporary authority review under `review-notes/adr026-authority-2026-09-07/` remains a dated input,
not current decision authority. ADR-027 and the current Base 0.6 plan now resolve its planning direction.
No implementation checkbox is closed from a documentation check.
