# Runtime CRUD UI execution plan

**Status:** Implemented in model 0.4; retained as the execution record  
**Scope:** Generic UI CRUD for runtime objects, object attribute values and object relations  
**Not in scope:** Editing attribute-type, object-type or relation-type definitions in the immutable
application model

## Handoff instructions

Before implementing this plan, read `AGENTS.md` and the required project documents in its stated order.
Treat the current worktree as user-owned: inspect `git status`, preserve unrelated changes and do not
revert or rewrite them. Implement the phases below in order and keep the application generic; no React
or Python branch may depend on starter keys such as `master-value`, `system-value` or
`system-value-maps-to-master`.

The word **relationship** in the UI maps to the repository's **relation** API and types.

## Product outcome

A user can manage the runtime graph without leaving the model-generated application UI:

1. Create, inspect, edit and safely delete an object.
2. See every configured object attribute, add a missing optional value, edit a stored value and remove
   a stored optional value.
3. See relationships in the direction configured by a detail panel, create an allowed relationship,
   edit its configured attributes and delete it when it is not engine-maintained.
4. Receive a clear, recoverable message when optimistic concurrency, uniqueness, cardinality or
   dependency checks reject a mutation.

The implementation must work through model definitions and stable public IDs. Exercise every generic
renderer with at least two object types, and exercise relation handling in both incoming and outgoing
directions.

## Scope interpretation

This slice is runtime-data CRUD. The immutable JSON model remains the source of truth for applications,
attribute types, object types, attribute bindings, relation types, allowed pairs and detail panels.
CRUD for those definitions would require draft models, validation previews, release creation and
migration planning; that is the later **Model administration** roadmap slice and must not be smuggled
into this work.

No schema-language change is required for the runtime CRUD UI. Existing object-type bindings determine
attribute editability, existing allowed relation triples determine valid endpoints and direction, and
the target object's `behavior.parentRelationTypeKeys` determines whether a relation is engine-managed.
Do not add presentation flags until two real workflows demonstrate a need that cannot be derived from
those semantics.

## Current baseline and gaps

### Objects

- Collection and detail reads are implemented.
- `ObjectFormDialog` creates objects and currently combines core-object and attribute editing.
- Object updates use `expectedVersion`, but the form does not expose `state`.
- The frontend client and detail screen do not expose object deletion.
- The backend already rejects deletion when children or non-parent relations remain and removes an
  incoming containment relation atomically when deletion is allowed.

### Attribute values

- Object responses already include stored, typed attribute values.
- The backend has individual `GET`, `POST`, `PATCH` and `DELETE` child-resource endpoints.
- The attributes panel is read-only, and the frontend client has no methods for those endpoints.
- Required and read-only bindings already have backend guards. Attribute writes claim the containing
  object's version. `POST` and `PATCH` return the refreshed object; `DELETE` returns `204`, so the UI
  must refetch the object after deletion.
- A binding with no `ObjectAttributeValue` entry is **unset**. Do not infer stored/unset from a falsy
  value: `false`, `0`, an empty JSON value and `null` are distinct from absence of the response item.

### Relations

- The relation panel reads expansions but discards relation ID, version and attributes when it maps
  results into `ObjectTable`.
- The backend already supports create, read-one, attribute replacement and delete for non-parent
  relations, with cardinality and optimistic-concurrency checks.
- Relation identity is immutable. Retargeting is delete plus create, not a `PATCH` of endpoint IDs.
- Parent/containment relations are readable but return `immutable_relation` for direct mutations;
  users change them through the object's parent field.
- Relation expansion is currently unpaged. Keep pagination/batched expansion as the separately tracked
  scale gap unless the implementation deliberately takes on that API contract as a prerequisite.
- The existing object list API can omit `applicationKey`. Relation candidates must use that ability
  because allowed relations can cross applications, as the starter model already demonstrates.

## UX and behavior contract

### Object CRUD

- Keep create actions in configured collection, child and parent-filtered table contexts.
- In create mode, render the name, applicable parent selector and all visible editable attribute
  bindings in binding order. Preserve server defaults and typed values.
- In edit mode, edit core object fields only: `name`, `state` and `parentObjectId` where the model permits
  a parent. Attribute value actions live in the attributes panel so there is one unambiguous place for
  attribute create/update/delete.
- Keep application, object type, workspace and public ID immutable in the edit UI.
- Add a destructive **Delete object** action on the detail page. Require an explicit confirmation that
  names the object and explains that children and relationships must be removed first.
- Send the detail's current `version` as `expectedVersion`. On success, navigate to the best matching
  configured collection view and refresh the explorer/list state. On `object_has_dependents`, keep the
  page open and show the server message. On `version_conflict`, reload the object before allowing a
  retry.

### Attribute-value CRUD

- The attributes panel continues to honor its configured `fields` order. Built-in fields remain
  display-only; only fields backed by an object-type attribute binding get value actions.
- For a stored, editable value, show **Edit**. For a stored value whose binding is optional, also show
  **Remove** behind confirmation.
- For an unset, editable optional value, show **Add**. Required values are supplied during object
  creation and cannot be removed. Read-only bindings never show mutation actions.
- Use one shared typed field renderer for object creation and single-attribute editing. It must preserve
  `text`, `longText`, `integer`, `decimal`, `boolean`, `date`, `dateTime` and `json` as their declared
  JSON types and apply existing `ui.helpText`, hidden, required, minimum and maximum hints.
- Choose `POST` or `PATCH` from whether the response contains a stored value item, not from its value.
- Use the current object version for every write. Replace the parent `ObjectItem` state with the object
  returned by `POST`/`PATCH`. After a successful `DELETE`, refetch the object because the endpoint has
  no response body but did advance the version.
- Surface validation, uniqueness and version errors beside the active field dialog. A version conflict
  must offer or perform a refresh; never silently replay a stale write.

### Relationship CRUD

- Replace the relation panel's object-only projection with a relationship table/view model that retains
  the expansion direction, relation ID, relation version, relation attributes and related object.
- Display the direction-correct label: use the relation type's forward name for outgoing rows and
  reverse name for incoming rows. Continue to render configured related-object columns generically.
- Derive creation choices by intersecting:
  1. the panel's `relationTypeKeys` and direction;
  2. `model.objectTypeRelations` entries whose current-object side matches the direction; and
  3. relation types that are not engine-maintained for the allowed pair's target type.
  Do not require the other endpoint's object type to belong to the current application: configured
  relationships may cross application boundaries.
- For an outgoing choice, anchor the current object as `fromObjectId` and select a target. For an
  incoming choice, anchor it as `toObjectId` and select a source. A `both` panel may offer both valid
  orientations. Self-relations must preserve the selected orientation explicitly.
- Exclude engine-maintained parent relations from create/edit/delete choices. Existing managed rows stay
  visible with a **Managed through Parent** indicator and point users to the object's Edit action.
- Use a debounced, server-side, cursor-paged object lookup for the other endpoint. Do not copy the
  parent picker's `fetchAllObjects` approach. Permit `applicationKey` to be omitted so cross-application
  candidates are discoverable, show application/path context in results and retain the default
  workspace boundary.
- Render configured relation attributes from the matched allowed pair's `attributeTypeKeys` using the
  same typed field primitives. Send them as the API's keyed `attributes` object. If no relation
  attributes are configured, creation still works and the Edit action is omitted because there is no
  mutable content.
- Update only relation attributes with `PATCH` and the row's `version`; endpoints and relation type are
  immutable. Deleting and recreating is a separate, explicitly confirmed retarget operation and must
  not masquerade as an atomic edit.
- After create/update/delete, reload only the affected relationship panel. Show `duplicate_relation`,
  `cardinality_violation`, `immutable_relation` and `version_conflict` without discarding the user's
  dialog state. Refresh the row before retrying a stale update.

## Implementation phases

### Phase 1 — Preserve API errors and complete the frontend adapter

Files:

- `frontend/src/api/client.ts`
- `frontend/src/types.ts`
- new `frontend/src/api/client.test.ts`

Tasks:

1. Introduce an `ApiError` carrying HTTP status, machine-readable `code`, `message` and optional
   `details`; keep non-JSON failures readable. Components must not parse `Error.toString()` to make
   decisions.
2. Make `ObjectQuery.applicationKey` optional and add `workspaceKey` as an optional explicit filter.
   Existing collection calls continue to provide their application key; cross-application relation
   lookup omits it.
3. Broaden the object update payload to a true partial patch plus required `expectedVersion`.
4. Add `deleteObject(objectTypeKey, objectId, expectedVersion)`.
5. Add typed attribute-value methods for read, create, update and delete.
6. Add relation methods for create, read-one, update and delete. Let relation expansion accept optional
   direction and relation-type filters already supported by the backend.
7. Extend `ObjectTypeRelationDefinition` with `required`, `attributeTypeKeys` and `features`, matching
   the model contract. Introduce named types for relation records, expansion rows, attribute-value
   responses and write payloads instead of nested anonymous shapes.
8. Unit-test URLs, query encoding, request bodies, `204` handling and structured error preservation.

Exit criteria: every existing runtime mutation endpoint is reachable through a typed frontend method,
and callers can branch on server error codes.

### Phase 2 — Extract reusable form and dialog primitives

Files:

- `frontend/src/components/ObjectFormDialog.tsx`
- new `frontend/src/components/AttributeField.tsx`
- new `frontend/src/components/ConfirmDialog.tsx`
- new `frontend/src/components/ObjectLookup.tsx`
- `frontend/src/styles.css`

Tasks:

1. Extract typed input rendering and form-value conversion from `ObjectFormDialog`. Conversion must be
   covered independently, especially boolean false, numeric zero, JSON parse errors and date/time
   strings.
2. Split object-create fields from core-object edit fields as described above. Keep parent derivation
   generic and preserve the existing context-supplied parent behavior.
3. Replace `fetchAllObjects` with a reusable, debounced, server-side, cursor-paged object lookup. Use it
   with the current application filter for parent selection and later without that filter for
   cross-application relationship candidates.
4. Add a reusable confirmation dialog with destructive styling, pending state, focus placement, focus
   return, Escape handling and semantic dialog labelling. It must not close from a backdrop click while
   a mutation is pending.
5. Keep keyboard operation and visible focus states. Do not introduce a component library solely for
   this slice.

Exit criteria: object creation still supports every declared value type, core edits no longer rewrite
unrelated attribute values, and destructive actions have one accessible confirmation primitive.

### Phase 3 — Finish object CRUD

Files:

- `frontend/src/components/ObjectDetail.tsx`
- `frontend/src/components/ObjectFormDialog.tsx`
- `frontend/src/App.tsx`
- focused component tests

Tasks:

1. Add state editing and send only changed core fields plus `expectedVersion`.
2. Add object deletion with confirmation, loading/error states and dependency/version-conflict handling.
3. Add an `onDeleted` path from `ObjectDetail` to `App` that returns to the matching view and refreshes
   the explorer. Do not leave a route pointing to a deleted UUID.
4. Ensure a successful object edit replaces the detail's object state and version before another child
   mutation can run.

Exit criteria: create/read/update/delete works from the UI for a root-creatable type and a contained
type, including successful deletion of a child whose engine-managed parent relation is removed by the
backend.

### Phase 4 — Add attribute-value CRUD to the detail panel

Files:

- `frontend/src/components/ObjectDetail.tsx` or an extracted
  `frontend/src/components/AttributesPanel.tsx`
- new `frontend/src/components/AttributeValueDialog.tsx`
- shared field/dialog files from Phase 2
- focused component tests

Tasks:

1. Lift an `onObjectChanged(savedObject)` callback into panel props so an attribute mutation updates the
   authoritative detail object and concurrency token.
2. Render stored/unset state and the correct actions from binding metadata.
3. Implement add/edit/remove against the individual attribute endpoints and preserve dialog state on
   errors.
4. Refetch the object after delete, then notify the explorer/collection refresh hook.
5. Keep hidden, read-only and required behavior consistent between create forms and detail actions.

Exit criteria: an optional value can move through unset -> stored -> updated -> unset, while required
and read-only values cannot be removed or edited contrary to the model.

### Phase 5 — Add relationship CRUD to relation panels

Files:

- extract `frontend/src/components/RelationsPanel.tsx` from `ObjectDetail.tsx`
- new `frontend/src/components/RelationTable.tsx`
- new `frontend/src/components/RelationFormDialog.tsx`
- reuse `frontend/src/components/ObjectLookup.tsx`
- `frontend/src/utils/model.ts`
- focused utility and component tests

Tasks:

1. Add pure model helpers that derive direction-aware relation choices, allowed pairs, labels and
   mutability. Test the same helpers with two unrelated synthetic relation types; do not rely only on
   starter keys.
2. Preserve the full expansion row in the table and add row-level Edit/Delete actions only when the
   relation is mutable.
3. Implement the paged candidate-object lookup and direction-correct create payload.
4. Implement configured relation-attribute editing and optimistic-concurrency deletion.
5. Refresh relation data after each success without refetching unrelated object collections.
6. Keep managed containment relations readable and immutable in the UI.

Exit criteria: users can create and remove both incoming- and outgoing-configured non-parent relations,
edit configured relation attributes, and cannot directly mutate a containment relation.

### Phase 6 — Integration, documentation and polish

Files:

- `frontend/src/styles.css`
- `docs/UI_MODEL.md`
- `docs/PROJECT_STATUS.md`
- `README.md` and `CHANGELOG.md` if the project version/release process requires them
- `docs/API.md` only if the implementation changes an API contract
- `docs/DECISIONS.md` only if a new durable tradeoff is introduced

Tasks:

1. Check responsive layouts, long names/paths, empty panels, loading states, retry behavior and visible
   destructive affordances.
2. Update documentation from future-tense/read-only wording to the implemented behavior and retain the
   distinction between runtime CRUD and model administration.
3. Record relation expansion pagination as a known gap if it remains outside this slice.
4. Do not add an ADR for ordinary component factoring. Amend ADR-011 only if UI behavior needs
   clarification; add a new ADR only for a genuinely new contract or architectural tradeoff.

## Test matrix

### Frontend automated tests

- API adapter preserves `status`, `code`, `message` and `details`; handles `204`.
- Object create and edit preserve typed fields and send the current expected version.
- Object delete success navigates away; dependent and stale deletes remain recoverable.
- Attribute add versus edit is selected by item presence, including `false`, `0` and `null` values.
- Attribute delete refetches the object and advances the displayed version.
- Required/read-only/hidden attributes expose only permitted actions.
- Relationship choices are correct for outgoing, incoming, both and self-relation cases.
- Cross-application candidate lookup omits the application filter and paginates/searches on the server.
- Relation create payload orientation is correct; update/delete use the relation version.
- Managed parent relations render without mutation controls.
- The same attribute and relation components work with at least two object types and two relation
  definitions.
- Dialogs have accessible names, keyboard dismissal when safe and disabled controls while saving.

Use Vitest and Testing Library already present in the repository. Add `@testing-library/user-event`
only if it materially improves realistic keyboard/form coverage; do not introduce a second test stack.

### Backend regression tests

No backend endpoint change is expected. Existing tests must continue to cover:

- object dependency and version-conflict deletion;
- attribute create/update/delete validation and object-version claims;
- relation cardinality, immutability and relation-version claims; and
- unified machine-readable error envelopes.

If implementation discovers that a required UI behavior cannot be expressed by the documented API,
stop and update this plan before changing the backend. Add service and router tests first, then document
the contract change in `docs/API.md`.

### Manual smoke scenarios

1. Create a root object, edit its name/state, add/edit/remove an optional attribute and delete it.
2. Create a contained object from a child panel, reparent it, then delete it and confirm its parent
   detail no longer lists it.
3. From a detail with an outgoing relations panel, search across applications, create a relation, edit
   configured relation attributes and delete the relation.
4. Repeat from an incoming relations panel and verify endpoint orientation and direction labels.
5. Open the same object or relation in two browser tabs, mutate in one and confirm the stale tab reports
   a version conflict and refreshes before retry.
6. Attempt to delete an object with children or non-parent relations and verify that the page explains
   what must be removed.
7. Verify that a containment relation is visible but has no direct edit/delete control.

## Required validation commands

Run from the repository root with the supported Python 3.14 and installed project dependencies:

```bash
python -m ruff check backend
python -m pytest backend/tests
npm --prefix frontend test
npm --prefix frontend run build
```

All four commands must pass. A frontend production build is required in addition to unit tests.

## Definition of done

- All product outcomes and phase exit criteria above are met.
- No runtime branch mentions an application, object-type, attribute-type or relation-type starter key.
- No collection silently loads every object for selectors; candidate discovery is server-side and
  cursor-paged.
- All writes use the latest object or relation concurrency token and never silently overwrite a newer
  version.
- Parent containment remains atomic and directly immutable through relationship controls.
- Attribute values keep their declared JSON types end to end.
- Errors remain explicit and machine-readable in the client, with useful user-visible recovery.
- Frontend components are exercised with at least two object types and relation directions.
- Tests, linting and the production build pass, and documentation matches the shipped behavior.

## Explicitly deferred work

- CRUD for model definitions and model-release administration.
- Permissions/OIDC and model-configurable operation authorization.
- Bulk object, attribute or relation mutation.
- Atomic relation retargeting/safe remapping beyond documented delete-plus-create semantics.
- Dedicated mapping-grid and hierarchy-tree editors.
- Cursor-paged or batched relation expansion, unless accepted as a prerequisite in a revised plan.
- Import/export, change feed, webhooks and database-level uniqueness hardening.
