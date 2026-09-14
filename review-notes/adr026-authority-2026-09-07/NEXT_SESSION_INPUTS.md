# Inputs for the next planning/revision session

## Stop/go recommendation

Do not execute the current WP9 specification yet. Insert a corrective WP8.1 authority-boundary package,
then rewrite WP9 and WP10 against the accepted outcome.

## Decision gates

### D1 — publication availability

Decide whether a workspace can be unpublished while remaining catalogue-active.

- If no: remove or rename publication retirement and treat revisions as immutable checkpoints/history.
- If yes: introduce a distinct publication-availability authority and specify which consumer/steward
  reads and writes are available while unpublished.

Do not use `active_revision_id` as both "latest checkpoint" and "is published" without one precise
behavioral contract.

### D2 — draft base

Decide how a coordinated-data draft starts from current live content.

- Preferred: capture an immutable internal base snapshot at draft creation.
- Alternative: provide an explicit current-live checkpoint/branch operation and define root drafts as
  empty/history-only branches.

The base must carry record versions for conflict detection. Intentional branching from older history
should remain separately available and visibly distinct.

### D3 — model scope for history

Confirm that a workspace revision is always interpreted using its pinned model release. Otherwise,
remove the misleading pin and define historical-data migration rules explicitly.

### D4 — model compatibility population

- All live rows should constrain global model activation because the active model serves them.
- Catalogue-retired but readable live rows should also constrain it unless reads use a pinned model.
- Historical revisions can be excluded only when their reads consistently use their pinned model.

## Corrective WP8.1 package

1. Record D1-D4 in one consolidating ADR instead of another detached amendment layer.
2. Correct compatibility analysis to use the accepted live-data population.
3. Implement the accepted current-live draft-base mechanism.
4. Resolve historical reads through the revision's pinned model.
5. Align retirement/checkpoint API names and behavior with D1.
6. Add direct regressions for every authority transition.
7. Rewrite canonical documentation so it states the current rules directly.

Exit gate:

- Exactly one authority exists for every concern in the authority table.
- Live-only rows cannot escape model compatibility analysis.
- A draft can truthfully start from current live content.
- Old revision data remains readable after model activation.
- Retirement/checkpoint behavior matches its name and UI meaning.
- No correction relies only on an amendment after contradictory prose.

## Revised WP9 input

Reuse the generic CRUD components in explicit content modes:

- **Live:** CRUD enabled without a draft; record-level `expectedVersion`.
- **Draft:** same components receive `workspaceDraftId`, draft version and record version.
- **History:** immutable and rendered with the revision's pinned model.
- **Catalogue-retired:** readable with all mutations disabled.
- **Publication/checkpoint:** presented according to D1 using truthful terminology.

WP9 must cover at least two object types and preserve dirty-input, busy, focus, keyboard, retry and
conflict recovery. It must not add nested draft CRUD resources or starter-key branches.

## Revised WP10 input

WP10 must validate these product journeys:

1. Live canonical-data creation and update without creating a draft or revision.
2. Live attribute, containment, relation and translation mutations.
3. Coordinated draft creation from the actual current live graph.
4. Live writes while that draft is open.
5. Activation/apply preserving untouched live changes.
6. Touched-record conflict publishing nothing and preserving draft plus live data.
7. Live-only content blocking an incompatible model release.
8. Historical content remaining readable and correctly typed after model activation.
9. Publication retirement/checkpoint behavior matching D1 in API and UI.
10. Browser, keyboard, accessibility and visual coverage of live, draft, history, conflict and retired
    states.
11. Migration, boot/restart, wheel, OpenAPI, backend tests/Ruff and frontend lint/tests/build with no
    relevant skipped suites.

## Future release classification

| Release area | Default expectation | Optional coordinated path |
|---|---|---|
| Mapping replacement | Live atomic relation-set mutation | Drafted mapping set applied later |
| Translation maintenance | Live data mutation | Staged translation campaign |
| Hierarchy maintenance | Live atomic parent plus typed-edge mutation | Coordinated restructure draft |
| Bulk/integration | Explicit live bulk/upsert contract | Preview/stage/apply job when requested |
| Application-model changes | Never live data CRUD | Model draft, validation, install, activation |

ADR-022 atomic mapping concurrency remains valuable in both live and staged modes. A workspace draft
must not become mandatory merely because an operation touches multiple records.

## Documentation revision map

1. `PRODUCT.md`: explicitly state daily live maintenance and when coordinated review is optional or
   required. Current wording implies this but does not fully specify workflow.
2. `ARCHITECTURE.md`: replace superseded paragraphs with the complete authority model and D1-D4.
3. `DECISIONS.md`: mark ADR-024/025 clauses as amended inline and add one consolidating final decision.
4. `BASE_0_6_IMPLEMENTATION_PLAN.md`: rewrite the outcome, principles, contracts, journeys, WP7-WP10
   bodies and acceptance criteria rather than appending another amendment.
5. `ROADMAP.md`: rewrite 0.6 and classify 0.7-0.9 mapping, translation, hierarchy and integration work.
6. `APPLICATION_MODEL.md`: distinguish live validation from staged whole-graph validation.
7. `API.md`: document live and optional-draft branches, cursor identities, delete error spelling and
   the settled retirement/checkpoint contract.
8. `PROJECT_STATUS.md`, `README.md`, `CHANGELOG.md`, `TODO.md`, `UI_MODEL.md`: remove stale draft-only
   handoffs and authority language.
9. `REVIEW.md`: add the P0 findings, decision outcomes, evidence and resolution checkboxes.

No documentary correction should be committed until this handoff has been reconciled with the direction
chosen in the next session.
