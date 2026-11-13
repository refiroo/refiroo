# Build 0.17 code review

Reviewed on 2026-11-13 against the working tree at `0b29e581` (Version 0.17.1) plus the uncommitted
changes present that day. Line numbers are the working tree's.

The review read the code only. Project documentation, plans, decisions and agent guidelines were
left unread on purpose, so nothing here is measured against a written requirement: each finding is
what the code does, where, and why that looks wrong or repeated.

## How the review was done

- Backend (`backend/app`, about 155,000 lines) and frontend (`frontend/src`, about 140,000 lines)
  were mapped by size and by directory.
- Read in full: the request path (`main.py`, `management/access.py`, `management/errors.py`,
  `management/dependencies.py`, `management/paging.py`, `management/query_parameters.py`),
  authentication and tokens, passwords, sign-in and resets, permissions, cursors, the webhook
  address rules and client, the AI provider adapters and their call recording, the notice mail and
  digest code, the mail logo check, the frontend API client, session handling, permissions state
  and the shared in-place editing components.
- Read in part: the objects router, the import router, the job worker's header and dispatch, the
  AI router, the larger frontend pages named in the findings.
- Four mechanical cross-checks, each over the whole tree:
  1. every API path the frontend calls against the backend's route table;
  2. every error code the frontend names against the codes the backend raises;
  3. every action group the frontend checks against the backend catalogue;
  4. every stylesheet class against the source that could name it.
- Two sweeps for repeated code: function names defined in several files (backend and frontend),
  then the bodies of each candidate compared by hand.

Not done: no test, build or server was run, and nothing was executed against a database. The
section "Not covered" at the end lists the large modules that were not traced.

## Summary

No defect was found that loses data, bypasses authorization or breaks a main flow. The request
path, authorization declarations, identity code and outbound HTTP are consistent and defensive.

What was found:

| Kind | Count | Most important |
| --- | --- | --- |
| Product defects | 9 | Kept AI request content outlives its retention on a quiet instance (D1); two pages leave the person stuck after a stale-version refusal (D2); the Claude adapter retries at once (D3) |
| Misalignments | 6 | Eight stale-version codes with four detail shapes (M1); three number and date locales in one interface (M2) |
| Reuse, backend | 8 | 74 hand-written `pageSize` declarations; about 30 hand-written version checks |
| Reuse, frontend | 13 | Three copies of the text-in-place controller; a dozen pluralising and number helpers; the workspace list read four ways |

---

## A. Product defects

### D1. Kept AI requests and answers outlive `AI_LOG_CONTENT_DAYS` when no new call is made — Medium

`backend/app/engine/proposals/calls.py:140-146` empties the kept content of calls whose time is
up. It runs in four places: `record_in` (line 121) and `record_apart` (line 133), which commit, and
`call_page` (line 151) and `last_call` (line 165), which serve `GET /api/v1/ai/calls` and
`GET /api/v1/ai/status`. Those two routes never commit (`management/dependencies.py:24-30` closes
the session without one), so their `UPDATE` is rolled back. The answer hides the expired content,
but the rows keep it.

Nothing else removes it: no worker sweep calls `expire_content`. So the content is removed only
when a later provider call is recorded. On an instance where AI use stops, or is switched off,
requests and answers (which hold record values at send level `samples` or `values`) stay in the
database past the retention the operator set.

Also, each read of Settings › AI issues an `UPDATE` that locks the expired rows for the length of
the request and then undoes itself.

Suggested fix: move the expiry into the worker's hourly retention pass, where jobs and inbox
notices are already expired, and make the two reads filter by `content_expires_at` instead of
writing.

### D2. A stale-version refusal leaves two pages with no way forward — Medium

- `frontend/src/features/settings/ImportProfilesPage.tsx:290-306` saves a profile with the version
  it loaded. On `409 IMPORT_PROFILE_VERSION_CONFLICT`
  (`backend/app/engine/imports/profiles.py:864`) it shows the message and keeps the old version, so
  every further Save is refused the same way. The delete at line 569 behaves the same.
- `frontend/src/features/model-admin/ModelReleaseDetail.tsx:218-237` retires, restores or deletes a
  release with its `statusVersion`. On `409 MODEL_RELEASE_VERSION_CONFLICT`
  (`backend/app/engine/model/release_lifecycle.py:107`) the dialog stays open with the stale
  version.

The frontend names neither code anywhere. Record and relationship writes re-read on a conflict and
say so; these two do not, and the only way out is to reload the page, which drops the edits to an
import profile.

Suggested fix: treat both codes as the record editors treat `VERSION_CONFLICT`: re-read, keep the
person's input where it still applies, and say the item changed. See M1 for the cause.

### D3. The Claude adapter retries immediately, and the other adapter never retries — Medium

`backend/app/engine/proposals/claude.py:108-123` sends a request up to three times. A `429`, `529`
or `5xx` answer is sent again at once: there is no wait and the `retry-after` header is not read,
so the second and third attempts meet the same limit. A timeout is also re-sent at once; with the
default `AI_TIMEOUT_SECONDS` of 60 and `max_tokens` 16000 on a non-streamed request, a slow answer
can cost three full requests before the person sees a failure, and the call is recorded once.

`backend/app/engine/proposals/openai_compatible.py:66-76` has no retry at all, so the same passing
failure is a failed call on one provider and three attempts on the other.

Suggested fix: one retry helper for both adapters that waits (the `retry-after` value when given,
otherwise a growing delay) and does not re-send after a timeout of a long answer.

### D4. Lists of workspaces silently stop at the first page — Low

Five places read one page of `GET /workspaces` and treat it as all of them:

| Where | Page size | Effect past that many workspaces |
| --- | --- | --- |
| `frontend/src/features/settings/AccountPage.tsx:386` | 100 | "My permissions" misses the groups of grants in later workspaces |
| `frontend/src/features/model-admin/ModelWorkbench.tsx:158` | 100 | later workspaces are not listed under their release |
| `frontend/src/features/workspaces/UnavailableWorkspace.tsx:321` | 100 | later workspaces are not offered as a way out |
| `frontend/src/features/security/GrantDialog.tsx:102` | 500 | a role cannot be granted in a later workspace |
| `frontend/src/features/security/GrantsSection.tsx:41` | 500 | a grant in a later workspace shows its key, not its label |

Four other places read every page with `lib/everyPage` (`ui/NewMoveDialog.tsx:58`,
`ui/WorkspaceField.tsx:54`, `features/moves/MoveEditor.tsx:140`,
`features/settings/WebhookDialog.tsx:196`). The comment at `ModelWorkbench.tsx:157` says workspaces
are few, which makes this low, but the same list should not be complete in one dialog and cut in
another.

### D5. One person gets three different initials — Low

Three functions named `initials` disagree:

| Function | "Anna" | "Anna (temporary)" |
| --- | --- | --- |
| `frontend/src/ui/SettingsParts.tsx:20` (People, Groups) | `AN` | `AN` |
| `frontend/src/app/useMe.ts:61` (top bar) | `A` | `A` |
| `frontend/src/features/security/AccessList.tsx:31` (workspace access) | `A` | `A(` |

The third shows a bracket in an avatar. Suggested fix: keep one (the top bar's handles notes in
brackets best) and import it in the other two.

### D6. The interface decides by the wording of a message — Low

- `frontend/src/features/objects/RelationTableView.tsx:278` reloads after a refused batch when an
  item's message matches `/changed/i`. The backend gives each item a `code`
  (`backend/app/engine/records/relation_batch.py:76-93`) and answers `409` when any item is stale;
  the frontend's type for the items leaves `code` out.
- `frontend/src/features/sign-in/ResetPasswordScreen.tsx:20-27` rewrites the engine's sentence with
  `/You can try again in .*$/`, and line 140 picks the notice's tone with
  `message.startsWith("Too many")`. The answer already carries `error: "slowed"` and `waitSeconds`.

A reworded message changes the behaviour with no failing type or test to say so.

### D7. Account and Home pages send requests per workspace — Low

- `frontend/src/features/settings/AccountPage.tsx:387-390` reads the permissions and the whole
  model of every workspace; the model is used only for each application's hue.
- `frontend/src/features/home/HomePage.tsx:396-407` reads permissions, then publication requests
  and the approval policy, for every workspace.

The number of requests on opening either page grows with the number of workspaces. `GET
/me/action-groups` already names the workspaces where each group is held, which would tell Home
where the person approves in one request; the hue could come from the workspace list.

### D8. `ai_requested` skips the ceiling check when `asked` is omitted — Low, latent

`backend/app/management/ai.py:52-54`: with `asked=None` the function returns before the check that
a request's `sendLevel` is not above `AI_SEND_LEVEL` (lines 59-66). Every caller passes `True`
today (`routers/ai.py:152, 256, 276, 314, 357`, `routers/mapping.py:447`), so nothing reaches it.
A route that passes the caller's optional flag through, as the docstring describes, would let a
request choose a higher send level than the operator allows. Suggested fix: check the ceiling
before the `asked is None` branch, or remove the branch.

### D9. Small ones — Low

- `frontend/src/features/objects/RecordTree.tsx:319-332` and `:405-414` write `localStorage` inside
  a state updater. Updaters should have no effects; under StrictMode each runs twice.
- `frontend/src/features/objects/RecordTree.tsx:321` and `:324` hold commented-out code.
- `frontend/src/features/ai-tasks/AiTaskJourneyBar.tsx:26-43` stores one `localStorage` key per AI
  task and never removes it; `RecordTree` keeps every expanded record ID the same way.
- `backend/app/management/query_parameters.py:23, 92-99` caches a route's parameters by
  `id(route)`. Routes of a discarded application can hand their ID to a new route; this can only
  happen where applications are created repeatedly (tests).
- Stale comments: `backend/app/engine/proposals/provider.py:15` describes a `workbookLoad` purpose
  the type below it no longer has; `backend/app/engine/proposals/registry.py:28` names
  `AI_MAX_STEPS`, which no setting or field has.

---

## B. Misalignments

### M1. A stale version is refused under eight codes with four detail shapes

Codes: `VERSION_CONFLICT`, `CHANGE_SET_VERSION_CONFLICT`, `RELATION_SET_VERSION_CONFLICT`,
`MAPPING_VERSION_CONFLICT`, `MODEL_RELEASE_VERSION_CONFLICT`, `AI_TASK_VERSION_CONFLICT`,
`IMPORT_PROFILE_VERSION_CONFLICT`, and `VERSION_MISMATCH` inside a publication's validation.

Details:

| Shape | Where |
| --- | --- |
| `{currentVersion}` | records, relationships, users, clients, groups, roles, workspaces, subscriptions, mail settings, source files, AI tasks, import profiles |
| `{expectedVersion, actualVersion}` | model drafts (`engine/model/drafts.py:164, 196, 215`), draft history (`engine/model/authoring/history.py:296`), publish (`engine/change_sets/publish.py:289`) |
| `{mappingVersion}` | `management/projections/mapping.py:1010` |
| `{releaseId, …}` | `engine/model/release_lifecycle.py:107` |

A separate code for the change set's version and the relation set's version says which of two
claims was stale, which is useful. A separate code for an import profile, a mapping or an AI task
says nothing `VERSION_CONFLICT` would not: users, clients, groups and workspaces all use the plain
code. `frontend/src/api/errors.ts:24-27` states that `isApiError(cause, "VERSION_CONFLICT")` is
the single way the interface recognises a stale write; it is not, and D2 is the result. An API
client has to know all eight codes and read the current version from four places.

Suggested direction: one helper that raises the refusal (see R1), one detail shape, and the extra
codes kept only where they tell two claims in one request apart.

### M2. Three locales format numbers and dates in one interface

- `"en"`: `ui/limits.ts:9` (the shared `count`), `features/objects/SelectionBar.tsx:14`,
  `features/objects/RelationGridChangeDialog.tsx:32`, `features/settings/AiPage.tsx:37`,
  `features/settings/AgentAccessPage.tsx:43`, `lib/duration.ts:7`.
- `"en-GB"`: `features/moves/MoveEditor.tsx:60`, `features/moves/MoveStatus.tsx:14`,
  `features/settings/operationsText.ts:54`, `features/model-admin/MigrationPage.tsx:43`,
  `features/model-admin/ProposedRows.tsx:14`, `features/model-editor/DraftMigration.tsx:15`; dates
  in `features/settings/FollowedWorkspaces.tsx:18`, `features/settings/NoticeMailPanel.tsx:44-47`,
  `features/settings/OperationsPage.tsx:128, 139`.
- The browser's locale: `ui/ScrollWindow.tsx:38`, `features/objects/RecordTree.tsx:74`,
  `ui/SettingsParts.tsx:288-289`, `ui/ChangeSetLoad.tsx:81-82`,
  `features/settings/OperationsPage.tsx:299, 427-436`, `features/settings/MailPage.tsx:919-921,
  979`, `features/model-editor/DryRunPanel.tsx:104, 138-140`,
  `features/model-editor/SourcePane.tsx:134`, and every date through `lib/dates.ts`.
- No grouping at all: `features/objects/ObjectDeleteDialog.tsx:11`,
  `features/settings/AccountPermissions.tsx:202`, `features/model-admin/ModelStructure.tsx:41`.

In a browser set to German, a list's row count reads `12.345` and the selection bar above it
`12,345`; Operations shows a 24-hour British time beside dates in the browser's format. The
interface's words are English throughout, so one fixed locale for numbers, chosen once in
`ui/limits.ts`, would be consistent with them.

### M3. Sign-in sentences are written twice in the backend and matched in the frontend

`backend/app/management/sign_in_pages.py:251, 436` (the engine's own pages) and
`backend/app/management/routers/oauth_app.py:177, 185, 224` (the application's sign-in) each hold
"Too many attempts for this account or from this address. You can try again in …", "Too many wrong
codes …", "The e-mail address or password is not right. Check both and try again." and "That code
is not right, or was already used. …". The frontend then matches on the first of these (D6). One
module of sign-in messages would keep the two sign-in surfaces saying the same thing.

### M4. Two quote styles for names

`frontend/src/ui/changeText.ts:13` writes names as “name”; `frontend/src/features/inbox/inboxText.ts:24`
writes them as ‘name’. The same change set is quoted differently in the activity list and in the
inbox.

### M5. Dialog actions sit in two places in the markup

`frontend/src/ui/ConfirmDialog.tsx:50-68` puts `.dialog-actions` after `.dialog-body`.
`frontend/src/features/moves/MoveEditor.tsx:822-828` and
`frontend/src/features/model-admin/MigrationPage.tsx:761-776` put it inside `.dialog-body`. The
two alert dialogs are hand-built where `ConfirmDialog` with `tone="plain"` and `dismissLabel` would
do (MigrationPage's fits as it is; MoveEditor's needs a second action).

### M6. Default and largest page sizes vary without a visible rule

Across 74 routes the default `pageSize` is 20, 50, 100, 500 or 1000 and the largest 100, 200, 500
or 1000 (see R2): 30 routes take 100 of at most 500, 24 take 50 of at most 500, and the remaining
20 use other pairs. A client cannot assume one limit, and nothing in the code says why a
list has the pair it has.

---

## C. Reuse: backend

The backend already has one paginator, one cursor format, one spreadsheet reader
(`engine/imports/readers.py`), one spreadsheet writer (`engine/jobs/xlsx.py`), one address-checked
HTTP client for webhooks and sign-in providers, and one route declaration for authorization. The
findings below are the places where that discipline was not applied.

### R1. About 30 hand-written version checks, four private `_stale` helpers

`if row.version != expected: raise api_error(409, "VERSION_CONFLICT", "… version has changed",
{"currentVersion": …})` is written out in about 20 modules, among them
`engine/identity/users.py:102`, `engine/identity/clients.py:54`, `engine/identity/links.py:94`,
`engine/events/subscriptions.py:328`, `engine/records/objects.py:239`,
`engine/records/relation_writes.py:51`, `engine/records/writes.py:285, 499`,
`engine/workspaces/catalogue.py:187, 218, 340`, `engine/sources/store.py:288`,
`engine/model/drafts.py:159, 191, 209`.

Four modules each define their own `_stale`: `engine/identity/providers.py:73`,
`engine/authorization/administration.py:65` (these two are identical),
`engine/mail/mail_template.py:82`, `engine/mail/settings.py:110`.

One `require_version(row, expected, what)` in `app/errors.py` or `common/` would remove them and
is what makes M1 fixable in one place.

### R2. `pageSize` is declared by hand on 74 routes

`management/paging.py` gives every route `cursor`, `from`, `position` and `includeTotal` through
`PageQuery`. The page size is not part of it: `page_size: int = Query(default=…, ge=1, le=…,
alias="pageSize")` is repeated 74 times. A `PageSize(default, largest)` dependency beside
`PageQuery` would state each list's limits in one line and make M6 visible.

### R3. `_chunks` four times, `_CHUNK = 500` four times

Identical bodies in `engine/records/context.py:90`, `engine/records/writes.py:94` and
`engine/operations/restructuring.py:737`; a variant with a size argument in
`engine/indexes/matrix_states.py:105`. Each file also defines `_CHUNK = 500`
(`records/context.py:65`, `records/writes.py:91`, `operations/restructuring.py:79`,
`indexes/matrix_states.py:91`). Python 3.12 added `itertools.batched`, which is this function.

### R4. `_is_containment` three times in model authoring

`engine/model/authoring/layout.py:461`, `engine/model/authoring/kinds.py:847` and
`engine/model/authoring/outline.py:682` each test `relation.features.parentOf`, with three
different signatures. One function on the relation definition would serve all three.

### R5. `_omitted` twice in the schemas

`management/schemas/changes.py:12` and `management/schemas/records.py:285` are the same field
factory. `management/schemas/common.py` is where the two things it uses already live.

### R6. Dotted version parsing twice

`engine/model/raising.py:44` and `engine/sources/inference/compare.py:265` both turn `"0.8"` into
a tuple of integers, differing only in what they return for text that is not a version.

### R7. The AI requester is built inline beside its helper

`management/routers/ai.py:283` defines `_requester(principal)`. `test_ai_provider` (lines 96-99)
and `post_query_translation` (lines 183-186) in the same file build the same value by hand.

### R8. Job kinds are dispatched by an `if` chain the worker owns

`engine/jobs/worker.py:377-399` chooses what a job does with eleven `if job.kind ==` branches, and
further branches at lines 333-341, 525, 554, 587, 621, 631, 820, 957, 978 and 990. The same kinds
are listed again in `EXPORT_KINDS`, `ASSISTANT_KINDS` (`worker.py:158-160`), `PREVIEWED_KINDS`,
`ROW_KINDS` (`store.py:309-312`) and `JOB_GROUPS` (`authorization/catalogue.py`). The model
authoring code and the mapping code already use a registry of kinds
(`engine/model/authoring/kinds.py:270`, `engine/moves/mapping_kinds.py:79`). The same shape for
job kinds (one entry per kind: its step, its group, whether it previews, whether it has rows) would
put a new kind in one place. This is the largest of the reuse items and is a design suggestion, not
a defect: today's lists agree with each other and with the frontend.

---

## D. Reuse: frontend

The frontend reuses its base well: 59 components use `ui/Modal`, in-place editing is built on
`ui/EditInPlace`, all requests go through `api/client.ts` and `authorizedFetch`, and there is no
`any`, `@ts-ignore` or `dangerouslySetInnerHTML` in the source. The findings below are the
repeated layers on top of that base.

### F1. The text-in-place controller exists three times

`frontend/src/ui/TextInPlace.tsx:44-145`, `frontend/src/features/model-editor/EditableText.tsx:51-132`
and `frontend/src/features/model-editor/EditableCell.tsx` each hold the same state and steps:
`editing`, `saving`, `error`, the `wasEditing` effect that returns focus, reading and trimming the
form value, closing when unchanged, "… needs a value.", save, show the refusal. They differ in the
notice's title ("Not saved" against "The name was not saved"), in whether a toast with Undo
follows, and in the field's control.

The focus-return effect alone is copied in five files (the three above,
`features/objects/relations/RelationValueCell.tsx` and `features/objects/EditableField.tsx`).

Suggested fix: a `useInPlaceEdit` hook in `ui/EditInPlace.tsx` that owns the state, the focus
return and the submit steps; the three components keep only their control and their words.
`TextInPlace` was added for the settings pages; `EditableText` is the same component with the model
editor's refusal text, and could be `TextInPlace` given a `refusal` function.

### F2. Pluralising is written twelve times

`features/settings/AccountPermissions.tsx:202`, `features/model-admin/ModelStructure.tsx:41`,
`features/ai-tasks/aiTaskText.ts:48`, `features/jobs/MoveOutcome.tsx:32`, `ui/BatchOutcome.tsx:29`,
`features/model-admin/MigrationPage.tsx:45`, `features/home/homeText.ts:16`,
`features/moves/StartMoveDialog.tsx:15`, `features/objects/RestructuringDialog.tsx:570`,
`features/moves/MoveStatus.tsx:15`, `features/objects/ObjectDeleteDialog.tsx:11`,
`features/objects/bulkDelete.ts:27`.

Most are `(n, one, many) => `${count(n)} ${n === 1 ? one : many}``; they are named `plural`,
`counted`, `count` and `records`, and three of them leave the number unformatted (M2). One
`counted(n, one, many?)` beside `count` in `ui/limits.ts` replaces all of them.

### F3. The number formatter is copied ten times

`ui/limits.ts:9` exports `count`. Local copies: `features/moves/MoveEditor.tsx:60`,
`features/moves/MoveStatus.tsx:14`, `features/settings/AgentAccessPage.tsx:43`,
`features/settings/operationsText.ts:54`, `features/settings/AiPage.tsx:37`,
`features/model-admin/MigrationPage.tsx:43`, `features/model-admin/ProposedRows.tsx:14`,
`features/model-editor/DraftMigration.tsx:15`, `features/objects/RelationGridChangeDialog.tsx:32`,
`features/objects/SelectionBar.tsx:14`. This is where M2's two fixed locales come from.

### F4. "All workspaces" is read four ways

`lib/everyPage` (four callers), a hand-written copy of `everyPage`
(`features/model-editor/ApplyDialog.tsx:91-99`), one page of 100 (three callers) and one page of
500 (two callers); see D4. One `allWorkspaces(options)` in the API client, built on `everyPage`,
serves every case.

### F5. Names of model elements are looked up by local helpers

`typeName`, `attributeName` and `relationName` over an `EngineModel` are defined in
`ui/MoveRowsTable.tsx:22-25`, `features/moves/MoveReport.tsx:15-18`,
`features/moves/mappingRows.ts:59-65` and `features/objects/useCellEditing.tsx:201`, while
`model/fields.ts:27` exports `attributeName` and `model/lookup.ts` holds the type lookups. The
draft outline has its own set (`model/outline.ts:92`), repeated in
`features/model-editor/elementSettings.tsx:18`, `features/model-editor/mapping.ts:146` and
`features/model-editor/RelationshipMatrix.tsx:215`.

### F6. `timeOfDay` three times

`ui/Timeline.tsx:149`, `features/workspaces/WorkspaceActivity.tsx:37` (identical), and inline at
`features/workspaces/WorkspacePage.tsx:693`. It belongs in `lib/dates.ts`, which already formats
the same time inside `formatServerDayTime`.

### F7. Value coercion helpers are redeclared per file

`list`, `text`, `str` and `record` (an unknown value as an array, a string, an object) are declared
in `features/model-editor/viewKinds.ts:23-24`, `relationTableView.ts:14`, `layout.ts:246-247`,
`consumer.ts:15-18`, `matrixView.ts:16`, `history.ts:31`, `mapping.ts:517`,
`features/ai-tasks/aiTaskDesign.ts:9-10`, `features/security/securityText.ts:249`,
`features/model-admin/structureParse.ts:55` and `features/jobs/JobProduced.tsx:26`. Some trim, some
treat an empty string as absent, so the copies are not interchangeable by accident.

### F8. `json(method, body)` in three API clients

`api/mailClient.ts:6`, `api/securityClient.ts:60`, `api/mailTemplateClient.ts:6`.

### F9. `ancestorsOf` twice in the model editor

`features/model-editor/candidates.ts:47` and `features/model-editor/matrixView.ts:19` walk a type's
parents; the second leaves the type itself out when it meets it again, the first does not.

### F10. A second `Switch`

`ui/Switch.tsx` is the shared one. `features/workbook-canvas/CanvasInspector.tsx:32` defines its
own with its own class (`canvas-switch`).

### F11. Browser storage bypasses `lib/localPreference`

`features/objects/RecordTree.tsx:327, 409, 1444` and
`features/ai-tasks/AiTaskJourneyBar.tsx:31, 39` repeat the try/catch around `localStorage` that
`readLocalPreference` and `writeLocalPreference` already provide.

### F12. Undo toasts are assembled in eleven places

`label: "Undo"` appears in eleven call sites, each building the same toast with its own refusal
sentence (`features/objects/undoText.ts:2` for records,
`features/objects/relations/RelationValueField.tsx:45` for relationships,
`ui/TextInPlace.tsx:83-84` for settings). A `toastWithUndo(text, undo, refused)` on the toast hook
would hold the shape once.

### F13. Stylesheets

- 49 classes are defined and never named in the source, 22 of them in `styles/settings.css` (for
  example `account-digest`, `account-kinds`, `account-kind-row`, `capability-groups`) and 16 in
  `styles/components.css` (for example `confirm-dialog`, `compact-dialog`, `model-catalogue`,
  `detail-header`).
- 31 classes are styled in four or more stylesheets; `.inline-attribute-editor` and `.dialog` in
  seven each, `.page-header`, `.form-field`, `.search-box` and `.secondary` in six. A change to one
  of these has to be checked in every file that restyles it.
  Counted again the same day: 18 of the 31 are named only inside another selector (a page, a frame, a
  state) and most of the other 13 repeat inside media rules. Those are intended differences, not copies;
  only a bare selector repeated outside a media rule is a copy.

---

## E. Checked and found aligned

- **Routes.** The backend declares 331 routes. Every API path the frontend builds has a route. The
  routes no frontend code calls are metadata reads (`/applications`, `/object-types`,
  `/attribute-types`, `/relation-types`, `/object-type-relations`, `/workspace-models`), the
  workspace feed and the object query, which are for API clients.
- **Error codes.** Each of the 85 codes the frontend names is raised by the backend, apart from the
  two the client makes itself (`UNEXPECTED_RESPONSE`, `BATCH_REFUSED`).
- **Action groups.** The ten groups the frontend checks are all in the backend catalogue.
- **Job kinds.** Twelve in the backend, the same twelve in `frontend/src/ui/jobText.ts`.
- **Authorization declarations.** Every management route that takes an identifier resolves its
  workspace from that identifier, or is an instance-level resource with an instance or
  held-anywhere check. No route was found whose check names one workspace while its handler loads
  from another.
- **Identity.** Password rules and storage, the sign-in slowdown, code redemption with PKCE, reset
  links, token verification and session checks read as intended; nothing to report.
- **Outbound requests.** Webhooks and sign-in providers connect only to addresses checked after
  resolution; redirects are not followed.
- **Hygiene.** No `TODO`/`FIXME`, no string-built SQL from request input, no mutable default
  arguments in the backend; no `any`, `@ts-ignore` or `dangerouslySetInnerHTML` in the frontend.

## F. Not covered

These were not traced, so the absence of findings there means nothing:

- Backend: `engine/imports/binding.py`, `engine/model/migrations.py`,
  `engine/operations/restructuring.py`, `engine/jobs/people.py`, `engine/jobs/batches.py`,
  `engine/change_sets/publish.py`, `engine/records/deletion.py`, `engine/sources/inference/`,
  `engine/tasks/` (the assistant's session and sandbox), `consumer/router.py` and the consumer
  reads, the event deriver and dispatcher loops, the Alembic migrations.
- Frontend: the logic of `ui/ScrollWindow.tsx`, `lib/hooks/useCursorWindow.ts`,
  `app/useRouter.ts`, `features/workbook-canvas/`, `features/objects/RecordTree.tsx`,
  `features/model-editor/operations.ts`; visual layout at any width; accessibility.
- Tests on both sides, and whether the findings above are covered by one.
- Behaviour under load or with several processes.
