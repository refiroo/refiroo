## Error codes

Every refusal carries a `code`. Each entry says what the code means, why it usually happens and what the client does. A refused request changes nothing unless an entry says otherwise.

### ACTION_GROUP_UNKNOWN

<span class="rdm-status rdm-4xx">Status 422</span>

The request names an action group the engine does not have. `details.actionGroups` lists the unknown keys. It usually comes from a misspelt group key, such as `holding=publishing` where the key is `publish`. Send one of the keys `GET /api/v1/action-groups` lists.

### ACTIVATION_CONFLICT

<span class="rdm-status rdm-4xx">Status 409</span>

The workspace's model changed since the client read its `version`, so the activation or migration it asked for was refused. `details` holds `workspaceKey`, `currentReleaseId` and `currentVersion`. It usually means another administrator activated or migrated a release in the meantime. Read the workspace's model assignment again and send the request with the current version if it is still wanted. It is answered by `POST /api/v1/workspaces/{workspace_key}/model/activation` and `POST /api/v1/workspaces/{workspace_key}/model/migrations`.

### AGENT_APPLICATION_INVALID

<span class="rdm-status rdm-4xx">Status 422</span>

An administrator tried to register an assistant with details the engine does not accept, in `POST /api/v1/agent-access/applications`. The message says which: `redirectUris` must be a non-empty list of at most 10 addresses of at most 2000 characters, each either a loopback address or an `https` address without a fragment. Correct the addresses and send the request again.

### AGENT_APPLICATION_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No assistant has the ID in the path of `POST /api/v1/agent-access/applications/{application_id}/block` or `.../restore`. It usually comes from an ID copied from another instance or a mistyped one. Use the ID the registration answered with.

### AI_NOT_CONFIGURED

<span class="rdm-status rdm-4xx">Status 409</span>

The request needs an AI feature the operator has not set up on this instance: no AI provider for provider calls such as `POST /api/v1/ai/test`, query translation, history accounts, impact summaries and mapping proposals, or no assistant command for the assistant tasks under `/api/v1/ai/tasks`. Nothing was sent and nothing changed. The client does not retry; an administrator sets the feature up.

### AI_SEND_LEVEL_TOO_LOW

<span class="rdm-status rdm-4xx">Status 409</span>

The send level that applies to the request does not allow what the feature needs to send to the AI provider or assistant. Either the `sendLevel` the request chose is above the instance's ceiling, or the level in force (the request's or the ceiling) is lower than the feature needs. `details` holds `sendLevel` and `ceiling`, and `needs` when the feature's requirement is the cause. Send a `sendLevel` at or below the ceiling; if the ceiling itself is too low for the feature, an administrator raises it.

### AI_TASK_CHECK_STALE

<span class="rdm-status rdm-4xx">Status 409</span>

The client asked to load an assistant task's design, but the draft model changed after the design was last checked. A load only goes ahead with the draft exactly as it was checked. Check the design again, read the task with `GET /api/v1/ai/tasks/{task_id}`, and then send `POST /api/v1/ai/tasks/{task_id}/run` with its new `version`.

### AI_TASK_DRAFT_HELD

<span class="rdm-status rdm-4xx">Status 409</span>

An assistant's own session tried to write a model draft that another assistant task holds. The draft may be under review and is deleted when that task ends. `details.draftId` names the draft. The session makes a new draft, starting from the same release if it should start the same.

### AI_TASK_NEEDS_WORDS

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/ai/tasks` came without a workbook or CSV file and without `words`. With no file the words are the instruction the assistant works from. Send a file, or say in a few words what the assistant should do.

### AI_TASK_NOTHING_TO_LOAD

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/ai/tasks/{task_id}/run` asked to load a task that has no design with a plan to load: the task is a kind that holds nothing to load, or its design has no loadable plan yet. Read the task with `GET /api/v1/ai/tasks/{task_id}` and load only a task that has been checked and holds a plan.

### AI_TASK_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No assistant task has the ID in the path, or the caller may not see it; the engine answers the same for both. Tasks are also removed when their retention ends. List the caller's tasks with `GET /api/v1/ai/tasks` and use an ID from there.

### AI_TASK_STATE

<span class="rdm-status rdm-4xx">Status 409</span>

The task is not in a state that allows the request, or something the request needs is no longer kept. For an operation on an assistant task, `details.state` holds the task's state and the message names the states allowed, for example a task must be `checked` to be loaded. In `GET /api/v1/ai/tasks/{task_id}/changes` it means the task has no check yet, or the check's dry run or working copy is no longer kept. A dry run of items at `POST /api/v1/model-drafts/{draft_id}/dry-run` answers it while an accepted task is loading the draft's checked items. Read the task, wait for it to reach the state the message names, or start a new task.

### AI_TASK_TABLE_UNKNOWN

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/ai/tasks/{task_id}/changes` named a `source` the latest check has no figures for, or no `source` at all. `details.source` holds the value sent and the message lists the sources the check has. Send one of those source numbers.

### AMBIGUOUS_MATCH

<span class="rdm-status rdm-4xx">Status 409</span>

A consumer API cross-reference read with `expect=one` found several objects that share the top match score, so the query does not identify one. `details.count` is the number sharing it and `details.candidates` lists some of them with `id`, `objectType`, `name` and `matchScore`. Make the query more specific, or choose among the candidates. In `POST /api/consumer/{consumer_api}/v{contract_version}/resolve` the answer is the `error` of that item, not the status of the request.

### AMBIGUOUS_NAME_KEY

<span class="rdm-status rdm-4xx">Not a response status</span>

A row error of an import, never a response status. It is the `error` of a row in `GET /api/v1/jobs/{job_id}/rows` and of its items, and the row is not loaded. A record is found by its name and several records have it (under the row's parent, when the row has one); `details` holds `column` and `count`. Key the source by an attribute that is unique, or correct the names.

### AMBIGUOUS_TARGET

<span class="rdm-status rdm-4xx">Status 409</span>

The read of one object through a consumer API named a crosswalk target that matches several items of the object, so the target does not identify one. `details` holds `id`, `objectType`, `parameter`, `path`, `count` and `targets` (some of the matching items). Give a target value that matches one item. A get by ID, a cross-reference read with `expect=one` and an item of a batch resolve can all answer it; in a batch resolve it is the `error` of that item.

### APPLICATION_IN_USE

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding about stored records, never a response status. The candidate release removes an application that stored records still stand in. It appears as an error in the `diagnostics` of a compatibility check (with `count`, the records affected), in the `details` of `MODEL_MIGRATION_REQUIRED`, and as the code of a `loss` item of a migration, where the records' type is in no application of the target release. Keep the application in the release, or migrate the workspace so the records move into an application the target has.

### APPLICATION_OBJECT_TYPE_IN_USE

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding about stored records, never a response status. The candidate release keeps an application but no longer lists an object type in it, and stored records of that type stand in the application. It appears as an error in the `diagnostics` of a compatibility check (with `count`), in the `details` of `MODEL_MIGRATION_REQUIRED`, and as the code of a `loss` item of a migration, where no application of the target release lists the type. List the type in the application again, or migrate the workspace so the records move to an application that lists it.

### APPLICATION_TARGET_AMBIGUOUS

<span class="rdm-status rdm-4xx">Not a response status</span>

A migration's item code, never a response status. The records of a type go to an application the target release does not settle: the type now stands in several applications of its own and none can be told from the others. The preview refuses the records (`outcome` `refused`) and `POST /api/v1/workspaces/{workspace_key}/model/migrations` is refused with `MIGRATION_HAS_REFUSALS`. Name the application in the type mapping's `toApplicationKey` and preview again.

### APPROVAL_POLICY_INVALID

<span class="rdm-status rdm-4xx">Status 422</span>

`PUT /api/v1/workspaces/{workspace_key}/approval-policy` set `secondPerson` without `requireApproval`. A second person can only be required when approval is required; `details.field` is `secondPerson`. Send `requireApproval: true` with it, or leave `secondPerson` off.

### APPROVAL_REQUIRED

<span class="rdm-status rdm-4xx">Status 409</span>

The workspace's approval policy forbids this caller from publishing a change set directly, so nothing was published. `details` holds `workspaceKey` and `secondPerson`. This happens when approval is required and the caller either does not hold the approval role or the policy demands approval by another person. Submit the change set with `POST /api/v1/change-sets/{change_set_id}/submission` and let an approver decide it with `POST /api/v1/change-sets/{change_set_id}/decisions`.

### AS_OF_NOT_SUPPORTED

<span class="rdm-status rdm-4xx">Status 422</span>

The request sent `asOf`, but the read cannot be dated. `asOf` works only for object types that declare an effective period; a date field is never taken for one. The management API answers 422: on the lists that span several types the message names the per-type and query routes to use, and `details.objectTypeKey`, `details.objectTypeKeys` or `details.route` say what to use instead. The consumer API answers 400 with `details.objectTypes` and `details.path`. In `POST /api/v1/exports` it is refused when no exported type declares a period. Leave `asOf` out, or read types that declare a period.

### ATTRIBUTE_ABOVE_MAXIMUM

<span class="rdm-status rdm-4xx">Status 422</span>

An integer or decimal attribute value is above the maximum its attribute type allows. The message names the attribute and the maximum. Send a value within the limit. In a batch the refusal appears in the rejected item of `GET /api/v1/jobs/{job_id}/items`, pointing at `attributes`, rather than as the status of the request.

### ATTRIBUTE_ALREADY_EXISTS

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}` creates an attribute value the record already has, live or in the change set named by `changeSetId`. Change the existing value with `PATCH` on the same path, or delete it first.

### ATTRIBUTE_BELOW_MINIMUM

<span class="rdm-status rdm-4xx">Status 422</span>

An integer or decimal attribute value is below the minimum its attribute type allows. The message names the attribute and the minimum. Send a value within the limit. In a batch the refusal appears in the rejected item of `GET /api/v1/jobs/{job_id}/items`, pointing at `attributes`, rather than as the status of the request.

### ATTRIBUTE_BINDING_IN_USE

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the stored values), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release no longer binds an attribute type to an object type whose records hold values for it. Keep the binding, or migrate the workspace; a migration lists those values as a `loss`, with this code, when the target type has no attribute to carry them.

### ATTRIBUTE_FILLED_TWICE

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem of a model mapping, never a response status. It is an entry of the mapping's `problems`, at its `pointer` on the `source` or `target` side; an operation that would cause it is refused when applied. Two source attributes are mapped onto one target attribute. Map one of them elsewhere.

### ATTRIBUTE_NOT_BOUND

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. The profile fills an attribute the object type does not bind, or a relationship attribute its binding does not carry. `path` points at the `attributeTypeKey`. Bind the attribute to the type in the model, or name one the type has.

### ATTRIBUTE_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The record has no value for the attribute the request names, so there is nothing to read, change or delete. It is answered by `GET`, `PATCH` and `DELETE` on `/api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}`, live or in a change set. A value that does not exist yet is created with `POST` on that path.

### ATTRIBUTE_NOT_MAPPED

<span class="rdm-status rdm-4xx">Not a response status</span>

A reason of a move, never a response status. The mapping names no target attribute for a source attribute, so its value is not carried. It is an entry of `leftBehind` of a row of the move's dry run, with the source attribute's `pointer`; map the attribute or ignore it on purpose.

### ATTRIBUTE_READ_ONLY

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. A column fills an attribute the type declares read-only, which no import can write. Leave the column out or ignore it.

### ATTRIBUTE_TYPE_IN_USE

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the stored values), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release removes an attribute type that stored records still hold values for. Keep the attribute type, or migrate the workspace so the values move to another attribute or are given up.

### ATTRIBUTE_UNIQUENESS_VIOLATED

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the groups of duplicate values), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release makes an attribute unique, or changes what it is unique within, and stored values already repeat. Correct the duplicates, or leave the attribute not unique.

### ATTRIBUTE_VALIDATION_VIOLATED

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the stored values outside the limit, on records and on relationships), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release sets or changes the `minimum` or `maximum` of an integer or decimal attribute type and stored values lie beyond it; `path` ends in `/validation/minimum` or `/validation/maximum`. Correct the values, or keep the limit.

### ATTRIBUTE_VALUE_TYPE_CHANGED

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the stored values), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release changes an attribute type's value type while stored records hold values of it. Keep the value type, or migrate the workspace so the values are converted; a value that does not convert is lost (`VALUE_NOT_CONVERTIBLE`).

### AUTHENTICATION_REQUIRED

<span class="rdm-status rdm-4xx">Status 401</span>

The request has no `Authorization` header, and the answer carries `WWW-Authenticate: Bearer`. It usually means the client forgot to send its token, or a proxy removed the header. Obtain an access token and send it as `Authorization: Bearer <token>`.

### BATCH_ROLLED_BACK

<span class="rdm-status rdm-4xx">Not a response status</span>

The reason of an item that did not run: an `atomic` job refused one item, so every applied item was rolled back and the others were left `unprocessed`. It appears as `reason` in the job's items (`GET /api/v1/jobs/{jobId}/items`) and the inline response of `POST /api/v1/batches`. Correct the rejected item, which carries the cause, and send the batch again, or send it as `independent` if partial progress is acceptable.

### BATCH_TOO_LARGE

<span class="rdm-status rdm-4xx">Status 413</span>

The request holds more items, or more bytes, than the operation accepts in one call, and nothing was done. `details.setting` names the operator setting that sets the limit and `details.maximum` its value, with `details.items` or `details.bytes` the size found. It is answered by `POST /api/v1/batches`, `POST /api/v1/relations/batch`, `POST /api/v1/relations/grid-change` (the number of relationships the change would write), the dry run of `POST /api/v1/model-drafts/{draft_id}/dry-run` with items, and `POST /api/consumer/{consumer_api}/v{contract_version}/resolve`, which also refuses a body over 16 KiB for each item `CONSUMER_RESOLVE_MAX_ITEMS` allows (`details.maximumBytes`). Split the work into smaller requests.

### BINDING_NOT_ALLOWED

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem of a model mapping, never a response status. It is an entry of the mapping's `problems`, at its `pointer` on the `source` or `target` side; an operation that would cause it is refused when applied. The element is declared but not usable there: an attribute not bound to the mapped type, a relationship not allowed at that end, a parent relation that does not contain the type, or a match attribute that is not unique. Choose one the release allows.

### CANNOT_DELETE_REQUIRED_ATTRIBUTE

<span class="rdm-status rdm-4xx">Status 422</span>

`DELETE /api/v1/objects/{object_type_key}/{object_id}/attributes/{attribute_type_key}` names an attribute that the record's type marks as required. A required attribute always has a value. Change the value with `PATCH` instead of deleting it.

### CARDINALITY_VIOLATION

<span class="rdm-status rdm-4xx">Status 409</span>

The relationship would give a record a second relationship that its relation type allows only once. `details` holds `relationTypeKey`, `cardinality` and `end` (`from` or `to`), the end whose record already holds one. Remove or change the existing relationship in the same set of changes, or relate other records. In a batch the refusal appears in the item.

### CHANGE_SET_BASE_INVALID

<span class="rdm-status rdm-4xx">Status 409</span>

The change set has no usable base to read against: its base is missing or belongs to another workspace, or it has none at all. The message says which; the last case asks for the change set to be recreated from live data. It means the change set's stored base cannot be used, so retrying does not help; start a new change set with `POST /api/v1/workspaces/{workspace_key}/change-sets`.

### CHANGE_SET_CONFLICT

<span class="rdm-status rdm-4xx">Not a response status</span>

A migration's item code, never a response status. A record or relationship of a change set that is moved onto another release, or published with a migration, changed both in the change set and in live data since the change set's base, so the change set's change cannot be applied as it stands. It is a `refused` item naming the record or relationship; the job cannot be confirmed. Settle the difference in the change set or in live data, then preview again. A publication's own conflict of the same kind is `VERSION_MISMATCH`.

### CHANGE_SET_CONTENT_INCOMPATIBLE

<span class="rdm-status rdm-4xx">Status 409</span>

The change set holds content that does not fit the model release the request would give it, so the pin was not changed. `details` holds `diagnostics` (at most 20), `diagnosticCount` and `diagnosticsTruncated`. It is answered by `PATCH /api/v1/change-sets/{change_set_id}/model-release` and by starting a change set on a chosen release. Keep the change set's current release, choose a compatible release, or move the data with a model migration.

### CHANGE_SET_INVALID

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/change-sets/{change_set_id}/submission` refused the submission because the change set does not validate. `details` holds `count` and `diagnostics`, the first of them. Fix the problems the diagnostics name, validate with `POST /api/v1/change-sets/{change_set_id}/validation`, and submit again.

### CHANGE_SET_MODEL_RELEASE_CONFLICT

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/change-sets/{change_set_id}/publication` was refused because the change set is pinned to a model release that the workspace no longer runs. `details.workspaceKey` names the workspace. It usually follows a model activation or migration after the change set was started. Move the change set to the workspace's current release with `PATCH /api/v1/change-sets/{change_set_id}/model-release` if its content fits, or start a new change set.

### CHANGE_SET_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No change set has the ID the request names. It usually comes from a mistyped ID or a change set that was published or deleted. List change sets with `GET /api/v1/workspaces/{workspace_key}/change-sets` and use an ID from there.

### CHANGE_SET_REQUIRED

<span class="rdm-status rdm-4xx">Status 409</span>

The request targets a change set with `changeSetId` but does not send `expectedChangeSetVersion`. The version is how the engine detects that the change set moved on. Read the change set with `GET /api/v1/change-sets/{change_set_id}` and send its `version` as `expectedChangeSetVersion`.

### CHANGE_SET_SNAPSHOT_RETRY

<span class="rdm-status rdm-4xx">Status 409</span>

Starting a change set from live data failed because live data or the workspace's active model changed while the engine was copying it. Nothing was saved. It happens when a write or a model activation lands at the same moment. Send `POST /api/v1/workspaces/{workspace_key}/change-sets` again; if the model changed, the new change set starts on the model now active.

### CHANGE_SET_SUBMITTED

<span class="rdm-status rdm-4xx">Status 409</span>

The change set is submitted for publication, so it cannot be submitted again or changed. A write to a submitted change set is refused unless the request says to withdraw the submission; `details` then holds `submissionId` and `withdraw` (`withdrawSubmission=true`). Withdraw the submission with `DELETE /api/v1/change-sets/{change_set_id}/submission`, or repeat the write with `withdrawSubmission=true`, which withdraws it first.

### CHANGE_SET_VERSION_CONFLICT

<span class="rdm-status rdm-4xx">Status 409</span>

The `expectedChangeSetVersion` sent is not the change set's current version, so someone else changed the change set after the client read it. Nothing was written. Every write into a change set claims its version, and so do restructurings, `PATCH /api/v1/change-sets/{change_set_id}/model-release` and a migration that names a change set. Read the change set again, check what changed, and send the request with its current `version` if it is still wanted.

### CLIENT_HAS_NO_SECRETS

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/clients/{client_id}/secrets` named a client that belongs to an assistant task. Such a client signs in without a secret and cannot hold one. Add secrets only to clients created with `POST /api/v1/clients`.

### CLIENT_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No client has the ID the request names, in the client routes under `/api/v1/clients/{client_id}` or as the principal of a grant in `POST /api/v1/grants`. It usually comes from a mistyped ID or a deleted client. List clients with `GET /api/v1/clients` and use an ID from there.

### CLIENT_SECRET_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The client has no secret with the ID in `DELETE /api/v1/clients/{client_id}/secrets/{secret_id}`. The secret may already have been removed. Read the client with `GET /api/v1/clients/{client_id}` to see its secrets.

### CODE_INCORRECT

<span class="rdm-status rdm-4xx">Status 422</span>

A code or password sent as proof is wrong, or the one-time code was already used. It is answered by `POST /api/v1/me/second-factor/confirmation`, `POST /api/v1/me/second-factor/recovery-codes`, `DELETE /api/v1/me/second-factor` and `DELETE /api/v1/me/passkeys/{passkey_id}`. Wrong proofs are counted; after too many the engine answers `SIGN_IN_SLOWED` instead. Send the current code from the authenticator app, a recovery code that is still unused, or the password where the operation takes it.

### COLUMN_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 422</span>

A column is not in the table that was named. As the response of `POST /api/v1/model-drafts/{draftId}/join-candidates`, a header or sheet letter is not in the header row or block of the sheet it was sent with; `details.path` is `/column` or `/against`. It is also a problem in an import's file, listed in `details.problems` of `IMPORT_FILE_MISMATCH`, or an item's refusal for an export's table layout: a column the profile names, by header or by letter, is not in the file's header row, or a sheet of an export's tables has records but no `applicationKey` column; `path` points at the profile part that names it. Restore the column in the file or correct what names it.

### COLUMN_UNMAPPED

<span class="rdm-status rdm-4xx">Not a response status</span>

A warning of a model draft's import profile, never a response status. It is an entry of the profile's warnings in a draft step's answer and does not block the step. A column the profile named is no longer mapped because a step took away what it named; `because.kind` says which. Map the column again or leave it.

### COMMENT_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/change-sets/{change_set_id}/decisions` sent the change set back without a comment. `details.field` is `comment`. Send a comment that says what the submitter should change.

### CONFLICTING_COLUMN_PARAMETERS

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/workspaces/{workspace_key}/relation-matrix` named its columns with `columnIds` and also paged them with `columnCursor`. `details.parameters` lists the two. Send `columnIds` to name the columns, or `columnCursor` to page through them, not both.

### CONFLICTING_PAGE_PARAMETERS

<span class="rdm-status rdm-4xx">Status 422</span>

A collection read named more than one way to select a page. A page is selected by at most one of `cursor`, `position` or `from=end`; `details.parameters` lists the ones the request sent. Send one of them, or none to read the first page.

### CONSUMER_API_CLIENTS_ONLY

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/grants` granted a consumer API to a user or a group. Consumer APIs are read by clients; people read through the management API, and a group's members are people. `details.principalKind` holds the kind sent. Grant the consumer API to a client.

### CONSUMER_API_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404 or 400</span>

The consumer API key does not exist in the model the request reads. The consumer API (`/api/consumer/{consumer_api}/...`) and the model routes `GET /api/v1/model/consumer-apis/{consumerApi}` and `/api/v1/model-drafts/{draft_id}/consumer-apis/{consumer_api}` answer 404; the latter two put the key in `details.consumerApi`. Creating or editing a consumer subscription answers 400 with `details.pointer` `/consumerApi`. Use a key the model declares.

A consumer token reading `/api/consumer/{consumer_api}/...` for a key the requested workspace's model does not declare also gets this 404, whatever its grants. `details.workspaces` lists, sorted, the active workspaces where this client holds a grant of that consumer API (empty when it holds none), and the message then names one to add as `?workspace=`. A key the workspace's model declares, read without a grant, stays `403 FORBIDDEN`.

### CONSUMER_API_REMOVED

<span class="rdm-status rdm-4xx">Not a response status</span>

A warning in the `diagnostics` of a model compatibility check, never a response status. The candidate model release or draft no longer declares a consumer API the active release has, so its consumers would receive 404 from `/api/consumer/{key}`. It does not block activation. Keep the consumer API in the model, or tell its consumers before activating.

### CONSUMER_CONTRACT_VERSION_DECREASED

<span class="rdm-status rdm-4xx">Not a response status</span>

An error in the `diagnostics` of a model compatibility check: the candidate model lowers a consumer API's `contractVersion` below the active release's. It is shown in the `consumerContracts` part of release and draft reads, and in `details` of `409 CONSUMER_CONTRACT_VERSION_REQUIRED` when activation or a migration is refused for it. Keep the `contractVersion` at or above the active one.

### CONSUMER_CONTRACT_VERSION_REQUIRED

<span class="rdm-status rdm-4xx">Status 409</span>

The model release being activated, or the target of a migration, changes what a consumer API's consumers read without raising its `contractVersion`. `details` lists the diagnostics, each naming the consumer API and the change. It is answered by `POST /api/v1/workspaces/{workspace_key}/model/activation` and `POST /api/v1/workspaces/{workspace_key}/model/migrations`. Raise the `contractVersion` of the consumer API in a new release and activate that release, or send `keepContractVersions: true` to keep the current version under its number: its consumers then read the new shape, and the answer and the release's activations record what was kept. The flag never covers a lowered `contractVersion` or a change to an earlier version served beside the current one; those stay refused.

### CONSUMER_KEPT_VERSION_CHANGED

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `consumerContracts` of a release or draft read: an earlier contract version of a consumer API that is kept would read differently from before, and a kept version is served as it was. Restore it, or stop serving it.

### CONSUMER_VERSION_STOPPED

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is a warning in the `consumerContracts` of a release or draft read: the candidate stops serving an earlier contract version of a consumer API, so its consumers will receive `404 CONTRACT_VERSION_NOT_FOUND` for it. Keep the version if consumers still read it.

### CONTAINMENT_CYCLE

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a change set's whole-graph check, never a response status. It is an error in the `diagnostics` of `POST /api/v1/change-sets/{change_set_id}/validation`, in the `details` of `CHANGE_SET_INVALID` when submitting is refused, and in the diagnostics that refuse a publication or a migration of the change set. A record's chain of parents leads back to itself, or to a parent that is not in the change set's graph. Correct the parent of the records concerned.

### CONTAINMENT_RELATION_MISSING

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a change set's whole-graph check, never a response status. It is an error in the `diagnostics` of `POST /api/v1/change-sets/{change_set_id}/validation`, in the `details` of `CHANGE_SET_INVALID` when submitting is refused, and in the diagnostics that refuse a publication or a migration of the change set. A record's parent is not joined to it by the parent relation its type declares; `details` holds `objectId` and `parentObjectId`. Relate them with the declared parent relation, or give the record another parent.

### CONTRACT_VERSION_CHANGED

<span class="rdm-status rdm-4xx">Not a response status</span>

The reason of a suspended subscription, never a response status. It is `suspension.reason` of a subscription, with `details` that depend on it. The model now serves a higher contract version of the consumer API than the subscription accepted (`details.contractVersion`, `details.servedContractVersion`). Resuming accepts the served version; check the receiver reads it first.

### CONTRACT_VERSION_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404 or 400</span>

The consumer API does not serve the contract version the request names. `details.servedContractVersions` lists the versions it serves and `details.contractVersion` the current one. The consumer API paths `/api/consumer/{consumer_api}/v{contract_version}/...` answer 404. Creating or editing a consumer subscription answers 400 with `details.pointer` `/contractVersion`. Use one of the served versions.

### COUNTERPARTS_ACROSS_MODELS

<span class="rdm-status rdm-4xx">Not a response status</span>

A batch or import that loads other workspaces' record IDs as counterparts (`otherWorkspaceIds: counterparts`) names a record of a workspace that runs a different model, and records cannot be loaded as counterparts across models. It appears as the code of the rejected item in `GET /api/v1/jobs/{job_id}/items`, and as a notice in the job's preview that counts the rows concerned; it is not a response status of the request that started the job. `details` holds `workspaceKey`, `modelKey` and `workspaceModelKey`. Move data between workspaces with different models through a move between the two models.

### CREATE_NEEDS_NAME_MATCH

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. A binding says `missing: create` but matches by something other than the name, so a cell that names no record has no name to create one with. Match by `name`, or leave `missing` at `refuse`.

### DATABASE_COLLATION

<span class="rdm-status rdm-4xx">Not a response status</span>

A failure of a backup rehearsal, never a response status. It is the `failure.code` of a rehearsal in `GET /api/v1/system/backup-rehearsals`. The copy's database does not use the ICU root collation `und` the engine requires. Create it with that collation and restore into it.

### DATABASE_EXTENSIONS

<span class="rdm-status rdm-4xx">Not a response status</span>

A failure of a backup rehearsal, never a response status. It is the `failure.code` of a rehearsal in `GET /api/v1/system/backup-rehearsals`. The copy lacks an extension the engine needs and could not create it. Install the extension on the server.

### DATABASE_MIGRATION_FAILED

<span class="rdm-status rdm-4xx">Not a response status</span>

A failure of a backup rehearsal, never a response status. It is the `failure.code` of a rehearsal in `GET /api/v1/system/backup-rehearsals`. Migrating the copy to this version failed. Read the message; the backup may need the version that wrote it first.

### DATABASE_REVISION_UNKNOWN

<span class="rdm-status rdm-4xx">Not a response status</span>

A failure of a backup rehearsal, never a response status. It is the `failure.code` of a rehearsal in `GET /api/v1/system/backup-rehearsals`. The copy is at a schema revision this version does not know, so it was written by a newer version. Rehearse with the version that wrote it.

### DATABASE_UNAVAILABLE

<span class="rdm-status rdm-5xx">Status 503</span>

The engine had no database connection for this request, and the answer carries `Retry-After` in seconds: `details.reason` is `unreachable`, `poolExhausted`, `tooManyConnections` or `transactionEnded`. Nothing was saved. It usually means the database is restarting or the engine's connection limits are too low for its load. Send the request again after the `Retry-After` time; if it persists, tell the operator.

### DATABASE_UNREACHABLE

<span class="rdm-status rdm-4xx">Not a response status</span>

A failure of a backup rehearsal, never a response status. It is the `failure.code` of a rehearsal in `GET /api/v1/system/backup-rehearsals`. The copy's server could not be reached. Check that it runs and that the address and role allow the connection.

### DATABASE_URL_INVALID

<span class="rdm-status rdm-4xx">Not a response status</span>

A failure of a backup rehearsal, never a response status. It is the `failure.code` of a rehearsal in `GET /api/v1/system/backup-rehearsals`. The address of the copy is not a database address the engine can use.

### DEFAULT_WORKSPACE_CANNOT_BE_RETIRED

<span class="rdm-status rdm-4xx">Status 409</span>

The request retires the default workspace. The default workspace is where requests without a workspace go, so it always stays active. Make another workspace the default first (`PATCH /api/v1/workspace-runtime-state`), then retire this one.

### DELETION_PREVIEW_CHANGED

<span class="rdm-status rdm-4xx">Status 409</span>

A cascading delete was confirmed with a `deletionPreviewToken`, but the record or what depends on it changed since the preview, or the record no longer exists. Nothing was deleted. Preview the deletion again, look at the new impact, and confirm with the new token. In a batch it is the code of the rejected item.

### DELETION_PREVIEW_REQUIRED

<span class="rdm-status rdm-4xx">Status 409</span>

A delete with `cascade=true`, in `DELETE /api/v1/objects/{object_type_key}/{object_id}` or a batch delete item, came without a `deletionPreviewToken`. A cascading delete must be previewed first. Run the delete as a preview step in a background batch (`stage: preview`), which gives each item's impact and its token, and confirm with that token.

### DELIVERY_FAILED

<span class="rdm-status rdm-4xx">Not a response status</span>

The reason of a suspended subscription, never a response status. It is `suspension.reason` of a subscription, with `details` that depend on it. A request failed for 24 hours (`details` holds `deliveryId`, `attempts`, `failingSince` and `lastError`). Repair the receiver, then resume.

### DELIVERY_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The subscription has no logged delivery with the ID in `GET /api/v1/consumer-subscriptions/{subscription_id}/deliveries/{delivery_id}` or in the resend route under it. It usually comes from an ID of another subscription, or a delivery older than the log retention. List the subscription's deliveries and use an ID from there.

### DELIVERY_NOT_SENT

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/consumer-subscriptions/{subscription_id}/deliveries/{delivery_id}/resend` named a delivery that was logged but never sent, so there is nothing to send again. Wait until the delivery has been attempted, or choose another delivery.

### DIAGNOSTICS_LEFT_OUT

<span class="rdm-status rdm-4xx">Not a response status</span>

The closing entry of the `details` list of `WORKSPACE_GRAPH_INVALID`, which lists at most 20 diagnostics of each code. One entry follows for each code with more: `details.leftOutCode` is the code and `details.count` how many diagnostics of it are not listed. Fix the listed ones and publish again, or validate the change set (`POST /api/v1/change-sets/{changeSetId}/validation`), which lists every diagnostic.

### DIGEST_NOT_SET

<span class="rdm-status rdm-4xx">Status 422</span>

`PUT /api/v1/me/notification-mail` put notice kinds into the digest, but the person has no digest frequency set. `details.kinds` lists the kinds. Nothing changed. Send `digest` (`every` and `timeZone`) in the same request or an earlier one, then choose `digest` for the kinds.

### DRAFT_HAS_NO_WORKBOOK

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/workspaces/from-workbook` named a model draft that has no workbook, so there is nothing to load into the new workspace. Nothing was created. Add the workbook to the draft (`POST /api/v1/source-files` with the draft as its owner), wait until it is read, then send the request again.

### DRAFT_HELD_BY_WORKSPACE

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/workspaces/from-workbook` was sent a model draft that another workspace already remembers as its own, so a second workspace cannot take it. `details` holds `draftId` and `workspaceKey`. Make a new draft, from the same release or workbook, and create the workspace from that.

### DRY_RUN_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The model draft has no dry run yet, so there is nothing to read at `GET /api/v1/model-drafts/{draftId}/dry-run` or its `rows`. It usually means no dry run was started for the draft. Start one with `POST /api/v1/model-drafts/{draftId}/dry-run`, then read its result.

### DUPLICATE_ATTRIBUTE

<span class="rdm-status rdm-4xx">Status 422</span>

A record write names the same attribute more than once in `attributes`. It usually comes from a client that builds the list from several sources without merging them. Send each `attributeTypeKey` once. In a batch the refusal appears in that item's result.

### DUPLICATE_ATTRIBUTE_VALUE

<span class="rdm-status rdm-4xx">Status 409</span>

The write gives an attribute that the model declares unique a value that another record in the workspace already holds. `details.attributeTypeKey` is the attribute and `details.conflictingObjectId` the record that holds the value. Use another value, or change the other record first. When the write goes into a change set, a clash that only arises between several pending changes is reported by `POST /api/v1/change-sets/{changeSetId}/validation` as a diagnostic with this code (its details are `objectId`, `attributeTypeKey` and `conflictingObjectIds`).

### DUPLICATE_BATCH_ITEMS

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/relations/batch` lists the same relationship in more than one item. `details.relationIds` holds the repeated IDs. Send each relationship once, with all its values in that one item.

### DUPLICATE_COLUMN_IDS

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/workspaces/{workspaceKey}/relation-matrix` names the same record more than once in `columnIds`. `details.path` is `/query/columnIds`. Send each column ID once.

### DUPLICATE_EDGE

<span class="rdm-status rdm-4xx">Not a response status</span>

A conflict of a publication, never a response status. It is an entry of `details.conflicts` in `VERSION_CONFLICT` when publishing a change set finds that the change set and live data both define the same directed relationship; the entry holds `conflictingRelationId`. Drop one of the two. When the change set is moved onto another release the same finding is an item of the job. A workspace migration's preview refuses a relationship the same way (a row with outcome `refused`) when a `relationTypeMappings` entry maps its relation type onto one that already links the same two records, or that another mapped relationship reaches: it stays under its own relation type, and the migration cannot be confirmed until one of the two is removed or the mapping is changed.

### DUPLICATE_INITIAL_RELATION

<span class="rdm-status rdm-4xx">Status 422</span>

A new record's `initialRelations` repeat the same relationship type, direction and other record. It usually comes from a list built without removing duplicates. Send each initial relationship once. The check applies to live creation and to creation in a change set alike.

### DUPLICATE_KEY

<span class="rdm-status rdm-4xx">Not a response status</span>

A model validation finding, never a response status. It is an error in the `diagnostics` of a model draft or of a validated model, at its `path`. A key is declared twice where it must be unique, such as a navigation group of an application. Rename one.

### DUPLICATE_KEY_IN_FILE

<span class="rdm-status rdm-4xx">Not a response status</span>

A row error of an import, never a response status. It is the `error` of a row in `GET /api/v1/jobs/{job_id}/rows` and of its items, and the row is not loaded. Rows of the file hold one key with different values, or give one related record different values; `details.rows` lists the other rows. Make the rows agree or remove the repeats.

### DUPLICATE_RELATION

<span class="rdm-status rdm-4xx">Status 409</span>

The relationship the write would create already exists between the two records, or, when a whole set is replaced in a batch, a record is listed twice in it. It usually happens when a create is sent again after the first one succeeded. Read the existing relationship instead of creating it again. In a batch it appears in that item's result.

### DUPLICATE_RELATION_SCOPE

<span class="rdm-status rdm-4xx">Status 409</span>

The model allows only one related record per ancestor scope for this relationship, and the source already has one in the scope of the target. `details` holds `ancestorObjectTypeKey`, `ancestorObjectId`, `conflictingObjectId` and `conflictingRelationId`. Remove the existing relationship or choose a target in another scope. In a change set the write is accepted and the breach is reported as a diagnostic with this code by `POST /api/v1/change-sets/{changeSetId}/validation`; it stays to fix before the change set is published.

### EFFECTIVE_PERIOD_DROPPED

<span class="rdm-status rdm-4xx">Not a response status</span>

A reason of a move, never a response status. The target type has no effective period, so the record's period values are not carried. It is an entry of `leftBehind` of a row of the move's dry run.

### ELEMENT_NOT_IN_RELEASE

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem of a model mapping, never a response status. It is an entry of the mapping's `problems`, at its `pointer` on the `source` or `target` side; an operation that would cause it is refused when applied. The release has no type, attribute or relationship type the mapping names. Choose one the release declares.

### EMAIL_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

`PATCH /api/v1/users/{userId}` would leave an active person without an e-mail address, which is the name they sign in with. It usually means the request clears `email` or activates a person who has none. Send an e-mail address in the same request.

### EMAIL_TAKEN

<span class="rdm-status rdm-4xx">Status 409</span>

Another person already has this e-mail address; the comparison ignores upper and lower case. It arises on `POST /api/v1/users` and on `PATCH /api/v1/users/{userId}` with a new `email`. Use another address, or work with the existing person.

### EVENTS_EXPIRED

<span class="rdm-status rdm-4xx">Status 410 or 409</span>

The events after a position the client holds are no longer kept. It is `410` when a consumer API's event feed (`GET /api/consumer/{consumerApi}/v{n}/events`) or a new subscription's `startAfter` names a position older than the feed keeps; `details` holds `earliestPosition`, `headPosition` and `publication`, the publication to read instead (a `pointer` is added for a body field). It is `409` when `POST /api/v1/consumer-subscriptions/{subscriptionId}/resume` finds that the events the subscription had not acknowledged expired; `details` holds `fromPosition`, `toPosition` and, for a consumer API subscription, `publication`. The same code is also the suspension reason of a subscription whose delivery fell too far behind. Read the publication or a live export as a new baseline, then continue from its position; to resume a subscription, send `reset: true` and reload the receiver.

### EVENTS_NOT_DECLARED

<span class="rdm-status rdm-4xx">Status 404 or 400</span>

The consumer API, at the contract version asked for, declares no events. It is `404` on `GET /api/consumer/{consumerApi}/v{n}/events`. It is `400` when `POST /api/v1/consumer-subscriptions` or an edit of a subscription names such an API; `details.pointer` is `/consumerApi`, and on resume it is listed among the `errors` of `SUBSCRIPTION_NEEDS_EDIT`. The release the workspace runs has not declared events for this API, or the client asks an older contract version. Ask for a version that declares events, or have an administrator add them to the model.

### EVENT_NOT_IN_DELIVERY

<span class="rdm-status rdm-4xx">Status 404</span>

`POST /api/v1/consumer-subscriptions/{subscriptionId}/deliveries/{deliveryId}/resend` names an `eventId` that the delivery's request did not carry. `details.pointer` is `/eventId`. It usually means the ID comes from another delivery. Read the delivery with `GET /api/v1/consumer-subscriptions/{subscriptionId}/deliveries/{deliveryId}` and send an event ID it holds.

### EVENT_POSITION_AHEAD

<span class="rdm-status rdm-4xx">Status 409</span>

The position the client gives is past the head of the events. `details.headPosition` is the head; for a body field `details.pointer` is `/startAfter`. It applies to a consumer API's event feed read and to `startAfter` of `POST /api/v1/consumer-subscriptions`. A position the engine gave out cannot be ahead, so it was taken from another workspace's events, or the database was restored to an earlier state. Read the workspace again from a publication and follow the events from there.

### EXPORT_TEXT_TOO_LONG

<span class="rdm-status rdm-4xx">Not a response status</span>

An export of an XLSX workbook holds a text of more than 32,767 characters, which is all a workbook cell holds; the file would carry it cut off or not open whole in Excel. It is the `error` of the failed export job. `details` holds `sheet`, `row`, `recordId` (the record the text is on, null where the sheet has no record column), `field` (the column's label), `length` and `limit`. Nothing is written. Shorten the text where it is stored, leave the field out of the export, or export the same records as CSV or JSON Lines, which hold it whole. A relation column's list over the limit is not this error: it is cut in its cell and written whole on its relationship's own sheet.

### FEED_POSITION_AHEAD

<span class="rdm-status rdm-4xx">Status 409</span>

The `after` position of a feed read is past the feed's head, which `details.headPosition` holds. A position the engine gave out cannot be ahead, so the reader took it from another workspace's feed, or the database was restored to an earlier state. Read the workspace again from a baseline (an export or a publication) and follow the feed from there.

### FEED_POSITION_EXPIRED

<span class="rdm-status rdm-4xx">Status 410</span>

The `after` position is older than the feed keeps (`FEED_RETENTION_DAYS`, 30 days unless the operator changed it). `details` holds `earliestPosition` (the oldest position still answered), `headPosition`, `publication` (the active publication to read instead: its `id`, `publicationNumber` and `feedPosition`) and `export.href` (the route that exports live data). A reader that stopped for longer than the retention period reads the named publication or an export, then follows the feed from that baseline's position.

### FILTER_MATCHES_NOTHING

<span class="rdm-status rdm-4xx">Status 400</span>

A filter of a consumer subscription holds a value that no record of the workspace matches. `details` holds `parameter`, `values` (the unmatched ones) and `pointer` (`/filters/<name>`). It arises on `POST /api/v1/consumer-subscriptions`, when editing one, and in the `errors` of `SUBSCRIPTION_NEEDS_EDIT` on resume. A running subscription is suspended with this code, adding `position`, when a filter value no longer matches a record. Correct the filter value, then resume.

### FLAG_WITHOUT_TARGET

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. A `relationFlags` binding lists flag columns that have no entry in its `targets`; the message names them. Give each column the name of the record it stands for.

### FORBIDDEN

<span class="rdm-status rdm-4xx">Status 403</span>

The caller is signed in but holds none of the action groups the operation needs in the workspace it works in, or at the instance for an operation that works at the instance. `details.action` is the action, `details.groups` the groups that would allow it and `details.workspaceKey` the workspace (null at the instance). It usually means the caller's roles do not cover this workspace. A client does not retry; an administrator grants the role.

### GRANT_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

`DELETE /api/v1/grants/{grantId}` names a grant that does not exist. It usually means the grant was already removed, or the ID comes from another instance. List the grants again and use an ID from the list.

### GRANT_SCOPE_INVALID

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/grants` gives a scope the grant cannot have. The scope must be either the instance (`instance: true`) or one workspace (`workspaceKey`), never both and never neither. An instance grant is not narrowed by `applications` or `recordTypes`. A consumer API grant needs one workspace and no narrowing. A workspace grant of a role whose action groups are held only at the instance is refused too; `details.role` then names the role. Change the scope; grant such a role at the instance.

### GRANT_SCOPE_UNKNOWN

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/grants` narrows a workspace grant to an application or record type that the workspace's model does not have, or grants a consumer API that the model does not declare. `details` lists `applications` and `recordTypes` that were not found, or holds `consumerApi`. It usually comes from a key of another model release or a misspelt key. Use keys that the workspace's model has.

### GROUP_CLAIM_TAKEN

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/groups` makes a provider group for a claim value that another group already stands for at the same sign-in provider. The message names that group. Use the existing group instead of creating another.

### GROUP_FROM_PROVIDER

<span class="rdm-status rdm-4xx">Status 409</span>

The group's members come from its sign-in provider at each sign-in, so a request cannot change them. It applies to adding and removing members, singly or in a batch, on a group made from a provider claim. Change the person's membership at the provider.

### GROUP_MEMBER_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

`DELETE /api/v1/groups/{groupId}/members/{userId}` names a person who is not a member of the group. Nothing is removed. Read the group's members with `GET /api/v1/groups/{groupId}/members`; the batch removal does not refuse this case, it reports `notMember` for such a person.

### GROUP_NAME_TAKEN

<span class="rdm-status rdm-4xx">Status 409</span>

Another group already has this name; the comparison ignores upper and lower case. It arises on `POST /api/v1/groups` and on `PATCH /api/v1/groups/{groupId}` with a new `name`. Choose another name.

### GROUP_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The group named in the path of a group route, or as the principal of `POST /api/v1/grants`, does not exist. It usually means the group was deleted or the ID is from another instance. List the groups with `GET /api/v1/groups` and use an ID from the list.

### HEADER_ROW_NOT_FOUND

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import's file, listed in `details.problems` of `IMPORT_FILE_MISMATCH`. The sheet ends before the source's `headerRow`. Correct `headerRow` in the profile, or send the right file.

### HISTORY_PERIOD_INVALID

<span class="rdm-status rdm-4xx">Status 422</span>

The period of an account of changes is empty or reversed (`until` is not later than `since`), or its `timeZone` is not a known time zone. It arises on `POST /api/v1/workspaces/{workspaceKey}/history/account` and `POST /api/v1/objects/{objectTypeKey}/{objectId}/history/account`. Send `until` later than `since` and an IANA time zone name such as `Europe/Berlin`.

### HTTP_ERROR

<span class="rdm-status rdm-4xx">Status 4xx</span>

The status is the one the web framework chose, for example 404 for an address no operation has and 405 for a method the address does not take. The `message` is the framework's. An operation that is switched off by a setting is not registered, so it answers 405 where another operation has its address and 404 where none does. Creating, changing and deleting workspaces answer 405 when `WORKSPACE_ADMIN_MUTATIONS_ENABLED` is false, as do the writes of a model mapping that share their address with a read when `INTEGRATION_JOBS_ENABLED` is false. The model administration operations (drafts, installing and activating releases) answer 404 when `MODEL_ADMIN_MUTATIONS_ENABLED` is false, as do undo, redo and applying inference on a model mapping when `INTEGRATION_JOBS_ENABLED` is false. Starting a workspace migration also needs `INTEGRATION_JOBS_ENABLED`.

### IDEMPOTENCY_IN_PROGRESS

<span class="rdm-status rdm-4xx">Status 409</span>

A request with the same `Idempotency-Key` was accepted earlier and its job is still running, so there is no finished answer to repeat yet. The answer carries `Retry-After: 1` and `details.jobId` names the running job. Send the same request again after a short wait, or follow the job with `GET /api/v1/jobs/{jobId}`. It applies to `POST /api/v1/batches` and `POST /api/v1/imports`.

### IDEMPOTENCY_KEY_REUSED

<span class="rdm-status rdm-4xx">Status 422</span>

The `Idempotency-Key` was used before with a different request, so nothing was run. `details.jobId` names the job of the first request. A key stands for one request: send a new key for a new request, and the same key only for a retry of an identical one. It applies to `POST /api/v1/batches` and `POST /api/v1/imports`.

### IDENTITY_COLLISION

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a change set's whole-graph check, never a response status. It is an error in the `diagnostics` of `POST /api/v1/change-sets/{change_set_id}/validation`, in the `details` of `CHANGE_SET_INVALID` when submitting is refused, and in the diagnostics that refuse a publication or a migration of the change set. One stable ID is used by both a record and a relationship; `details.id` names it. A client assigns IDs: give one of them another.

### IDENTITY_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

`DELETE /api/v1/users/{userId}/identities/{provider}` names a provider the person has no sign-in with. It usually means the identity was already removed.

### IDENTITY_PROVIDER_TAKEN

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/users/{userId}/identities` would move an identity from the person named in `fromUserId` to a person who already signs in with the same provider. Nothing moves. Remove the existing identity with `DELETE /api/v1/users/{userId}/identities/{provider}` first, or link another person.

### ID_COLLISION

<span class="rdm-status rdm-4xx">Not a response status</span>

A conflict of a publication, never a response status. It is an entry of `details.conflicts` in `VERSION_CONFLICT` when publishing a change set finds that the ID of a record or relationship the change set created already exists in live data; the entry names its `kind` and `id`. Give the new one another ID.

### IMMUTABLE_RELATION

<span class="rdm-status rdm-4xx">Status 422</span>

A relationship write targets a containment relationship, which the engine keeps itself: the one between a record and its parent. It cannot be created, changed or deleted on `POST /api/v1/relations`, `PATCH /api/v1/relations/{relationId}` or `DELETE /api/v1/relations/{relationId}`. Move a record by changing its parent in a record edit.

### IMPACT_SUMMARY_DRAFT_INVALID

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/model-drafts/{draftId}/impact-summary` was asked about a draft that does not compile, so what it changes cannot be described. `details` is the list of the draft's diagnostics. Fix the draft until its compilation is valid, then ask again.

### IMPORT_FILE_MISMATCH

<span class="rdm-status rdm-4xx">Not a response status</span>

The file does not fit the import profile, for example a sheet or a column the profile names is missing, or a column letter is beyond the table. `details.problems` lists every problem with its `path`, `code` and `message`. It is found when the import's job reads the file, so it appears as the `error` of the failed job at `GET /api/v1/jobs/{jobId}`, not as the status of `POST /api/v1/imports`. Change the file or the profile and import again.

### IMPORT_FILE_MISSING

<span class="rdm-status rdm-4xx">Status 410</span>

The file of the import is no longer in the engine's job file directory. It arises on `POST /api/v1/jobs/{jobId}/reread`, and as the `error` of an import job whose file was removed before it was read. Send the file again with a new import. Operators check the job file directory and what removes files from it.

### IMPORT_FILE_UNREADABLE

<span class="rdm-status rdm-4xx">Status 422</span>

The file cannot be read as the format it claims: a workbook that is not a valid XLSX file, a CSV file that is not UTF-8 or breaks its quoting, a JSON Lines file that is not UTF-8, or a workbook whose import profile sheet cannot be read. The message says what failed and, for a CSV, `details.line` the line. `POST /api/v1/imports` refuses it when a workbook sent without a profile cannot be opened or its profile sheet cannot be read; in other cases the problem is found while a job reads the file (an import, or the profile job of `POST /api/v1/source-files`) and appears as the `error` of that job at `GET /api/v1/jobs/{jobId}`. Save the file again in the right format and send it again.

### IMPORT_HAS_NO_PROFILE

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/jobs/{jobId}/reread` was sent for an import that was read without a profile, so it has no columns to read differently. `details.jobId` names the job. Import with a profile, or send the file again.

### IMPORT_PROFILE_EXISTS

<span class="rdm-status rdm-4xx">Status 409</span>

An import profile with this key exists already. It arises on `POST /api/v1/import-profiles`, and when a profile is saved under a key that holds a profile of another model, as in `POST /api/v1/ai/tasks/{taskId}/run` with `saveProfile`. Choose another key, or change the existing profile with `PUT /api/v1/import-profiles/{profileKey}`.

### IMPORT_PROFILE_MODEL_MISMATCH

<span class="rdm-status rdm-4xx">Status 422</span>

The import profile belongs to another model than the workspace runs. `details` holds `profileKey`, `modelKey` (the profile's model) and `workspaceModelKey`. A profile is written against one model and used only in workspaces running it; a stored profile read under another model reads as not valid with this as its one problem. It is answered by `POST /api/v1/imports`, `PUT /api/v1/import-profiles/{profileKey}` and `POST /api/v1/source-files`. Use a workspace of the profile's model, or save a profile for the other model.

### IMPORT_PROFILE_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The import profile named in the path or in `profileKey` does not exist. It usually means the key is misspelt or the profile was deleted. List the profiles with `GET /api/v1/import-profiles`.

### IMPORT_TOO_LARGE

<span class="rdm-status rdm-4xx">Status 413</span>

The uploaded file is larger than the instance accepts. `details` holds `setting` (`IMPORT_MAX_BYTES`), `maximum` and `bytes`. It applies to `POST /api/v1/imports`, `POST /api/v1/source-files` and `POST /api/v1/ai/tasks`. Split the file, or ask the operator to raise the limit.

### IMPORT_TOO_MANY_ITEMS

<span class="rdm-status rdm-4xx">Not a response status</span>

The rows of the file make more items than one job may run. `details` holds `setting` (`ATOMIC_JOB_MAX_ITEMS` for an atomic import, `BACKGROUND_JOB_MAX_ITEMS` otherwise), `maximum` and `items`. It is found when the job reads the file, so it appears as the `error` of the failed job at `GET /api/v1/jobs/{jobId}`, not as the status of `POST /api/v1/imports`. Split the file into smaller imports.

### INCOMPLETE_VIEW_IDENTITY

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/workspaces/{workspaceKey}/relations` was sent with only one of `applicationKey` and `viewKey`. A view is named by both. Send both, or neither.

### INFERENCE_DISAGREES

<span class="rdm-status rdm-4xx">Not a response status</span>

A warning of a model draft's import profile, never a response status. It is an entry of the profile's warnings in a draft step's answer and does not block the step. The draft reads a column otherwise than the latest inference of the workbook does; nothing was changed. The warning names the sheet, the column, both readings and the pattern. Apply the proposal or keep the draft's reading.

### INFERENCE_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The model draft or model mapping has no inference yet, so there are no proposals to read or apply. It arises on the `inference` routes under `/api/v1/model-drafts/{draftId}` and `/api/v1/model-mappings/{key}`. Start one first with `POST /api/v1/model-drafts/{draftId}/inference` or `POST /api/v1/model-mappings/{key}/inference`.

### INFERENCE_NOT_READY

<span class="rdm-status rdm-4xx">Status 409</span>

The latest inference has not completed, so its proposals cannot be read or applied. `details.state` is the state of the inference job. It usually means the inference is still running or it failed. Wait until it is completed, or start it again.

### INFERENCE_STALE

<span class="rdm-status rdm-4xx">Status 409</span>

The proposals no longer fit what they were made for, so they were not applied. For a draft, it was changed after the inference (`details.inferenceDraftVersion` and `details.draftVersion`). For a mapping, it names other releases than the inference read (`details.inferenceMappingVersion` and `details.mappingVersion`). It arises on `POST .../inference/application`. Run the inference again, then apply the new proposals.

### INTERNAL_ERROR

<span class="rdm-status rdm-5xx">Status 500</span>

The engine failed in a way it did not expect. `details.correlationId` (also the `X-Request-Id` header) names the request in the engine's log. Retrying a read is safe; before retrying a write, read the data to see whether it was saved. Give the correlation ID to the operator.

### INVALID

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem of an assistant task's check, never a response status. A property of the draft's import profile is not valid: it is an entry of `profileProblems` with the `path` of the property and why (unknown, required or of the wrong shape). Correct the property.

### INVALID_AS_OF

<span class="rdm-status rdm-4xx">Status 400</span>

The `asOf` parameter of a consumer API read is not one calendar date written `YYYY-MM-DD`: it has a time or a zone, is an impossible day, or is given more than once. `details.path` is `/query/asOf`. Send a single date.

### INVALID_ATTRIBUTE

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/workspaces/{workspaceKey}/relation-grid` names an `attribute` that is not one of the view's `attributeColumns`. `details.path` is `/query/attribute`. Send only attribute keys that the view declares.

### INVALID_ATTRIBUTE_VALUE

<span class="rdm-status rdm-4xx">Status 422</span>

A value does not have the type the attribute declares, for example text where a number or a date is expected. The message names the attribute. It applies to every write of attribute values, in a batch as that item's result and in an import as the rejection of that cell, where the message quotes the cell. A value outside a declared range has its own codes. Send the value in the attribute's type, as the model describes it.

### INVALID_BATCH_CONTEXT

<span class="rdm-status rdm-4xx">Status 422</span>

The request does not name exactly one place to write. A batch or an import names either `workspaceKey` for live data or `changeSetId` for a change set, not both and not neither, and `expectedChangeSetVersion` only goes with `changeSetId`. `details.pointer` locates the field. Fix the request; a change set without `expectedChangeSetVersion` is refused as `CHANGE_SET_REQUIRED`.

### INVALID_CANVAS

<span class="rdm-status rdm-4xx">Status 422</span>

A change to a model draft's canvas would leave it with more than 500 cards. `PATCH /api/v1/model-drafts/{draftId}/canvas` refuses it and changes nothing; `details` holds `cards` and `limit`. Remove the positions of cards that no longer exist (send them as `null`) in the same request, or send fewer.

### INVALID_CELL

<span class="rdm-status rdm-4xx">Not a response status</span>

A cell of an import row is not what its column needs. A row of an export's table layout, sent back as an import without a profile, holds an ID that is not a UUID, a version that is not a whole number from 1, or a type the model does not have; a cell of any import holds a character that cannot be stored (a NUL or an unpaired surrogate), or a value to find a record by that is over 2,000 bytes; a key cell of a profile's source that cannot be read is this refusal too, whatever `rowsWithoutKey` says. It is the row's refusal in the job's rows (`GET /api/v1/jobs/{jobId}/rows`), and `details.column` names the column. Correct the cell in the file.

### INVALID_CLEAR_ATTRIBUTES

<span class="rdm-status rdm-4xx">Status 422</span>

`PUT /api/v1/workspaces/{workspaceKey}/mappings` clears a mapping (no `targetObjectId`) but also sends `attributes`. A clear takes none. Omit `attributes` or send an empty object.

### INVALID_CURSOR

<span class="rdm-status rdm-4xx">Status 422</span>

The `cursor` of a collection read is not one the engine can use: it is not a cursor, it was made for another collection, another sort or other filters, or it was altered. Cursors are opaque and bound to the request that produced them. Start again from the first page and pass `nextCursor` back unchanged, with the same filters.

### INVALID_DATE

<span class="rdm-status rdm-4xx">Status 422</span>

The `since` or `until` argument of the `history_facts` tool is not an ISO 8601 date and time. The tool is called through the assistant endpoint `/mcp`, so the refusal appears in the text of the tool's result, starting with `INVALID_DATE:`, and not as an HTTP status. Send both arguments as ISO 8601 date-times.

### INVALID_EFFECTIVE_PERIOD

<span class="rdm-status rdm-4xx">Status 422</span>

A write gives a record an effective period whose end is not after its start. `details` holds `startAttributeTypeKey`, `endAttributeTypeKey`, `start` and `end`. Send an end date later than the start date, or leave one open. The same code appears as a compatibility diagnostic, with a count of records, when a model release declares or moves the effective period and stored records already break it; the data has to be corrected before the release is used.

### INVALID_EXPAND

<span class="rdm-status rdm-4xx">Status 422</span>

The `expand` parameter of `GET /api/v1/objects/{objectTypeKey}` names a relationship key more than once, or a key or field that the type does not have. `details.parameter` is `expand` and `details.value` the key. Send each key once, and only keys or reverse keys of relationships the type has, with an optional field of the related records.

### INVALID_EXPECT

<span class="rdm-status rdm-4xx">Status 400</span>

The `expect` parameter of a consumer API's `xref` read is neither `any` nor `one`. `details.path` is `/query/expect`. Send one of the two, or omit it for `any`.

### INVALID_EXPORT_LAYOUT

<span class="rdm-status rdm-4xx">Status 422</span>

An export asks for a layout that cannot be built. The `layout` or `people` options do not fit the request: the people layout is an XLSX workbook only, `people` goes only with the layout `people`, and its columns and sheets must exist in the model. `details.path` is the JSON pointer of the offending field, and a refusal of the workbook's own import profile adds `details.problems`. It is returned by `POST /api/v1/exports`. Correct the field the pointer names, or use the technical layout.

### INVALID_FILTER

<span class="rdm-status rdm-4xx">Status 422</span>

A `filter.<field>.<operator>` parameter, or a filter of an object query, cannot be applied: the form is wrong, the field is not one the list or view can filter by, the operator is not supported for it or the value does not fit its type. The message names the cause, and `details.path` locates the parameter, for example `/query/filter.name.eq`. Some lists add which fields they do accept. Fix the parameter, or use the list that offers the field.

### INVALID_GRID_CHANGE

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/relations/grid-change` cannot be applied: the `attributeTypeKey` is not an attribute of the view's relationship or does not hold scalar values, the `value` is not of its type, or some of the listed records are not of the view's types in this workspace. `details.path` locates the field; for records `details.objectIds` lists up to 20 of them. Nothing is written. Fix the field the path names.

### INVALID_IMPORT_PROFILE

<span class="rdm-status rdm-4xx">Status 422</span>

An import profile does not fit the model release it is checked against. `details.problems` lists every problem, each with `path` (a JSON pointer into the profile), `code` and `message`. It is raised when a profile is saved (`POST /api/v1/import-profiles`, `PUT /api/v1/import-profiles/{profileKey}`), sent with an import (`POST /api/v1/imports`, by key, inline or carried in the workbook) or used for a model draft's dry run (`POST /api/v1/model-drafts/{draftId}/dry-run`). It usually means the profile names a type, attribute or relationship the active model does not have, or its sources reference each other in a cycle. Correct the listed paths and send it again. A dry run that falls back on the draft's own profile and finds none answers the same code with `details.pointer` `/profile`; send a profile in the request.

### INVALID_IMPORT_READING

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/jobs/{jobId}/reread` named a reading the import's binding report cannot take. `details.path` points at the part of `readings` at fault: a source the report does not have, a column that is not a relationship or matrix column of that source, or a `field` that does not identify the related type's records. It usually comes from a stale report or a misspelt field. Read the preview's binding report again and send one of the options it lists for that column.

### INVALID_INFERENCE_REQUEST

<span class="rdm-status rdm-4xx">Status 422</span>

The request names an application the draft does not suit. `POST /api/v1/model-drafts/{draftId}/inference` refuses an `applicationKey` the draft lacks when extending it, or one the draft already has when creating a new application. `POST /api/v1/model-drafts/{draftId}/inference/list` refuses an `applicationKey` the draft lacks. `details.pointer` is `/applicationKey`. Send the key of an application the draft holds, or a new key.

### INVALID_INSTALLED_MODEL

<span class="rdm-status rdm-5xx">Status 500</span>

A model release stored in the engine no longer compiles, so the operation cannot compare or activate it. It is raised by `GET /api/v1/model-releases/{releaseId}/diff`, `POST /api/v1/workspaces/{workspaceKey}/model/activation`, `POST /api/v1/model-drafts/{draftId}/compile` (for the baseline release) and the impact summaries; where the compile diagnostics exist, `details` lists them. It points at the engine's data or version, not at the request. Retrying does not help; tell the operator.

### INVALID_MIGRATION_MAPPING

<span class="rdm-status rdm-4xx">Status 422</span>

A type, attribute or relation-type mapping in a model migration names something the two models do not hold, or names it twice. `details.pointer` is the JSON pointer into the request, such as `/typeMappings/0/toObjectTypeKey`. It is raised when a migration is started with `POST /api/v1/workspaces/{workspaceKey}/model/migrations` or `POST /api/v1/change-sets/{changeSetId}/model-migrations`. It usually comes from a mapping written against another release. Correct the mapping at the pointer and start the migration again.

### INVALID_MODEL

<span class="rdm-status rdm-4xx">Status 422</span>

A model draft does not compile, and the operation needs a valid draft. `details` lists the diagnostics (or holds them under `diagnostics` for the consumer API documents). It is raised when a draft is installed (`POST /api/v1/model-drafts/{draftId}/installation`), dry-run, used for inference, or asked for a consumer API's schema, example or OpenAPI document. The same string is also the `code` of many diagnostics in compile results. Fix the draft with operations until `POST /api/v1/model-drafts/{draftId}/compile` reports it valid, then repeat the request.

### INVALID_MODEL_MAPPING

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/model-mappings` named a side of the mapping by both a workspace and a release, or by neither. `details.pointer` points at `/sourceWorkspaceKey` or `/targetWorkspaceKey`, whichever side is at fault. Name each side by exactly one of a workspace or a release.

### INVALID_NAME

<span class="rdm-status rdm-4xx">Not a response status</span>

A row's name is longer than 500 characters, so the row is refused. It appears in the job's rows (`GET /api/v1/jobs/{jobId}/rows`), and `details.column` names the column. Shorten the name in the file.

### INVALID_OBJECT_TYPE_FOR_APPLICATION

<span class="rdm-status rdm-4xx">Status 422</span>

The object type is not enabled in the application the request names. It is raised when a record is created (`POST /api/v1/objects`, a change set's record, a batch item) and when a record read passes both `applicationKey` and an object type. It usually means the application key and the type key were taken from different places. Read the application's `objectTypeKeys` and send a pair that belongs together. In a batch it appears in the item's rejected outcome.

### INVALID_OPERATION

<span class="rdm-status rdm-4xx">Status 422</span>

One step of an operations list cannot be applied to the document it targets. It is raised for model drafts (`POST /api/v1/model-drafts/{draftId}/operations` and the draft inference that applies operations) and for model mappings (`POST /api/v1/model-mappings/{key}/operations`). `details` holds `index` (the step), `pointer` (the parameter at fault) and `reason` (a machine-readable word). The whole request is refused and nothing is applied. Correct the step at the pointer and send the list again.

### INVALID_ORIGIN

<span class="rdm-status rdm-4xx">Status 422</span>

The `origin` filter of `GET /api/v1/jobs` is not `aiTask:<id>` or `modelDraft:<id>`. `details.path` is `/query/origin`. Send one of those two forms, with the ID of an assistant task or a model draft.

### INVALID_PAGE_PARAMETER

<span class="rdm-status rdm-4xx">Status 422 or 400</span>

A paging or list parameter holds a value the read does not accept. On `GET /api/v1/jobs/{jobId}/rows`, a `status` or `outcome` that belongs to another kind of job answers 422 with `details.parameter` and `details.allowed`. On the consumer API's list, cross-reference and publication reads, `from` other than `start` or `end`, or `includeTotal` other than `true` or `false`, answers 400 with `details.path`. Send one of the allowed values.

### INVALID_PAGE_SIZE

<span class="rdm-status rdm-4xx">Status 400</span>

`pageSize` of a consumer API read is not a whole number in the range the read allows. Lists, cross-references, publications and the API index take 1 to 100; the events feed takes 1 to 100 with `payload=full` and 1 to 1000 with `payload=identity`. `details.path` is `/query/pageSize`. Send a size in range, or leave it out for the default.

### INVALID_PARENT_TYPE

<span class="rdm-status rdm-4xx">Status 422</span>

The parent record's type is not permitted for this object type, or no single containment relation allows it. It is raised when a record is created or moved with a `parent` (`POST /api/v1/objects`, `PATCH /api/v1/objects/{objectTypeKey}/{objectId}`, a change set's record writes) and in batch items. `GET /api/v1/objects/{objectTypeKey}/{objectId}/parent-candidates` raises it for a `parentObjectTypeKey` that cannot contain the type, with `details.parentObjectTypeKey` and `details.permitted`. Choose a parent of a permitted type.

### INVALID_PAYLOAD

<span class="rdm-status rdm-4xx">Status 400</span>

The `payload` parameter of the consumer API's events feed is neither `full` nor `identity`. `details.path` is `/query/payload`. Send one of the two, or leave it out for `full`.

### INVALID_POSITION

<span class="rdm-status rdm-4xx">Status 422 or 400</span>

A position parameter is not usable. On the management API's list reads, a negative `position` answers 422. On the consumer API, a `position` that is not a whole number, or an `after` of the events feed that is not a whole number of 0 or more, answers 400. `details.path` names the parameter. Send a whole number of 0 or more, or read from the first page.

### INVALID_QUERY

<span class="rdm-status rdm-4xx">Status 422</span>

A query names something the model cannot answer: an unknown type, a criterion the type's fields cannot answer, or an `asOf` that is not a date. `details.path` is a JSON pointer into the request body. It is raised by `POST /api/v1/workspaces/{workspaceKey}/queries/objects`, and by `POST /api/v1/exports` and `POST /api/v1/moves` for the criteria of their selection (the pointer then starts at the selection). Read the model, correct the criterion at the pointer and send the request again.

### INVALID_RANGE

<span class="rdm-status rdm-4xx">Status 422</span>

A spreadsheet range is not usable. `GET /api/v1/source-files/{sourceFileId}/profile/sheets/{sheet}/cells` refuses a `range` that is not a rectangle such as `A3:C12`, is empty, or lies outside the sheet's used area; `details.range` and `details.path` (`/query/range`) say which. `POST /api/v1/model-drafts/{draftId}/inference/list` refuses a `block` that holds no value under its header or that is not a list; `details.path` is `/block`. Name the corners of a range that holds cells.

### INVALID_RECORD_KEY

<span class="rdm-status rdm-4xx">Not a response status</span>

A batch item identifies a record by an attribute that is not declared unique on its object type. The code appears in the rejected item's `error`, in the batch's outcomes (`POST /api/v1/batches` run inline, or `GET /api/v1/jobs/{jobId}/items`), not as the response status. `details` holds `pointer`, `objectTypeKey` and `attributeTypeKey`. Use an attribute the type declares unique, or identify the record by its ID.

### INVALID_REFERENCE

<span class="rdm-status rdm-4xx">Not a response status</span>

A model validation finding, never a response status. It is an error in the `diagnostics` of a model draft or of a validated model, at its `path`. A declaration names something that does not exist, such as a collection or view a navigation group lists. Name one the application has.

### INVALID_RELATION_PAIR

<span class="rdm-status rdm-4xx">Status 422</span>

The relation type is not allowed between these two object types, in the direction given. It is raised when relations are written (`POST /api/v1/relations`, relation updates and set replacements, a batch's relation items), and by `GET /api/v1/relations/held` when the object type has no binding of the relation type (`details.parameter` is `relationTypeKey`). Check the model for the types the relation type connects and send a permitted pair. In a batch it appears in the item's outcome.

### INVALID_SEEK

<span class="rdm-status rdm-4xx">Status 422 or 400</span>

The `seek` value of a list read cannot be read as a value of the list's first sort field, for example text where a number or date is sorted. `details.path` is `/query/seek`. The management API answers 422; the consumer API answers 400. Send a value of the sort field's type, or page with a cursor.

### INVALID_SORT

<span class="rdm-status rdm-4xx">Status 422</span>

The `sort` of a list read names a field the list cannot sort by: a field that is not one of the view's sort fields, a JSON attribute, a field that needs a single object type when the list holds several, or a timestamp that change sets and publications do not record. `details.path` is `/query/sort`; the cross-type record list also holds `builtInSorts` and `route`. Sort by a field the list supports; the view or the per-type list names them.

### INVALID_TYPE_MAPPING

<span class="rdm-status rdm-4xx">Status 422</span>

An attribute mapping for a change of object type does not fit: the target attribute is not bound on the new type, the source is not bound on the old type, or the two value types are not compatible. `details` holds `attributeTypeKey` (the target) and, where relevant, `from`, `fromObjectTypeKey`, `toObjectTypeKey`, `fromValueType` and `valueType`. It is raised when a restructuring with `mappings` is previewed or applied (`POST /api/v1/change-sets/{changeSetId}/restructurings/preview` and `.../restructurings`). Map a compatible source, or leave the attribute unmapped.

### INVALID_WEBHOOK_URL

<span class="rdm-status rdm-4xx">Status 400</span>

The URL of a subscription is not allowed. It must be an absolute `https` URL of at most 2,048 characters, without user information or a fragment; plain `http` is accepted only for `localhost`, `127.0.0.1` and `::1`. An address that is, or whose host name resolves to, a private or otherwise non-public address is refused too, unless the instance allows private addresses (`WEBHOOK_PRIVATE_ADDRESSES_ALLOWED`, off by default); a link-local address is refused always. `details.pointer` is `/url`. It is raised when a subscription is created or edited (`POST /api/v1/consumer-subscriptions`, `PATCH /api/v1/consumer-subscriptions/{subscriptionId}`); when several things are wrong, the first is answered. Send a valid URL.

### JOB_CANCELLED

<span class="rdm-status rdm-4xx">Not a response status</span>

The reason of an item that did not run: the job was cancelled before the worker reached it. It appears as `reason` in the job's items (`GET /api/v1/jobs/{jobId}/items`); the chunks committed before the cancel stay applied. Send the items that are `unprocessed` again if they are still wanted.

### JOB_EXPIRED

<span class="rdm-status rdm-4xx">Status 410</span>

The job passed its retention and what it kept is gone. `POST /api/v1/jobs/{jobId}/confirm` answers it for a preview that waited too long, whose file or items were removed; `GET /api/v1/jobs/{jobId}/output` answers it for an export whose file was removed. Send the import or batch again, or request the export again.

### JOB_FAILED

<span class="rdm-status rdm-4xx">Not a response status</span>

The job stopped because of an internal error, or because a refusal reached it that is not its own. The job is `failed`; as an error its `details.correlationId` names the log entry, and the items it applied before stay applied. As an item's `reason` it marks the items that were not reached. Send the `unprocessed` items again; if it recurs, report the correlation ID to the operator.

### JOB_FINISHED

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/jobs/{jobId}/cancel` named a job that is no longer queued, running or waiting. `details` holds `jobId` and `state`. It usually means the job completed before the request arrived. Read the job with `GET /api/v1/jobs/{jobId}`; there is nothing to cancel.

### JOB_HAS_NO_OUTPUT

<span class="rdm-status rdm-4xx">Status 404</span>

`GET /api/v1/jobs/{jobId}/output` named a job that is not an export; only an export has a file. A batch's or an import's outcomes are read from `GET /api/v1/jobs/{jobId}/items` or `.../rows`.

### JOB_HAS_NO_ROWS

<span class="rdm-status rdm-4xx">Status 404</span>

`GET /api/v1/jobs/{jobId}/rows` named a job that has no rows by row. Imports, dry runs, profile checks, migrations and moves have them; batches and exports do not. Read a batch's outcomes with `GET /api/v1/jobs/{jobId}/items`.

### JOB_NOT_AWAITING_CONFIRMATION

<span class="rdm-status rdm-4xx">Status 409</span>

The job is not a preview waiting for confirmation. `details` holds `jobId` and `state`. `POST /api/v1/jobs/{jobId}/confirm` raises it for a job in another state, and `POST /api/v1/jobs/{jobId}/reread` for anything but an import preview waiting for confirmation. It usually means the preview was cancelled, already ran, or the job is not an import or batch preview. Read the job to see its state and decide whether to start the import again.

### JOB_NOT_COMPLETED

<span class="rdm-status rdm-4xx">Status 409</span>

`GET /api/v1/jobs/{jobId}/output` named an export that has not completed, so its file is not served; `details.state` is the export's state. Poll `GET /api/v1/jobs/{jobId}` until the state is `completed`, then fetch the file. A failed or cancelled export has no file: request it again.

### JOB_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No job has the ID in the path. It comes from the job routes (`GET /api/v1/jobs/{jobId}` and its `items`, `rows`, `output` and `events`, and `cancel`, `confirm` and `reread`). It usually means a mistyped or truncated ID. List jobs with `GET /api/v1/jobs` and use an ID it returns.

### JOB_OUTPUT_MISSING

<span class="rdm-status rdm-4xx">Status 410</span>

The export is completed, but its file is no longer in the engine's job file directory. It usually means the file was removed from the server's storage. Request the export again with `POST /api/v1/exports`; tell the operator if it recurs.

### KEY_AMBIGUOUS

<span class="rdm-status rdm-4xx">Not a response status</span>

A row error of an import, never a response status. It is the `error` of a row in `GET /api/v1/jobs/{job_id}/rows` and of its items, and the row is not loaded. Several records hold the row's key, or the combination of keys. Correct the data, or key the source by something unique.

### KEY_NOT_BOUND

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. A source's `key` names an attribute, or a name, that no column of the source fills, so a row's record cannot be found. `path` points at the key. Add a column that fills the key, or change the key.

### KEY_NOT_UNIQUE

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. A source's `key` names an attribute that is not declared unique, so it cannot find one record. Use a unique attribute, set `storedUnique` if the stored values identify one record each, or use `attributeTypeKeys` for several.

### LAST_LOCAL_ADMINISTRATOR

<span class="rdm-status rdm-4xx">Status 409</span>

Local sign-in is off, and the change would remove the way in of the last active person who still signs in with a password. `PATCH /api/v1/users/{userId}` raises it when it clears `localKept` or deactivates that person. Turn local sign-in on, or let another person keep it, then repeat the change.

### LAST_SECURITY_ADMINISTRATOR

<span class="rdm-status rdm-4xx">Status 409</span>

The change would leave no active person holding Security administration at the instance, directly or through a group; clients do not count. It is raised when a role loses its action groups (`PATCH /api/v1/roles/{roleKey}`), a group is deleted or loses members, a grant is deleted, or a person is deactivated or linked away. Nothing is changed. Give the role to another person first.

### LINK_SAME_PERSON

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/users/{userId}/identities` has `fromUserId` equal to the person in the path. Name the other person, the one a provider sign-in created.

### LINK_TARGET_DEACTIVATED

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/users/{userId}/identities` links onto a person who is deactivated, who could not sign in afterwards. Activate that person with `PATCH /api/v1/users/{userId}` and link again.

### LIST_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The consumer API has no list with that key in the contract version asked for. It is raised by `GET /api/consumer/{consumerApi}/v{version}/lists/{listKey}` and by the assistant lookup tools. It usually means a misspelt key or a list that exists in another contract version. Read the API's OpenAPI document (`GET /api/consumer/{consumerApi}/v{version}/openapi.json`) for its list keys.

### LIST_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

An assistant lookup tool was called with `operation` `lists` and no `list`. It appears as the error text of the tool call (`LIST_REQUIRED: lists needs list`) on the MCP endpoint, not as an HTTP status. Call the tool again with the key of the list to read.

### LOCAL_SIGN_IN_OFF

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/users/{userId}/password-reset` was asked for a person who cannot use a password: local sign-in is off and this person does not keep it. Turn local sign-in on, or mark the person as one who keeps it (`localKept` on `PATCH /api/v1/users/{userId}`).

### MAIL_CERTIFICATE_INVALID

<span class="rdm-status rdm-4xx">Status 422</span>

`PUT /api/v1/mail-settings` carries a Microsoft 365 `certificate` the engine cannot read; the message says why and `details.field` is `certificate`. Nothing is saved. Send a certificate the engine can read, or use a client secret.

### MAIL_CREDENTIAL_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

`PUT /api/v1/mail-settings` for Microsoft 365 sent neither a client secret nor a certificate, and a saved one cannot be kept because the tenant, application or token address changed or none was saved. `details.field` is `clientSecret`. Send a client secret or a certificate.

### MAIL_INSECURE_LOGIN

<span class="rdm-status rdm-4xx">Status 422</span>

`PUT /api/v1/mail-settings` has a `username` while `security` is `none`, which would send the login in clear text. Choose TLS or STARTTLS, or remove the user name.

### MAIL_LOGO_TOO_LARGE

<span class="rdm-status rdm-4xx">Status 413</span>

`PUT /api/v1/mail-template/logo` received an image over 512 KB (`details.limit` is the limit in bytes). Send a smaller image; a logo of a few kilobytes is enough for a message.

### MAIL_LOGO_UNSAFE

<span class="rdm-status rdm-4xx">Status 422</span>

`PUT /api/v1/mail-template/logo` received an SVG that holds script, an event handler or an external object, which a mail client could run. Remove them or send a PNG or JPEG.

### MAIL_LOGO_UNSUPPORTED

<span class="rdm-status rdm-4xx">Status 422</span>

`PUT /api/v1/mail-template/logo` received a file that is not a PNG, JPEG or SVG image; the type is read from the content, not from the file name. `details.accepted` lists the media types.

### MAIL_NOT_SET_UP

<span class="rdm-status rdm-4xx">Status 409</span>

The request needs mail and none is configured. It is raised by `POST /api/v1/mail-settings/test`, `DELETE /api/v1/mail-settings`, `POST /api/v1/users/{userId}/password-reset` with `send: true` and `PUT /api/v1/me/notification-mail` when it switches mail on. An administrator saves the settings with `PUT /api/v1/mail-settings`, then the request is repeated.

### MAIL_PASSWORD_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

`PUT /api/v1/mail-settings` sets a `username` without a password, or changes the SMTP host or port without sending the password again; a saved password is never carried to another server. `details.field` is `password` in the second case. Send the password.

### MAIL_SEND_FAILED

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/mail-settings/test` could not send the test message. `details.kind` is `connection`, `tls`, `login`, `recipient`, `sender` or `rejected`, and `details.reason` repeats the message. It usually means a wrong host, port, security mode or credentials, or a server that refuses the sender or recipient. Correct the settings with `PUT /api/v1/mail-settings` and test again.

### MAIL_TEMPLATE_CONTENT_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

The e-mail template of `PUT /api/v1/mail-template` or `POST /api/v1/mail-template/preview` does not hold `{{content}}` exactly once (`details.count` says how often it does). `{{content}}` is where each message's own text goes, so put it in once.

### MAIL_TEMPLATE_NOT_SAVED

<span class="rdm-status rdm-4xx">Status 409</span>

`DELETE /api/v1/mail-template/logo` was called while no e-mail template is saved, so there is no logo to remove. Nothing to do.

### MAIL_TEMPLATE_TOO_LONG

<span class="rdm-status rdm-4xx">Status 422</span>

The e-mail template's Markdown is longer than 20,000 characters (`details.limit`). Shorten it.

### MAIL_TEMPLATE_UNKNOWN_PLACEHOLDER

<span class="rdm-status rdm-4xx">Status 422</span>

The e-mail template holds a `{{name}}` that is not a placeholder (`details.placeholder`; `details.known` lists the ones that are). Correct the name or remove it.

### MAPPING_BINDING_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The relation type, from type and to type of a mapping read are not a binding of the model in this context. It is raised by `GET /api/v1/workspaces/{workspaceKey}/mapping-coverage` and `.../mapping-targets`. Send the binding the mapping view is configured with, as the model's `objectTypeRelations` list it.

### MAPPING_CANDIDATE_TYPE_MISMATCH

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/workspaces/{workspaceKey}/mapping-candidates` asked for an `objectTypeKey` that is not the target type of the mapping view. Send the view's target type.

### MAPPING_ENDPOINT_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

`PUT /api/v1/workspaces/{workspaceKey}/mappings` names a source or target record that does not exist in the workspace, or, with a change set, is not in the change set or is of another type. It usually comes from a record that was deleted or a stale ID. Read the mapping coverage again and send existing IDs.

### MAPPING_ENDPOINT_TYPE_MISMATCH

<span class="rdm-status rdm-4xx">Status 422</span>

`PUT /api/v1/workspaces/{workspaceKey}/mappings` names a live record whose object type is not the one the binding expects at that end. Send records of the binding's from and to types.

### MAPPING_PARENT_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The `parentObjectId` of a mapping read does not exist in the selected context. It is raised by `GET /api/v1/workspaces/{workspaceKey}/mapping-coverage` and `POST /api/v1/workspaces/{workspaceKey}/mapping-proposals`. Send the ID of a record that exists in that workspace, change set or publication.

### MAPPING_PARENT_SCOPE_MISMATCH

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/workspaces/{workspaceKey}/mapping-coverage` has a `parentObjectId` whose type cannot be the direct parent of the view's source records. Send a record of a type that contains the source type, or leave `parentObjectId` out.

### MAPPING_PROPOSED_NEEDS_CHANGE_SET

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/workspaces/{workspaceKey}/mapping-coverage` has `proposed=true` without `changeSetId`. Proposals exist only in a change set; send the change set's ID.

### MAPPING_SET_CHANGED

<span class="rdm-status rdm-4xx">Not a response status</span>

A migration's item code, never a response status. A relationship set that a change set changed was changed in live data too since the change set's base, while the change set is moved onto another release. It is a `refused` item; the job cannot be confirmed. Settle the set in one place and preview again.

### MAPPING_SOURCE_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

`GET /api/v1/workspaces/{workspaceKey}/mapping-targets` has a `sourceObjectId` that is not a record of the view's source type in the selected context. Send a source ID from the mapping coverage.

### MAPPING_VERSION_CONFLICT

<span class="rdm-status rdm-4xx">Status 409</span>

`GET /api/v1/workspaces/{workspaceKey}/mapping-targets` raises it when the `mappingVersion` sent is stale: the targets of the mapping source changed since the client read them, and `details.mappingVersion` is the current version. It is a refused read, not a stale write (a stale `PUT .../mappings` is `VERSION_CONFLICT`). Read the coverage again for the current version and read the targets again.

### MAPPING_VIEW_BINDING_MISMATCH

<span class="rdm-status rdm-4xx">Status 422</span>

The binding and direction of a mapping read are a real binding but not the one the selected mapping view uses. It is raised by `GET /api/v1/workspaces/{workspaceKey}/mapping-coverage` and `.../mapping-targets`. Send the view's own `relationTypeKey`, `fromObjectTypeKey`, `toObjectTypeKey` and `direction`.

### MAPPING_VIEW_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The `applicationKey` and `viewKey` do not name a mapping view of the model in this context. It comes from the mapping reads and from `POST /api/v1/workspaces/{workspaceKey}/mapping-proposals`. It usually means a misspelt key, or a view that exists only in another release. Read the model's applications and send the key of a mapping view.

### MAPPING_VIEW_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/workspaces/{workspace_key}/mapping-targets` named only one of `applicationKey` and `viewKey`. The two identify a view together, so a request sends both or neither; without them the read uses the default grid. Send both parameters, or drop the one that is alone.

### MATCH_AMBIGUOUS

<span class="rdm-status rdm-4xx">Not a response status</span>

A reason of a move, never a response status. Several records of the target match the record by the mapping's `match`; `details` holds `count` and `candidates`. The row is not moved (`notMoved`). Name a more exact match.

### MESSAGE_BEING_SENT

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/mail-outbox/{message_id}/stop` found the message held by a sender that is delivering it at this moment. The message is still waiting, but stopping it now would race the delivery. Send the request again after a short while; by then the message is either sent or released.

### MESSAGE_NOT_WAITING

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/mail-outbox/{message_id}/stop` named a message that is no longer waiting: it was already sent or has already failed. The message text says which. There is nothing left to stop; read the message in `GET /api/v1/mail-outbox` to see its final state.

### MIGRATION_FAILED

<span class="rdm-status rdm-4xx">Not a response status</span>

A confirmed migration, or the move of a change set onto another release, failed unexpectedly while the background worker ran it. It appears in the `error` of the job (`GET /api/v1/jobs/{job_id}`), not as the status of a request. Nothing changed: the workspace or change set keeps its release and its content. `details` holds `correlationId` and `workspaceKey` (or `changeSetId` for a change set). Preview the migration again; if it fails again, give the correlation ID to the operator.

### MIGRATION_HAS_REFUSALS

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/jobs/{job_id}/confirm` on a migration whose preview refused some items, so the migration cannot be applied. `details.refused` is the number of refused items. The job stays waiting. Read the preview's rows at `GET /api/v1/jobs/{job_id}/rows`, fix the data (or the type mappings), and start a new migration preview.

### MIGRATION_LOSS_NOT_ACCEPTED

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/jobs/{job_id}/confirm` on a migration whose preview removes items, sent without `acceptLoss: true`. `details.loss` is the number of items the migration removes. The job stays waiting. Review the listed items, then confirm again with `acceptLoss: true` if the removal is intended.

### MIGRATION_REVIEW_STALE

<span class="rdm-status rdm-4xx">Status 409</span>

What the preview read is no longer what the migration (or the move of a change set) would run on, so nothing was migrated. It usually means the workspace was written to, its release changed, or the change set changed or was published or discarded after the preview. On `POST /api/v1/jobs/{job_id}/confirm` the job stays waiting; `details` names the reviewed and current versions (`reviewedVersion` and `currentVersion`, `reviewedFeedPosition` and `currentFeedPosition`; for a change set also its versions and active publication). When the data changed between confirmation and execution, the same code appears in the job's `error` with `reviewed` and `now` counts. Preview the migration again and confirm the new preview.

### MIGRATION_TARGET_IS_CURRENT

<span class="rdm-status rdm-4xx">Status 422</span>

The migration names the release the workspace already runs, or, for a change set, the release the change set is already pinned to, so there is nothing to migrate. It comes from `POST /api/v1/workspaces/{workspace_key}/model/migrations` and `POST /api/v1/change-sets/{change_set_id}/model-migrations`. `details` holds `releaseId` and `workspaceKey` or `changeSetId`. Choose another target release.

### MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/workspaces/{workspace_key}/model/migrations` named a `changeSetId` together with a `targetReleaseId` other than the release the change set works under. Such a migration publishes the change set, so the workspace moves to the change set's release. `details` holds `changeSetId`, `changeSetReleaseId` and `releaseId`. Leave `targetReleaseId` out, or send the change set's release.

### MIGRATION_TARGET_NOT_WORKSPACE_RELEASE

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/change-sets/{change_set_id}/model-migrations` named a `targetReleaseId` other than the release the change set's workspace runs. A change set is moved onto its workspace's release only. `details` holds `workspaceKey`, `workspaceReleaseId` and `releaseId`. Leave `targetReleaseId` out, or send the workspace's release.

### MISSING_DELETE_NEEDS_CHANGE_SET

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/imports` uses an import profile whose source deletes the records missing from the file (`missing: delete`), but the request loads into live data. Only a load into a change set may delete. Name a change set in the request, or change the source's `missing` setting to report in the profile.

### MISSING_RECORD_KEY

<span class="rdm-status rdm-4xx">Not a response status</span>

The key that identifies the record to update has no value. In an import it is a row error: the row's key column is empty, and `details.column` names it; the row appears in the job's rows (`GET /api/v1/jobs/{job_id}/rows`), and the profile can choose to skip such rows instead of refusing them. In `POST /api/v1/batches` an upsert item has no value for its key attribute; `details` holds `pointer` and `attributeTypeKey`, and the item is `rejected`. Fill in the key value, or remove the row or item.

### MISSING_REQUIRED_ATTRIBUTES

<span class="rdm-status rdm-4xx">Status 422</span>

A record was written without a value for one or more attributes its object type requires, or with an empty one. `details.attributeTypeKeys` lists them. It usually comes from a create (`POST /api/v1/objects`) that leaves out a required field, or from an edit that clears one. Send the missing values. In a batch the item is `rejected` with `pointer` `/attributes`.

### MISSING_REQUIRED_RELATION

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a change set's whole-graph check, never a response status. It is an error in the `diagnostics` of `POST /api/v1/change-sets/{change_set_id}/validation`, in the `details` of `CHANGE_SET_INVALID` when submitting is refused, and in the diagnostics that refuse a publication or a migration of the change set. A record lacks a relationship its type requires; `details` holds `objectId` and `relationTypeKey`. Relate the record, or remove the requirement from the model.

### MISSING_REQUIRED_RELATIONS

<span class="rdm-status rdm-4xx">Status 422</span>

A record would exist without a relationship its type requires. A new record must bring each required incoming relationship (other than its parent) as an initial relation, and a record whose type changes in a restructuring must still have them. `details.relationTypeKeys` lists the missing relation types; for a type change `details.objectId` names the record. Send the missing relations with the record, or create them first.

### MODEL_CHANGED

<span class="rdm-status rdm-4xx">Not a response status</span>

The reason of a suspended subscription, never a response status. It is `suspension.reason` of a subscription, with `details` that depend on it. A model release the workspace activated no longer declares the consumer API, an event or a filter parameter it names; `details.errors` lists what. Edit the subscription, then resume it.

### MODEL_DRAFT_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The model draft ID in a `/api/v1/model-drafts/{draft_id}` route does not exist. It usually comes from a mistyped ID or a draft that was deleted. List the drafts with `GET /api/v1/model-drafts` and use an ID from there.

### MODEL_ELEMENT_NOT_IN_EVERY_MODEL

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/objects` read several workspaces together (repeated `workspaceKey`) and named an application or object type that only some of those workspaces' models contain. `details.element` holds the `kind` and `key`, and `details.workspaces` lists the workspaces that lack it. Name only the workspaces whose models hold the element, or read the workspaces one by one.

### MODEL_HASH_CHANGED

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/model-releases/{release_id}/raising` with `confirm: true` carried an `expectedModelHash` that is no longer the release's hash, so the release changed after the preview. Nothing was raised. `details` holds `releaseId`, `expectedModelHash` and `currentModelHash`. Preview the raising again and confirm with the new hash.

### MODEL_MAPPING_EXISTS

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/model-mappings` used a `key` that another model mapping already has. Keys are unique. Choose another key, or read the existing mapping with `GET /api/v1/model-mappings/{key}`.

### MODEL_MAPPING_MODEL_MISMATCH

<span class="rdm-status rdm-4xx">Status 422</span>

The mapping is between two models, and a workspace named in the request runs a release of a different model (for example when reading a mapping against a workspace, starting its inference, or sending a move). `details` holds the mapping's `mappingSourceModelKey` and `mappingTargetModelKey`, the workspace's model keys `sourceModelKey` and `targetModelKey`, and `workspaceKey`. It usually means a workspace was moved to another model after the mapping was made. Use a mapping made for the models the two workspaces run now.

### MODEL_MAPPING_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No model mapping has the key in the route or request (`/api/v1/model-mappings/{key}`, or the mapping named by a move). It usually comes from a mistyped key or a deleted mapping. List the mappings with `GET /api/v1/model-mappings`.

### MODEL_MIGRATION_REQUIRED

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/workspaces/{workspace_key}/model/activation` was refused because the workspace's data does not fit the candidate release: the release removes or changes something the data uses. `details` is a list of diagnostics, each with `severity`, `code`, `path`, `message` and sometimes `count`. Nothing was activated. Migrate the workspace to the release with `POST /api/v1/workspaces/{workspace_key}/model/migrations`.

### MODEL_REGISTRY_REFRESH_FAILED

<span class="rdm-status rdm-5xx">Status 503</span>

`POST /api/v1/workspaces/{workspace_key}/model/activation` activated the release and committed it, but the answering process could not load the new release. `details` holds `workspaceKey`, `releaseId` and `version`. The activation is saved, so do not repeat it. Read the workspace again after a moment, and tell the operator if requests to it keep failing.

### MODEL_REGISTRY_UNAVAILABLE

<span class="rdm-status rdm-5xx">Status 503</span>

The engine cannot serve the model the request needs. It answers this for every operation while its startup could not prepare the database, and for a workspace whose model release this version of the engine cannot read or that runs no installed release (`details.workspaceKey` then names the workspace). It usually follows an upgrade or a damaged database. Retrying does not help; tell the operator.

### MODEL_RELEASE_CHANGED

<span class="rdm-status rdm-4xx">Status 409</span>

The workspace, or the change set, the request works on runs another model release than the request was built on or read under, so nothing was saved or answered. It happens when a release was activated or a change set moved while the request was being prepared, when the `X-Expected-Model-Release-Id` header names an older release, or while a read straddled the switch. `details` holds `workspaceKey`, `currentReleaseId` and `expectedReleaseId` or `resolvedReleaseId` (and `changeSetId` for a change set). Reload the model and send the request again. The same code appears on `POST /api/v1/jobs/{job_id}/confirm` for an import, batch or move whose release changed since the preview, and in a job's `error` when it changed while the job waited.

### MODEL_RELEASE_IN_USE

<span class="rdm-status rdm-4xx">Status 409</span>

`DELETE /api/v1/model-releases/{release_id}` named a release something still refers to. `details.blockedBy` gives the first reason: `running` (a workspace runs it), `history` (records, change sets, publications or jobs refer to it), `importProfile` or `mapping`. Retire the release instead with `PATCH /api/v1/model-releases/{release_id}`.

### MODEL_RELEASE_IS_DEFAULT

<span class="rdm-status rdm-4xx">Status 409</span>

`PATCH /api/v1/model-releases/{release_id}` tried to retire the release the default workspace runs. New workspaces start on it unless another release is named. `details.releaseId` names it. Make another workspace the default, or move the default workspace to another release, then retire this one.

### MODEL_RELEASE_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No installed model release has the ID the request names. Releases are listed by `GET /api/v1/model-releases`. Check that the ID comes from this instance: IDs of another instance's releases are not known here.

### MODEL_RELEASE_RETIRED

<span class="rdm-status rdm-4xx">Status 409</span>

The request chooses a release that has been retired, and a retired release cannot be chosen for a new workspace, a change set, an activation or the target of a migration (a migration confirmed after the release was retired is refused the same way and changes nothing). `details` names the `releaseId` and the `operation`. Choose a release that is not retired.

### MODEL_REPLACED

<span class="rdm-status rdm-4xx">Not a response status</span>

A note of the migration a model draft states, never a response status. It is in `notes` of `GET /api/v1/model-drafts/{draft_id}/migration` when a step replaced the whole model, so what became what before it is not known. Check the type mappings against the types.

### MOVE_COPY_NOT_PUBLISHED

<span class="rdm-status rdm-4xx">Status 409</span>

The change set being published deletes records a move has copied into another change set, and that copy is not published yet. The deletion waits for the copy. It comes from publishing the change set (`POST /api/v1/change-sets/{change_set_id}/publication`, or an approving decision). `details.changeSetId` names the copy's change set and `details.state` is `open` or `discarded`. Publish the copy's change set first; if it was discarded, this deletion can only be discarded as well.

### MOVE_MAPPING_CHANGED

<span class="rdm-status rdm-4xx">Status 409</span>

The model mapping is at a different version than the move was prepared with. It comes from `POST /api/v1/moves` when `mapping.expectedVersion` is out of date, and from `POST /api/v1/jobs/{job_id}/confirm` when the mapping changed after the dry run. `details` holds `currentVersion` and `expectedVersion`. Read the mapping again and send the move with the current version; a waiting move has to be sent again.

### MOVE_MAPPING_HAS_PROBLEMS

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/moves` named a mapping that does not hold against the releases the two workspaces run: it names things the releases lack or do not allow. No job was created. `details.problems` lists them. Correct or re-point the mapping, then send the move again.

### MOVE_NOTHING_TO_MOVE

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/jobs/{job_id}/confirm` on a move whose dry run would create or update nothing in the target. The job stays waiting. `details.jobId` names it. Change the mapping or the selection and send the move again.

### MOVE_SAME_WORKSPACE

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/moves` named the same workspace as source and target. A move takes records from one workspace into another. `details.path` is `/targetWorkspaceKey`. Name two different workspaces.

### MULTIPLE_TARGETS

<span class="rdm-status rdm-4xx">Status 400</span>

A consumer API read (`/api/consumer/...`) carried more than one `to.` parameter. A read has one target. `details.parameters` lists the `to.` names that were sent, and `details.path` or `details.pointer` points at the second of them. In a batch resolve the refusal is that item's `refused`. Send one `to.` parameter per read.

### MUTUALLY_EXCLUSIVE_CONTEXT

<span class="rdm-status rdm-4xx">Status 422</span>

A read named both `changeSetId` and `publicationId`. A read looks at one context: live data, one change set or one publication. It applies to reads of records, attribute values, relations and mapping views. Send only one of them.

### MUTUALLY_EXCLUSIVE_SCOPE

<span class="rdm-status rdm-4xx">Status 422</span>

A list of records (`GET /api/v1/objects` or `GET /api/v1/objects/{object_type_key}`) sent both `topLevel` and `parentObjectId`. They select opposite scopes: records with no parent, and the children of one record. `details.parameters` lists the two. Send only one.

### NAME_REQUIRED

<span class="rdm-status rdm-4xx">Not a response status</span>

A row would create a record but gives no name, so the row is refused. It appears in the job's rows (`GET /api/v1/jobs/{jobId}/rows`), and `details.column` names the column. Fill the name in the file, or bind a column to the record's name.

### NOTHING_TO_APPLY

<span class="rdm-status rdm-4xx">Status 409</span>

Applying an inference's proposals found no proposal to apply: none is open. It comes from `POST /api/v1/model-drafts/{draft_id}/inference/application` and `POST /api/v1/model-mappings/{key}/inference/application` sent without a list of proposals. Run the inference again, or name the proposals to apply.

### NOTHING_TO_REDO

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/model-drafts/{draft_id}/redo` or `POST /api/v1/model-mappings/{key}/redo` found no undone step to redo. Redo only repeats the latest undone step, and a new change after an undo ends the chance. Read the history of operations to see what can be redone.

### NOTHING_TO_UNDO

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/model-drafts/{draft_id}/undo` or `POST /api/v1/model-mappings/{key}/undo` found no step to undo, or a step named in `step` or `steps` cannot be undone (it was undone already, or it is not an undoable step); then `details.step` names it. Read the history of operations and name a step that can be undone.

### NOT_A_PERSON

<span class="rdm-status rdm-4xx">Status 403</span>

The route works on a signed-in person's own account, and the caller is a client (a token from client credentials). It applies to the caller's sessions and password, second factor and passkeys under `/api/v1/me`, switching notice mail with `PUT /api/v1/me/notification-mail`, and following workspaces. A client has no such settings. Call it with a person's token.

### NOT_A_TABLE_LAYOUT

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import's file, listed in `details.problems` of `IMPORT_FILE_MISMATCH`. A CSV or XLSX file was sent without a profile but is not an export's table layout, which has an `objectTypeKey` or `relationTypeKey` column. Name a profile for any other file.

### NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The thing in the route does not exist for this caller: a mail message in `POST /api/v1/mail-outbox/{message_id}/stop`, a notification in `GET /api/v1/me/notifications/{notification_id}` (an unknown one or another person's), or a workspace in the routes that follow or unfollow one (`/api/v1/me/followed-workspaces/{workspace_key}`). Following also answers it for a workspace that is retired or that the caller may not browse. Check the ID or key.

### NOT_SUBMITTED

<span class="rdm-status rdm-4xx">Status 409</span>

The change set has no open submission for publication. It comes from `DELETE /api/v1/change-sets/{change_set_id}/submission` (withdraw) and `POST /api/v1/change-sets/{change_set_id}/decisions`. It usually means the submission was already withdrawn or decided. Read the change set, and submit it with `POST /api/v1/change-sets/{change_set_id}/submission` if it should be decided.

### NOT_SUPPORTED_BY_SOURCE

<span class="rdm-status rdm-4xx">Status 400</span>

`PATCH /api/v1/consumer-subscriptions/{subscription_id}` set `filters` or `payload` on a subscription to workspace events. Those events have a fixed shape and cannot be filtered or reshaped. `details.pointer` is `/filters` or `/payload`. Leave the field out.

### NO_EMAIL

<span class="rdm-status rdm-4xx">Status 409</span>

The person has no e-mail address, so no mail can be sent to them. It comes from `POST /api/v1/users/{user_id}/password-reset` with `send: true`, and from `PUT /api/v1/me/notification-mail` when switching mail on. The earlier reset link stays as it was. Add an e-mail address to the person (`PATCH /api/v1/users/{user_id}`), or pass the link on yourself.

### NO_IDENTITY_TO_LINK

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/users/{user_id}/identities` named, in `fromUserId`, a person who has no sign-in provider identity to move. It usually means the wrong person was named, or their identities were already linked. Check the person's identities and name the one a provider sign-in created.

### NO_MATCH

<span class="rdm-status rdm-4xx">Status 404</span>

A consumer API cross-reference with `expect=one` (`GET /api/consumer/{api}/v{n}/xref`) found no object for the query terms, or the API defines no matching rules. In `POST .../resolve` the same refusal is the `refused` of that item, not a response status. Change the terms, or read with `expect=any` for a page of candidates.

### NO_PROFILE

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem of an assistant task's check, never a response status. The task's draft has no import profile, so there is nothing to check the workbook against; it is the entry of `profileProblems` in the draft's check. Give the draft a profile.

### NO_WORKING_PROVIDER

<span class="rdm-status rdm-4xx">Status 409</span>

`PATCH /api/v1/sign-in-providers/local` tried to turn local sign-in off before any enabled sign-in provider has signed someone in. Turning it off then could lock everybody out. Sign in once through an enabled provider, then turn local sign-in off.

### OBJECT_ALREADY_EXISTS

<span class="rdm-status rdm-4xx">Status 409</span>

A create sent an `id` that a record already has. Record IDs are unique across the instance, so a record of another workspace also blocks it; then the message names that workspace and `details.workspaceKey` holds it. This is the usual result of loading a file with record IDs, such as an export, into a workspace it did not come from. Read the existing record, or send the create without an `id`. In a batch the item is `rejected` with `pointer` `id`.

### OBJECT_ATTRIBUTE_RULE_VIOLATION

<span class="rdm-status rdm-4xx">Status 422</span>

The record breaks a rule of its object type: at least one of a set of attributes must have a value. `details.rule` is `atLeastOneOf` and `details.attributeTypeKeys` lists the attributes. Send a value for at least one of them.

### OBJECT_HAS_DEPENDANTS

<span class="rdm-status rdm-4xx">Status 409</span>

The record cannot be deleted because other records or relationships depend on it, and the delete did not ask for a cascade. `DELETE /api/v1/objects/{object_type_key}/{object_id}` lists in `details` what would be deleted or removed (`GET …/deletion-impact` reads the same without deleting) (`objectsToDelete`, `relationshipsToRemove`, counts and a `deletionPreviewToken`); a batch delete item carries an `impact`; removing a level in a restructuring lists `objectIds` that still hold records. Review the impact and repeat with `cascade=true` and the preview token, or remove the dependants first.

### OBJECT_ID_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

An assistant's `objects` lookup through the MCP endpoint (`/mcp`) did not pass `objectId`. It is reported as the text of the tool result, not as an HTTP status. Pass the record's `objectId`.

### OBJECT_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No record has the ID in the request in the context being read or written: live data, the named change set or publication. It also covers a parent, a relation endpoint or a selection entry that names a missing record (then `details.path` points into a move's selection). It usually comes from a mistyped ID, a record deleted since, or an ID read from another context. Check the ID and the context.

### OBJECT_TYPE_CHANGED

<span class="rdm-status rdm-4xx">Status 409</span>

The route names an object type, but the record has another type in the context being read or edited. A record keeps its ID when its type changes. `details` holds `objectId`, `objectTypeKey` (the record's type now) and `requestedObjectTypeKey`. Use the route of the record's current type. An edit never changes a type; use a restructuring in a change set for that.

### OBJECT_TYPE_IN_USE

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the stored records), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release removes an object type that stored records still have. Keep the type, or migrate the workspace so its records move to another type; a migration lists the records of a type the target lacks as a `loss`, with this code.

### OBJECT_TYPE_NOT_IN_APPLICATION

<span class="rdm-status rdm-4xx">Status 422</span>

A write in a change set names an application that does not enable the object type. In the change set's validation (`POST /api/v1/change-sets/{change_set_id}/validation`) it is a finding with `details.objectId`. Use an application that has the type, or change the type.

### OBJECT_TYPE_UNCHANGED

<span class="rdm-status rdm-4xx">Status 422</span>

A restructuring in a change set changes a record's type, or the type of all records of a type under a record, to the type they already have (`POST /api/v1/change-sets/{change_set_id}/restructurings` and its `/preview`). `details` holds `objectId` and `objectTypeKey`. Name a different type, or leave the operation out.

### OBJECT_VALIDATION_RULE_VIOLATED

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the stored records), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release declares or changes the `atLeastOneOf` rule of an object type and stored records hold none of the attributes it names. Fill in one of the attributes on those records, or keep the earlier rule.

### OPERATION_BATCH_TOO_LARGE

<span class="rdm-status rdm-4xx">Status 413</span>

A request to change a model draft or a model mapping holds more operations than the instance allows: `POST /api/v1/model-drafts/{draft_id}/operations`, `POST /api/v1/model-mappings/{key}/operations`, or applying an inference's proposals, where a single step is counted. `details` holds `limit` and `received` (and `step` for a proposal). Split the operations over several requests.

### OPERATION_HAS_DEPENDANTS

<span class="rdm-status rdm-4xx">Status 409</span>

An undo of a model draft or model mapping step was refused because later steps depend on what the step created or re-keyed. `details.steps` lists the steps asked for and `details.dependants` the steps that depend on them. Undo the dependants together with the step.

### OPERATION_NOT_OFFERED

<span class="rdm-status rdm-4xx">Status 404</span>

The consumer API exists at the contract version in the path, but its definition does not list the operation the request uses. `details.operation` names it (`objects`, `xref` or `resolve`). It usually means the integrator calls a read the API's author left out of this version. Read `GET /api/consumer/{consumerApi}/v{contractVersion}/openapi.json` to see which operations the API offers, and call one of those.

### PARAMETER_NOT_SUPPORTED

<span class="rdm-status rdm-4xx">Status 400</span>

A consumer read received a parameter the API knows but this read does not apply, for example a list's parent parameter sent to another list, or a definition parameter sent in the query of `POST /api/consumer/{consumerApi}/v{contractVersion}/resolve`, which takes them in its body (`defaults` or an item). `details.parameters` lists the names and `details.path` points at the first. In a batch resolve, a name in `defaults` or in an item is refused the same way, and `details.pointer` replaces `path`. Remove the parameter, or send it where the read takes it.

### PARENT_BOUND_TWICE

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. A source fixes every row's parent with `parent` and also has a column bound as `parent`. Keep one of the two.

### PARENT_CYCLE

<span class="rdm-status rdm-4xx">Status 422</span>

The change moves a record under itself or under one of its own descendants, which would make the hierarchy a loop. It usually comes from `PATCH /api/v1/objects/{objectTypeKey}/{objectId}` with a `parentObjectId` taken from the record's own subtree, and a change set write or a batch item fails the same way. Choose a parent outside the record's subtree. In a batch, `details.pointer` points at the item's parent.

### PARENT_NOT_ALLOWED

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. The model does not let a record of the type stand under a record of the parent's type, so the binding's parent, container or place is refused. `path` points at it. Choose a parent type the model allows.

### PARENT_NOT_FOUND

<span class="rdm-status rdm-4xx">Job result</span>

This code is not a response status. It appears as the reason (`reasons[].code`) on a `notMoved` row of a move job, read with `GET /api/v1/jobs/{jobId}/rows`: the record's parent in the source is neither moved along nor present in the target workspace, so the record cannot be placed. `details.parentId` names the parent; where the mapping fixes the parent by type and name, `details` holds `objectTypeKey`, `value` and `count` instead, and the message says how many matching records the target holds. Move the parent first, or change the mapping so the parent is found or created, then run the move again.

### PARENT_RELATION_SEMANTICS_CHANGED

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the stored relationships), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release no longer treats a relation type as a parent relation of the child type, or changes what makes it one (`parentOf`, `hierarchical`), while stored containment uses it. Keep the parent relation. A migration of a change set refuses the records concerned with this code (the target has no place for the record under its parent).

### PARENT_RELEASED

<span class="rdm-status rdm-4xx">Not a response status</span>

A migration's item code, never a response status. The target release lets the child's type stand at the top, so the containment relationship to its parent goes while the record stays. It is a `loss` item of the relationship; the record becomes a top-level record. Accept the loss when confirming (`acceptLoss: true`).

### PARENT_REMOVED

<span class="rdm-status rdm-4xx">Not a response status</span>

A migration's item code, never a response status. A record is lost because its parent, or an ancestor, is lost: what a lost record contains goes with it. It is a `loss` item of the record. Keep the parent's type in the target release, or accept the loss when confirming (`acceptLoss: true`).

### PARENT_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

The record would have no parent, but its object type is not creatable at the top of the hierarchy. It usually comes from `POST /api/v1/objects` without `parentObjectId`, or from a change that sets the parent to null. Send a `parentObjectId` of a record whose type may contain this type. In a batch, `details.pointer` points at the item's parent.

### PARENT_TYPE_NOT_MAPPED

<span class="rdm-status rdm-4xx">Not a response status</span>

A reason of a move, never a response status. The type of the record's parent is not mapped and the parent is not in the target (`details.parentId`), so the record does not move. It is a reason of a `notMoved` row, and of a parent the mapping's coverage lists.

### PARENT_WRONG_SCOPE

<span class="rdm-status rdm-4xx">Status 422</span>

The named parent belongs to another application or another workspace than the record. Live writes raise it only for an existing parent in the wrong place; a parent that does not exist is `OBJECT_NOT_FOUND`. In a change set write the same code means the parent is not a record of that change set. Use a parent from the same application and workspace; in a change set, make sure the parent exists in it.

### PASSKEY_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The caller has no passkey with the ID in the path. It usually means the ID belongs to another person, was already removed, or is mistyped. List the person's passkeys with `GET /api/v1/me/passkeys` (or `GET /api/v1/users/{userId}/passkeys` as an administrator) and use an ID from the list.

### PASSWORD_INCORRECT

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/me/password` was sent a `currentPassword` that does not match, or the person has no password. The wrong attempt is counted like a wrong sign-in, so repeated attempts end in `429 SIGN_IN_SLOWED`. Send the right current password; a person without one cannot use this operation.

### PASSWORD_REJECTED

<span class="rdm-status rdm-4xx">Status 422</span>

The new password breaks the password rules, so the password was not changed. `details.reason` is `tooShort` (below the instance's minimum length), `tooLong`, `email` (it equals the person's e-mail address) or `common` (it is on the list of very common passwords). Send a new password that meets the rule `message` names.

### PASSWORD_REQUIRED

<span class="rdm-status rdm-4xx">Status 409</span>

The person tries to set up a second factor or a passkey but has no password, as when they sign in only through a provider. Both need a password: `POST /api/v1/me/second-factor` answers this code, and so does the engine's own page for adding a passkey, with the body `{error, code}`. The client cannot fix it; the person signs in with a password account, or an administrator arranges one.

### PERSON_HAS_ACCESS

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/users/{userId}/identities` was asked to move the identities of a person (`fromUserId`) who already holds a password, direct roles or local groups of their own, so they are a real person's and are not joined automatically. `details.held` lists what they hold. Remove those first, or link the other way round, with this person as `fromUserId`.

### PINNED_MODEL_INVALID

<span class="rdm-status rdm-4xx">Status 409</span>

The model release a change set or publication is pinned to is stored but no longer passes validation, so it cannot be used. `details` holds `modelReleaseId` and `diagnostics`. This points at a damaged or hand-changed release rather than a request error. Retrying does not help; tell an administrator, who can install a corrected release.

### PINNED_MODEL_UNAVAILABLE

<span class="rdm-status rdm-4xx">Status 409</span>

The model release the request depends on is not installed. When a change set is created (`POST /api/v1/workspaces/{workspaceKey}/change-sets`) or its model release is changed (`PATCH /api/v1/change-sets/{changeSetId}/model-release`) with a `modelReleaseId` the instance does not have, `details.modelReleaseId` names it. When a publication's own release row is missing, `details.modelReleaseDbId` holds its internal number. Choose an installed release (`GET /api/v1/model-releases`); in the second case tell an administrator.

### PROFILE_CHECK_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No file of the import profile has been checked in the workspace named by `workspaceKey`, so there is no check to read. It usually means the first file has not been uploaded. Upload one with `POST /api/v1/source-files` naming the profile as its owner, wait for the check job to finish, then read `GET /api/v1/import-profiles/{profileKey}/check` again.

### PROOF_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

The operation lowers or widens the person's protection (`DELETE /api/v1/me/passkeys/{passkeyId}`, or adding a passkey on the engine's page) and needs the person to prove who they are again, but the request carried no `proof`. Send the person's password, or a code from their authenticator app or a recovery code, as `proof`. A person with neither a password nor an app is not asked.

### PROPOSAL_ALREADY_APPLIED

<span class="rdm-status rdm-4xx">Status 409</span>

A proposal listed in `proposals` was already applied to the draft or mapping, so applying it again is refused and nothing changes. `details.proposal` names it. It usually comes from sending an old list after an earlier application. Read the inference's proposals again and send only open ones, or omit `proposals` to apply every open proposal. This comes from `POST /api/v1/model-drafts/{draftId}/inference/application` and `POST /api/v1/model-mappings/{key}/inference/application`.

### PROPOSAL_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

A proposal ID in `proposals` is not part of the latest inference of the draft or mapping. `details.proposal` names it. It usually means the inference was run again and its proposals have new IDs, or the ID is mistyped. Read the current inference and use its IDs.

### PROPOSAL_REQUIREMENT_MISSING

<span class="rdm-status rdm-4xx">Status 422</span>

A proposal to apply requires another proposal that is neither applied yet nor sent in the same request. `details.proposal` names the proposal and `details.requirement` the one it needs. Add the required proposal to `proposals`, or apply it first.

### PUBLICATION_CONFLICT

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/change-sets/{changeSetId}/decisions` with `approve` found that the workspace's active publication is no longer the one the client saw in `expectedActivePublicationId`, so nothing was published. `details.activePublicationId` holds the current one. Another change set was published meanwhile. Read the workspace again and decide with the new `expectedActivePublicationId`.

### PUBLICATION_CONTRACT_MISMATCH

<span class="rdm-status rdm-4xx">Status 409</span>

A consumer read with `publication=` named a publication made under a model release that does not declare this consumer API at this contract version. `details.publication` is its ID and `details.contractVersion` the version that release does declare (null when it does not declare the API at all). Read a publication made under the contract version you call, or call the version that publication was made under.

### PUBLICATION_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No publication with this ID exists, or it belongs to another workspace than the one the request reads. It is raised by `GET /api/v1/publications/{publicationId}`, `POST /api/v1/publications/{publicationId}/withdrawal`, reads that name a `publicationId`, `POST /api/v1/moves` (`details.path` is `/sourceAt`), and consumer reads (`publication=`, `details.publication`). A consumer read of `publication=latest` also answers it when the workspace has no current publication. List the workspace's publications and use one of its IDs.

### QUERY_OR_ID_REQUIRED

<span class="rdm-status rdm-4xx">Status 400</span>

An item of `POST /api/consumer/{consumerApi}/v{contractVersion}/resolve` holds both `query` and `id`, or neither. It appears in that item's outcome inside the answer, with `details.pointer` such as `/items/3`; the other items are still resolved. Send exactly one of the two in each item.

### QUERY_REQUIRED

<span class="rdm-status rdm-4xx">Status 400</span>

A consumer cross-reference lookup (`GET /api/consumer/{consumerApi}/v{contractVersion}/xref`) has no search term: `query` is missing or holds only blank values. `details.path` is `/query/query`. In a batch resolve, an item whose `query` is empty gets this refusal in its own outcome. Send at least one non-blank term.

### QUERY_TOO_BROAD

<span class="rdm-status rdm-4xx">Status 400</span>

The terms match more records than a consumer cross-reference scores in one request, whatever other parameters narrow it. `details.limit` is that number (10,000), `details.minimumContainsLength` the shortest term that is matched by contains, and `details.path` is `/query/query`. In a batch resolve it appears in the item's outcome. Use longer or more specific terms.

### QUERY_TRANSLATION_FAILED

<span class="rdm-status rdm-5xx">Status 502</span>

`POST /api/v1/workspaces/{workspaceKey}/query-translations` could not turn the question into filters: the AI provider failed or did not answer, answered in a shape the engine could not read, or used a field or condition the list does not take. Nothing is applied. The call is recorded and `details.callId` is its ID, readable with `GET /api/v1/ai/calls`, with the reason. Ask again, perhaps worded differently, or tell an administrator if it keeps failing.

### QUERY_TRANSLATION_VIEW_UNSUPPORTED

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/workspaces/{workspaceKey}/query-translations` named a view that is not a table view; only table views have filters to build. `details.viewKey` and `details.viewType` name the view and its type. Send the key of a table view of the application.

### READ_ONLY_ATTRIBUTES

<span class="rdm-status rdm-4xx">Status 422</span>

The write sets or clears an attribute that the object type declares read-only, so only the engine may change it. When values are sent, `details.attributeTypeKeys` lists them. Leave those attributes out of the request. In a batch, `details.pointer` points at the item's `attributes`.

### RECORD_CREATED

<span class="rdm-status rdm-4xx">Not a response status</span>

A migration's item code, never a response status. A record that the migration creates, for example when a value is turned into a record of a list (`VALUE_LISTED`). It is a `created` item.

### RECORD_IDS_AS_COUNTERPARTS

<span class="rdm-status rdm-4xx">Not a response status</span>

A notice on an import job's `notices`, not an error. The file names records by IDs that another workspace's records hold, and the import asked for `otherWorkspaceIds: "counterparts"`, so those rows load as this workspace's own records. `details` holds `workspaceKey` and `rows`.

### RECORD_IDS_OF_ANOTHER_WORKSPACE

<span class="rdm-status rdm-4xx">Not a response status</span>

A notice on an import job's `notices`, not an error. Rows of the file name their records by IDs that another workspace's records hold, such as an export of that workspace, and the import did not ask for counterparts, so those rows cannot load here and each is refused. `details` holds `workspaceKey` and `rows`. Send the file with `otherWorkspaceIds: "counterparts"` if it is meant to load as this workspace's own data.

### RECORD_NOT_MOVED

<span class="rdm-status rdm-4xx">Not a response status</span>

A reason of a move, never a response status. A record does not move because its parent does not (`details.parentId`), or a relationship does not move because a record at one end does not (`details.objectId`); it cascades level by level. It is a reason of a `notMoved` row. Settle the first record that does not move.

### RECORD_RECLASSIFIED

<span class="rdm-status rdm-4xx">Not a response status</span>

A migration's item code, never a response status. A record whose type, application or parent changes under the target release. It is a `reclassified` item; the record keeps its ID.

### REFERENCE_AMBIGUOUS

<span class="rdm-status rdm-4xx">Not a response status</span>

A row error of an import, never a response status. It is the `error` of a row in `GET /api/v1/jobs/{job_id}/rows` and of its items, and the row is not loaded. A related record's cell matches several records (`details` holds `column` and `count`). Name which one with `matchBy`.

### REFERENCE_CYCLE

<span class="rdm-status rdm-4xx">Not a response status</span>

A row error of an import, never a response status. It is the `error` of a row in `GET /api/v1/jobs/{job_id}/rows` and of its items, and the row is not loaded. The row's parent leads back to the row through other rows of the file. Break the cycle.

### REFERENCE_NOT_FOUND

<span class="rdm-status rdm-4xx">Not a response status</span>

A reference in a batch or an import row names a record the context does not hold, so that item or row is rejected. It appears in the item's `error` in a batch's results (`GET /api/v1/jobs/{jobId}/items`) and as a row error of an import, not as the status of the whole request. `details.pointer` locates the reference and `details.id` is the ID. When the ID is a record of another workspace, `details.workspaceKey` names that workspace and the message says its counterpart has to be loaded first. In an import it also means a row would need a new record but the sheet has no place for one. Correct the ID, or load the file that creates the record first.

### REFERENCE_TYPE_MISMATCH

<span class="rdm-status rdm-4xx">Not a response status</span>

A reference in a batch item names a record of another object type than the item expects. It appears in that item's `error` in a batch's results, not as the status of the whole request. `details` holds `pointer`, `id`, `objectTypeKey` and `applicationKey` of the record found. Reference a record of the expected type.

### REFUSED

<span class="rdm-status rdm-4xx">Not a response status</span>

The code under which a dry run of items counts a refused item that carries no code of its own. Read the item's message in the outcome for why. It is never a response status.

### RELATION_ALREADY_EXISTS

<span class="rdm-status rdm-4xx">Not a response status</span>

A restructuring that changes a record's type tried to bring back a relationship under its former ID, and a relationship with that ID is already in the change set. `details.relationId` names it. It appears as a refusal of the plan in `POST /api/v1/change-sets/{changeSetId}/restructurings/preview` and as `details.refusals` of the apply. Preview the restructuring again: it plans from the change set as it stands now.

### RELATION_ANCESTOR_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

The relation type is limited to one related record per ancestor of a given type, and the record at the `to` end has no ancestor of that type, so no scope exists for it. It usually comes from `POST /api/v1/relations` or a relation write in a change set with a record that sits outside every such ancestor. Relate a record that sits under an ancestor of the type the message names.

### RELATION_ATTRIBUTE_IN_USE

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the stored relationships), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release removes an attribute from a relation type's pair of object types while stored relationships hold values for it. Keep the attribute on the pair; a migration lists those values as a `loss`, with this code.

### RELATION_ATTRIBUTE_VALUE_TYPE_CHANGED

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the stored relationships), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release changes the value type of an attribute that stored relationships hold values for. Keep the value type, or migrate the workspace so the values are converted.

### RELATION_BATCH_REFUSED

<span class="rdm-status rdm-4xx">Status 409 or 422</span>

A write that sets values on several relationships, `POST /api/v1/relations/batch` or an apply of `POST /api/v1/relations/grid-change`, was refused whole, and nothing was written. `details.items` names each item that failed: `index`, `relationId` (`null` for a pair to link), `fromObjectId` and `toObjectId` where the relationship was found, `code`, `message` and the item's own `details`. The status is 409 when any item had a stale version and 422 otherwise. It usually means a relationship changed since it was read, or a value is invalid. Read the stale relationships again, correct or drop the items named, and send the rest.

### RELATION_CANDIDATE_REFUSED

<span class="rdm-status rdm-4xx">Status 422</span>

The model limits which records may stand at one end of this relationship, and the record does not meet those criteria; a relationship already held is kept, only added ones are checked. `details` holds `relationTypeKey`, `end` (`from` or `to`), `objectId` and `criteria`, the path of the criteria in the model. Choose a record that meets the criteria, or ask an administrator to change them.

### RELATION_CARDINALITY_VIOLATED

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the records that hold more than one relationship), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release narrows a relation type's cardinality so that an end holds at most one, and stored records already hold several. Remove the surplus relationships, or keep the earlier cardinality.

### RELATION_CARDINALITY_VIOLATION

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a change set's whole-graph check, never a response status. It is an error in the `diagnostics` of `POST /api/v1/change-sets/{change_set_id}/validation`, in the `details` of `CHANGE_SET_INVALID` when submitting is refused, and in the diagnostics that refuse a publication or a migration of the change set. A relationship exceeds the cardinality of its type at the source or the target end, where an end may hold one; `details.relationId` names it. Remove the surplus relationship.

### RELATION_CREATED

<span class="rdm-status rdm-4xx">Not a response status</span>

A migration's item code, never a response status. A relationship that the migration creates, for example between a record and a record made from a list value. It is a `created` item.

### RELATION_ENDPOINT_MISSING

<span class="rdm-status rdm-4xx">Status 422</span>

A relationship names a record at one end that does not exist, for example in `POST /api/v1/relations` or in `initialRelations` of a new record. The message names the ID. In the answer of `POST /api/v1/change-sets/{changeSetId}/validation` it is reported when a relationship's end is not in the candidate graph. Create the record first, or correct the ID.

### RELATION_END_REMOVED

<span class="rdm-status rdm-4xx">Not a response status</span>

A migration's item code, never a response status. A relationship is lost because a record at one of its ends is lost. It is a `loss` item of the relationship. Keep the record's type in the target release, or accept the loss when confirming (`acceptLoss: true`).

### RELATION_MATRIX_ACTION_NOT_ALLOWED

<span class="rdm-status rdm-4xx">Status 422</span>

The relation matrix view does not offer the action in its cells: `GET /api/v1/workspaces/{workspaceKey}/relation-matrix/containers` needs `create` and `GET /api/v1/workspaces/{workspaceKey}/relation-matrix/link-candidates` needs `link`. `details.viewKey` and `details.action` say which. Use a view that offers it, or do not call the route.

### RELATION_MATRIX_COLUMN_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

A column ID named in `columnIds` or `columnId` is not a record of the matrix's column type in the context read. `details.columnIds` lists the ones that failed and `details.columnObjectTypeKey` the type. It usually means an ID from another view or context, or a deleted record. Take column IDs from the matrix's own pages.

### RELATION_MATRIX_PARENT_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The `parentObjectId` of `GET /api/v1/workspaces/{workspaceKey}/relation-matrix` is not a record in the context the matrix reads (live, a change set or a publication). `details.parentObjectId` names it. Use an ID that exists in that context.

### RELATION_MATRIX_PARENT_SCOPE_MISMATCH

<span class="rdm-status rdm-4xx">Status 422</span>

The record in `parentObjectId` is of a type that cannot contain the matrix's rows according to the model. `details.parentObjectId` and `details.parentObjectTypeKey` name it. Pick a parent of a type that holds the row type.

### RELATION_MATRIX_ROW_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The `rowId` of `GET /api/v1/workspaces/{workspaceKey}/relation-matrix/link-candidates` is not a record of the matrix's row type in the context read. `details.rowId` and `details.rowObjectTypeKey` say what was expected. Use a row ID from the matrix.

### RELATION_MATRIX_STATE_REQUIRES_COLUMNS

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/workspaces/{workspaceKey}/relation-matrix` was sent `state` without `columnIds`; the state filter applies to the columns the request names. `details.path` is `/query/columnIds`. Name the columns with `columnIds`, or drop `state`.

### RELATION_MATRIX_VIEW_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The `applicationKey` and `viewKey` of a relation matrix route do not name a relation matrix view in the model of the context read. `details` repeats both keys. It usually means a mistyped key, a view of another type, or a change set or publication pinned to a release without the view. Read the application's views and use a relation matrix view.

### RELATION_NOT_ALLOWED

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. The model allows no relationship of that type from the row's type to the type the binding names. `path` points at the `relationTypeKey`. Use a relation type the two types are joined by.

### RELATION_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No relationship with this ID exists in the context the request reads or writes (live, a change set or a publication), or one of its ends is outside the workspace. It comes from `GET`, `PATCH` and `DELETE /api/v1/relations/{relationId}` and from relation items of a batch. A relationship created in a change set is not found live until it is published. Check the ID and the context (`changeSetId`, `publicationId` or `workspaceKey`).

### RELATION_NOT_MAPPED

<span class="rdm-status rdm-4xx">Not a response status</span>

A reason of a move, never a response status. The mapping does not carry the relationship's type, so the relationship is not moved. It is a reason of a `notMoved` relationship row; map the relationship type if it should move.

### RELATION_PAIR_IN_USE

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the stored relationships), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release no longer allows a relation type between two object types while stored relationships of that pair exist. Allow the pair again; a migration lists those relationships as a `loss`, with this code.

### RELATION_SET_CLAIM_INCOMPLETE

<span class="rdm-status rdm-4xx">Status 422</span>

A request claimed a relation set's version but sent only half of the claim: `expectedRelationSetVersion` and `relationSetDirection` must be sent together. `details.parameters` lists both names. It applies to `POST /api/v1/relations`, `DELETE /api/v1/relations/{relationId}` and the matching batch items. Send both, or neither.

### RELATION_SET_VERSION_CONFLICT

<span class="rdm-status rdm-4xx">Status 409</span>

The relation set the request claimed with `expectedRelationSetVersion` and `relationSetDirection` has changed since the client read it, so nothing was written. `details` holds `anchorObjectId`, `direction` and `relationSetVersion`, the current version; in a batch `details.pointer` points at the item. Read the set again, apply the change to what it holds now, and send the new version.

### RELATION_TABLE_BINDING_FIXED

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/workspaces/{workspaceKey}/relations` named a relationships table view with `applicationKey` and `viewKey`, and also sent `relationTypeKey`, `fromObjectTypeKey`, `toObjectTypeKey` or `direction`. A table lists its own binding. Leave those parameters out, or leave the view out.

### RELATION_TABLE_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The `applicationKey` and `viewKey` do not name a relationships table view in the model of the context read. It comes from `GET /api/v1/workspaces/{workspaceKey}/relation-grid` and from `POST /api/v1/relations/grid-change`. Use the key of a relationships table view of that application.

### RELATION_TABLE_VIEW_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/workspaces/{workspaceKey}/relations` was sent `sort` or a `filter.<field>.<operator>` parameter without `applicationKey` and `viewKey` naming a relationships table view; the fields they refer to come from that view. Add the view's keys, or remove the sorting and filters.

### RELATION_TARGET_LEFT_BEHIND

<span class="rdm-status rdm-4xx">Not a response status</span>

A reason of a move, never a response status. A relationship names a record that is neither moved along nor in the target (`details.objectId`), so the relationship is not moved, or the record is refused when the mapping says `missing: refuse`. Select the record too, or let the mapping create it.

### RELATION_UNIQUENESS_VIOLATED

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the conflicts between stored relationships), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release declares or changes the scoped uniqueness of a relation type (`uniqueToAncestorTypeKey`, `uniqueWhenToAttributeEquals`) and stored relationships already conflict within the scope. Remove the conflicting relationships, or keep the earlier rule.

### RELATION_WRONG_SCOPE

<span class="rdm-status rdm-4xx">Status 422</span>

The two records of a relationship belong to different workspaces. A relationship, including an entry of `initialRelations`, stays within one workspace. Relate records of the same workspace.

### RELEASE_IDENTITY_CONFLICT

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/model-drafts/{draftId}/installation` found that a release with the draft's key and version is already installed, with different content. Installed releases never change. `details` holds `releaseKey`, `releaseVersion` and `freeVersion`, the next version number not in use. Change the draft's release version (for example to `freeVersion`) and install again.

### RELEASE_NOT_RAISABLE

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/model-releases/{releaseId}/raising` was asked for a release whose schema version this engine already reads as it is, or is later than it reads. Only a release of a schema that has left the supported range can be raised. `details` holds `schemaVersion` and `supportedSchemaVersions`. Use the release as it is, or run an engine version that reads the later schema.

### RELEASE_RAISE_REFUSED

<span class="rdm-status rdm-4xx">Status 422</span>

The release's schema is outside the supported range, but raising it fails: its schema is not a version, it cannot be read, the raised document is invalid, or it would equal another installed release. `details.reason` says which, with `diagnostics` for an invalid document and `collidesWith` (a release ID) for an equal one. Nothing is changed. Fix the cause in the release or use the colliding release instead.

### REQUEST_VALIDATION_ERROR

<span class="rdm-status rdm-4xx">Status 422</span>

The request body, a path value or a query parameter is not valid: a missing field, a value of the wrong type or outside its range, a field the operation does not take, or text with a NUL character. `details` is a list; each item has `loc` (where: `body`, `query` or `path`, then the field) and `msg` (why). Correct the request. The same request is refused again.

### REQUIRED_ATTRIBUTE_MISSING

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the stored records without a value), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release makes an attribute required on an object type and stored records of it have no value. Fill in the value on those records first, or keep the attribute optional.

### REQUIRED_OWNERSHIP_BINDING

<span class="rdm-status rdm-4xx">Status 422</span>

A replacement of a whole relationship set was sent for a binding that is required and one-to-one or one-to-many, so the set cannot be replaced in one step. It is raised by the relation set replacements of batches and by `PUT /api/v1/mappings`. Change such a relationship through the record that owns it, or with single relationship writes.

### REQUIRED_RELATION

<span class="rdm-status rdm-4xx">Status 422</span>

The write would leave a record without a relationship its type requires: it deletes a relationship of a required binding (`DELETE /api/v1/relations/{relationId}`, or in a change set), clears a required relation set, or a set replacement removes one that the record at the other end needs. `details` may hold `objectId` and `relationId` of the affected record and relationship. Relate the record to another one first, or replace instead of delete.

### REQUIRED_RELATION_MISSING

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a model compatibility check, never a response status. It is an error in the `diagnostics` of the `compatibility` of a model release, a draft or a release comparison, with `count` (the stored records without the relationship), and in the `details` of `MODEL_MIGRATION_REQUIRED` when activating the release is refused. The candidate release requires a relation type of an object type and stored records of it have none. Relate those records first, or keep the relationship optional.

### RESOURCE_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

This code appears only in the MCP endpoint (`/mcp`), as the refusal text of the `read_resource` tool, not as an HTTP status. The `uri` has no resource: it does not match the model, application, object type or view address forms, or it names a view the application does not have. Read the resource list and templates the server gives and use one of those addresses.

### RESTRUCTURING_NOT_READY

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/change-sets/{changeSetId}/restructurings` recomputed the plan and it is not `ready`, so nothing was written. `details` holds `status` (`needsInput` or `refused`), `summary` and `refusals`, the first refusals with their `code`, `message` and `objectId`. It usually means inputs are missing or the change set changed after the preview. Run `POST .../restructurings/preview` again, supply the inputs, resolve the refusals, and apply the plan that comes back ready.

### RESTRUCTURING_PLAN_CHANGED

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/change-sets/{changeSetId}/restructurings` recomputes the plan when it is applied, and the plan it got is not the one whose `planDigest` the request carries. It usually means the change set's records or the live data changed between the preview and the apply. Nothing was written. `details.planDigest` holds the digest of the plan as it is now: preview again (`POST /api/v1/change-sets/{changeSetId}/restructurings/preview`), check the plan, and apply with the new digest.

### RESTRUCTURING_TOO_LARGE

<span class="rdm-status rdm-4xx">Status 422</span>

The restructuring would change more than the allowed number of records at once; `details.limit` is that number (500). Both the preview and the apply of a restructuring of a change set refuse it. Choose a smaller part of the hierarchy, for example a lower parent, and restructure in several steps.

### ROLE_IN_USE

<span class="rdm-status rdm-4xx">Status 409</span>

`DELETE /api/v1/roles/{roleKey}` names a custom role that at least one grant still gives; `details.grants` is the number of grants. Delete or change those grants first (`DELETE /api/v1/grants/{grantId}`), then delete the role.

### ROLE_NAME_TAKEN

<span class="rdm-status rdm-4xx">Status 409</span>

Another role already has the name sent to `POST /api/v1/roles` or `PATCH /api/v1/roles/{roleKey}`. The comparison ignores upper and lower case. Send a different name.

### ROLE_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No role has the key the request names: in the path of `GET`, `PATCH` or `DELETE /api/v1/roles/{roleKey}`, in `copiedFrom` of `POST /api/v1/roles`, or in `role` of `POST /api/v1/grants`. It usually comes from a mistyped key or from a role that was deleted. Read the keys from `GET /api/v1/roles`.

### ROLE_PREDEFINED

<span class="rdm-status rdm-4xx">Status 409</span>

`PATCH /api/v1/roles/{roleKey}` or `DELETE /api/v1/roles/{roleKey}` names one of the predefined roles, which cannot be changed or deleted. To get a role with other action groups, create a custom role with `POST /api/v1/roles` and `copiedFrom` set to the predefined role's key, then change the copy.

### ROWS_SKIPPED

<span class="rdm-status rdm-4xx">Not a response status</span>

A finding of a dry run of items, never a response status. Most rows of a source wrote nothing because their key is empty and the source skips such rows; they are not counted as refused. Fill the key column or name a key that the rows carry.

### SECOND_FACTOR_EXISTS

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/me/second-factor` starts setting up an authenticator app for a person who already has a confirmed one. A secret that was started but not confirmed is replaced by a new one and does not cause this. Remove the existing second factor first (`DELETE /api/v1/me/second-factor`) if the person wants to set it up again.

### SECOND_FACTOR_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The request needs an authenticator app the caller does not have in the state it expects. `POST /api/v1/me/second-factor/confirmation` answers it when no secret is waiting to be confirmed (none was started, or it is already confirmed); `POST /api/v1/me/second-factor/recovery-codes` and `DELETE /api/v1/me/second-factor` answer it when no confirmed second factor exists. Check `GET /api/v1/me/second-factor`, and start with `POST /api/v1/me/second-factor` where needed.

### SECOND_FACTOR_REQUIRED

<span class="rdm-status rdm-4xx">Status 409</span>

The instance requires a second factor for people who sign in with a password, and the request would take away the caller's last one. `DELETE /api/v1/me/second-factor` answers it unless the caller has a passkey; `DELETE /api/v1/me/passkeys/{passkeyId}` answers it for the caller's last passkey unless the caller has an authenticator app. Set up the other kind first, or ask a security administrator to remove the second factor or the passkey (`DELETE /api/v1/users/{userId}/passkeys/{passkeyId}`).

### SESSION_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

`DELETE /api/v1/me/sessions/{sessionId}` names a session that is not an open session of the caller. It belongs to another person, it never existed, or it has already ended. List the caller's open sessions with `GET /api/v1/me/sessions`; a session that has ended needs no further sign-out.

### SHEET_NOT_FOUND

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import's file, listed in `details.problems` of `IMPORT_FILE_MISMATCH`. The workbook has no sheet named as the profile's source says; the message lists the sheets it has. Correct `sheet` in the profile, or send the right workbook.

### SIGN_IN_MANAGED

<span class="rdm-status rdm-4xx">Status 403</span>

An administrator manages the sign-in of the caller's account (`signInManaged` is true on `GET /api/v1/me`), so the caller may not change their own credentials or end other sessions. It comes from `POST /api/v1/me/password`, `POST /api/v1/me/second-factor`, `POST /api/v1/me/second-factor/confirmation`, `POST /api/v1/me/second-factor/recovery-codes`, `DELETE /api/v1/me/second-factor`, `PATCH` and `DELETE /api/v1/me/passkeys/{passkeyId}`, the engine's passkey registration, `DELETE /api/v1/me/sessions` and `DELETE /api/v1/me/sessions/{sessionId}` for a session other than the caller's own. Signing out the caller's own session still works. Ask a security administrator to make the change: a reset link, `DELETE /api/v1/users/{userId}/second-factor`, `DELETE /api/v1/users/{userId}/passkeys/{passkeyId}` and `DELETE /api/v1/users/{userId}/sessions` are theirs, and `PATCH /api/v1/users/{userId}` with `signInManaged: false` hands the account back.

### SIGN_IN_PROVIDER_IN_USE

<span class="rdm-status rdm-4xx">Status 409</span>

People have already signed in with this provider, so it cannot be deleted (`DELETE /api/v1/sign-in-providers/{key}`) and its issuer cannot be changed (`PATCH /api/v1/sign-in-providers/{key}`): another issuer's subjects could sign in as those people. Disable the provider with `PATCH` instead of deleting it, or create a new provider for the new issuer.

### SIGN_IN_PROVIDER_KEY_TAKEN

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/sign-in-providers` names a key that another provider has, or one of the reserved keys `local`, `password` and `passkey`. Choose another key.

### SIGN_IN_PROVIDER_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No sign-in provider has the key the request names: in the path of `GET`, `PATCH` or `DELETE /api/v1/sign-in-providers/{key}`, or in `source.provider` of `POST /api/v1/groups`. Read the keys from `GET /api/v1/sign-in-providers`.

### SIGN_IN_PROVIDER_SECRET_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

`PATCH /api/v1/sign-in-providers/{key}` changes the `issuer` without sending `clientSecret`. The saved secret was given to the old provider and is never carried over to another one. `details.field` is `clientSecret`. Send the new provider's `clientSecret` in the same request.

### SIGN_IN_PROVIDER_UNREACHABLE

<span class="rdm-status rdm-4xx">Status 422</span>

The engine read the provider's discovery document (the issuer's `/.well-known/openid-configuration`) when a provider was created or changed, and cannot use it. It checks this when the provider is enabled or its issuer changes, and, when `signOutOfProvider` is on, that the document names an `end_session_endpoint`. `details.reason` is the explanation and `details.kind` is `address` (the address is not https), `unreachable` (not readable, not JSON, or missing endpoints), `issuer` (the document names another issuer than the one sent) or `sign-out` (no sign-out address). Correct the issuer, or fix the provider, and send the request again.

### SIGN_IN_SLOWED

<span class="rdm-status rdm-4xx">Status 429</span>

Too many wrong passwords or codes were counted for this account or from this address, so the engine refuses further attempts for a while. `POST /api/v1/me/password`, `POST /api/v1/me/second-factor/confirmation`, `POST /api/v1/me/second-factor/recovery-codes`, `DELETE /api/v1/me/second-factor` and the proof of the passkey operations answer it; the passkey registration page answers it as `{error, code}`. `details.waitSeconds` is how long to wait before the next try. Do not retry sooner.

### SKIP_NEEDS_KEY

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. A source says `rowsWithoutKey: skip` but has no `key`, so no row can lack one. Add a key, or remove the setting.

### SOURCE_CHANGED

<span class="rdm-status rdm-4xx">Not a response status</span>

A reason of a move, never a response status. With `mode: move`, a record changed in the source after the move read it, so it was copied as read and stays in the source. It is the reason of a `kept` entry in `MoveSourceOutcome`.

### SOURCE_CYCLE

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. The sources reference each other's types in a ring, so none can load first. Break the ring: load one type's records without a reference to the other.

### SOURCE_DOES_NOT_FIT

<span class="rdm-status rdm-4xx">Not a response status</span>

A refusal of a dry run of items, never a response status. The workbook's sheet does not fit the profile's source, so the source was left out; the refusal names the `sheet`, the `objectTypeKey`, the `rows` and an example. Change the source or the file.

### SOURCE_FILE_MISSING

<span class="rdm-status rdm-4xx">Status 410</span>

The stored source file's content is no longer in the engine's job file directory, although the file is still listed. `POST /api/v1/imports` with `sourceFileId` answers it with this status; when the file is read in a background job (profiling a file), it appears as that job's error. It usually means something removed files from the directory. Upload the file again with `POST /api/v1/source-files`; an operator checks the job file directory if it recurs.

### SOURCE_FILE_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No source file with this ID is available to the request: in the path of `GET` or `DELETE /api/v1/source-files/{sourceFileId}` and of the profile reads under it, or in `sourceFileId` of `POST /api/v1/imports`. A model draft or import profile that holds no file answers it for `POST /api/v1/model-drafts/{draftId}/dry-run`, the inference routes of the draft and `POST /api/v1/import-profiles/{profileKey}/check`, which also answers it for the profile's file in the workspace named. A file owned by another draft is not found either. A background job that reads a file deleted in the meantime reports it as the job's error. Upload a file first (`POST /api/v1/source-files`) or use an ID from `GET /api/v1/source-files`.

### SOURCE_FILE_PROFILE_NOT_READY

<span class="rdm-status rdm-4xx">Status 409</span>

The request reads the profile of a source file, or starts work that needs it, and the profile is not stored yet. `details.state` is `queued`, `running`, `failed` or `cancelled` (with the job's `error` when it has one) and `details.jobId` is the profiling job. Reading the sheets, columns or cells, `POST /api/v1/model-drafts/{draftId}/dry-run`, the draft's inference and `POST /api/v1/import-profiles/{profileKey}/check` answer it. Follow the job at `GET /api/v1/jobs/{jobId}` until it completes and send the request again; after `failed` or `cancelled`, upload the file again.

### SOURCE_SHEET_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

The sheet named in the request is not in the source file; `details.sheet` is the name sent. The columns and cells reads under `/api/v1/source-files/{sourceFileId}/profile/sheets/{sheet}` and the draft's list proposal (`POST /api/v1/model-drafts/{draftId}/inference/list`) answer it. Take the sheet names from `GET /api/v1/source-files/{sourceFileId}/profile/sheets`; they are matched exactly.

### SOURCE_WITHOUT_COLUMNS

<span class="rdm-status rdm-4xx">Not a response status</span>

A warning of a model draft's import profile, never a response status. It is an entry of the profile's warnings in a draft step's answer and does not block the step. A source of the profile maps no column yet.

### SOURCE_WITHOUT_KEY

<span class="rdm-status rdm-4xx">Not a response status</span>

A warning of a model draft's import profile, never a response status. It is an entry of the profile's warnings in a draft step's answer and does not block the step. A source has no key, so every row creates a record and loading twice creates them twice. Name a key.

### SUBSCRIPTION_ALREADY_SUSPENDED

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/consumer-subscriptions/{subscriptionId}/suspend` names a subscription that is already suspended; `details.reason` is why it was suspended. Nothing needs to be done for suspension; to deliver again, resume it.

### SUBSCRIPTION_NEEDS_EDIT

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/consumer-subscriptions/{subscriptionId}/resume` checks the subscription as a new one would be checked, and it cannot be served as it is: for example an event or filter the Consumer API no longer declares, a webhook address that is no longer allowed, or a workspace that is not active. `details.errors` lists every finding with its code and a pointer. Change the subscription with `PATCH /api/v1/consumer-subscriptions/{subscriptionId}`, then resume it.

### SUBSCRIPTION_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No subscription has the ID in the path of a `/api/v1/consumer-subscriptions/{subscriptionId}` operation. It usually comes from an ID of a deleted subscription. Read the IDs from `GET /api/v1/consumer-subscriptions`.

### SUBSCRIPTION_NOT_SUSPENDED

<span class="rdm-status rdm-4xx">Status 409</span>

`POST /api/v1/consumer-subscriptions/{subscriptionId}/resume` names a subscription that is not suspended. Only a suspended subscription is resumed; read its `status` first.

### SUSPENDED_BY_USER

<span class="rdm-status rdm-4xx">Not a response status</span>

The reason of a suspended subscription, never a response status. It is `suspension.reason` of a subscription, with `details` that depend on it. It was suspended with `POST /api/v1/consumer-subscriptions/{subscription_id}/suspend`. Resume it when ready.

### TARGET_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

A Consumer API read with a crosswalk target (a `to.` parameter) found the object, but the object has no item of the target's projection that the parameter matches. `details` names the object (`id`, `objectType`), the `parameter` and its `path`. `GET /api/consumer/{consumerApi}/v{contractVersion}/objects/{objectId}` and the XREF read with `expect=one` answer it as a status; in a `POST .../resolve` request the same finding is that item's `not_found` outcome. Check the value of the `to.` parameter, or read without a target.

### TOKEN_INVALID

<span class="rdm-status rdm-4xx">Status 401</span>

The access token is not accepted. `details.reason` is `expired` (the token's time has run out), `revoked` (the client or person is no longer active, or the person's session ended), `audience` (the token is for another API, for example a `consumer` token on a management operation), `unknownKey` (signed with a key the engine no longer accepts), `malformed` (not a bearer token the engine issues) or `signature` (does not verify). Obtain a new token and send the request again; if the reason is `revoked`, the caller must be made active again first.

### TOO_MANY_COLUMNS

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/workspaces/{workspaceKey}/relation-matrix` names more columns in `columnIds` than one read can return; `details.limit` is the limit (20). Send at most that many IDs, or leave `columnIds` out and page through the columns.

### TOO_MANY_PASSKEYS

<span class="rdm-status rdm-4xx">Status 409</span>

The person already has the largest number of passkeys allowed (25), so no further passkey can be registered. The passkey registration page asks `POST /oauth/passkeys/registration/options` and gets this as `{error, code}`. Remove a passkey the person no longer uses (`DELETE /api/v1/me/passkeys/{passkeyId}`) and register again.

### TOO_MANY_RECORDS

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/relations/held` names more records in `objectId` than one read allows; `details.limit` is the limit (500) and `details.parameter` is `objectId`. Send the records in several requests of at most that many.

### TOO_MANY_TERMS

<span class="rdm-status rdm-4xx">Status 400</span>

The Consumer API XREF read (`GET /api/consumer/{consumerApi}/v{contractVersion}/xref`) has more terms in `query` than it accepts. `details.limit` is the limit (100), `details.count` the number sent and `details.path` is `/query/query`. Split the terms over several requests.

### TYPE_CHANGES_NEED_CHANGE_SET

<span class="rdm-status rdm-4xx">Status 422</span>

`GET /api/v1/objects/{objectTypeKey}/{objectId}/parent-candidates` has `includeTypeChanges` without `changeSetId`. A record's type changes only in a change set. `details.parameter` is `includeTypeChanges`. Send `changeSetId` as well, or leave `includeTypeChanges` out.

### TYPE_NOT_IN_APPLICATION

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. The object type exists but is not in the application the source or related record names. `path` points at the `objectTypeKey`. Name the application that holds the type.

### TYPE_NOT_MAPPED

<span class="rdm-status rdm-4xx">Not a response status</span>

A reason of a move, never a response status. The mapping maps no target type for the record's source type, so it does not move. It is a reason of a `notMoved` row; map the type.

### UNKNOWN_APPLICATION

<span class="rdm-status rdm-4xx">Status 404</span>

The application key in the request is not in the model the request reads. `GET /api/v1/applications/{applicationKey}`, a live record write naming an `applicationKey`, and the object reads and relation-matrix reads that take an application answer it as a status. In `details.problems` of `INVALID_IMPORT_PROFILE` the same code marks a profile whose `applicationKey` is not in the model; in a change set the same mistake is `OBJECT_TYPE_NOT_IN_APPLICATION`. Take the keys from `GET /api/v1/applications`, in the model of the workspace you work in.

### UNKNOWN_ATTRIBUTE

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. An `attributeTypeKey` of the profile is not in the model. `path` points at it. Correct the key, or use a release of the model that has the attribute.

### UNKNOWN_ATTRIBUTES

<span class="rdm-status rdm-4xx">Status 422</span>

The request sets, or deletes, an attribute that the record's object type does not have. The message lists the unknown keys. Creating or changing a record, a change-set record write and a restructuring answer it; `details.attributeTypeKeys` and `details.objectTypeKey` are present for a restructuring. In a batch it is that item's rejection in the item outcomes (`GET /api/v1/jobs/{jobId}/items`, or the inline response of `POST /api/v1/batches`) rather than a response status. Check the keys against `GET /api/v1/object-types/{objectTypeKey}`.

### UNKNOWN_ATTRIBUTE_TYPE

<span class="rdm-status rdm-4xx">Status 404</span>

`GET /api/v1/attribute-types/{attributeTypeKey}` names a key the model does not have. Read the keys from `GET /api/v1/attribute-types` of the same model. The same code also appears in the diagnostics a model validation returns, when an object type or relation binding names an attribute type that is not defined; the diagnostic's path points at the reference.

### UNKNOWN_EVENT

<span class="rdm-status rdm-4xx">Status 400</span>

The request names an event that the Consumer API does not declare (for a workspace-event subscription, an event that is not one of the workspace events). `POST` and `PATCH` of `/api/v1/consumer-subscriptions` and `GET /api/consumer/{consumerApi}/v{contractVersion}/events` answer it; `details.events` lists the unknown keys, with `pointer` (subscription) or `path` `/query/event` (feed). The message lists the events that are declared. Resume lists it among the findings of `SUBSCRIPTION_NEEDS_EDIT`.

### UNKNOWN_INCLUDE

<span class="rdm-status rdm-4xx">Status 400</span>

A Consumer API read lists in `include` a related block that the API does not serve on request. `details.include` lists the unknown names, `details.valid` the names this API serves on request (empty when every block is always served) and `details.path` the parameter. Send only names from `details.valid`.

### UNKNOWN_NOTICE_KIND

<span class="rdm-status rdm-4xx">Status 422</span>

`PUT /api/v1/me/notification-mail` names, in `kinds`, a kind of notice that does not exist; `details.kinds` lists them. Nothing was changed. Use the kinds the notification settings list.

### UNKNOWN_OBJECT_TYPE

<span class="rdm-status rdm-4xx">Status 404 or 422</span>

The object type key in the request is not in the model it is read against. A live read or write answers 404, for example `GET /api/v1/object-types/{objectTypeKey}` and `POST /api/v1/objects`. A change set answers 422 (the key is not in the change set's model), as do the change lists `GET /api/v1/change-sets/{changeSetId}/object-changes` (`details.key`), a restructuring (`details.objectTypeKey`) and `withinObjectTypeKey` of `GET /api/v1/objects/{objectTypeKey}/{objectId}/parent-candidates` (`details.objectTypeKeys`). A Consumer API read names its public names instead and answers 400 with `details.publicNames` listing the names it exposes. A type filter of a consumer subscription is answered the same way by `POST` and `PATCH /api/v1/consumer-subscriptions`, with `details.pointer` `/filters/<name>`. A profile or model that refers to an unknown type reports it in `details` of `INVALID_IMPORT_PROFILE` or in the diagnostics of a model validation, and a change set's validation lists it as an error. Take the keys from `GET /api/v1/object-types` of the model in question.

### UNKNOWN_PARAMETER

<span class="rdm-status rdm-4xx">Status 422 or 400</span>

The request has a query parameter the operation does not declare, which usually means a misspelt name such as `pagesize` for `pageSize`. `details.parameters` lists the unknown names. The engine refuses it instead of ignoring it, so a client never gets another answer than it asked for. Remove or correct the parameter. The check comes after the checks of the token and the caller's rights. A filter of a consumer subscription that names no parameter of its consumer API is refused the same way with `400` on `POST` and `PATCH /api/v1/consumer-subscriptions`, and `details.pointer` is `/filters/<name>`.

### UNKNOWN_RELATION_ATTRIBUTES

<span class="rdm-status rdm-4xx">Status 422</span>

The request gives a relationship attributes that the relation's binding does not allow. The message lists the unknown keys. In a batch it is that item's rejection in the item outcomes rather than a response status. Check the binding's attribute types in `GET /api/v1/object-type-relations`.

### UNKNOWN_RELATION_TYPE

<span class="rdm-status rdm-4xx">Status 404 or 422</span>

The relation type key in the request is not in the model it is read against. `GET /api/v1/relation-types/{relationTypeKey}` answers 404; every other request, such as `GET /api/v1/relations/held` or a write that names a relation type, answers 422, including a change set (the key is not in its pinned model). `details.parameter` or `details.path` names the parameter when it is a read. A profile or model that refers to an unknown relation type reports it in `details` of `INVALID_IMPORT_PROFILE` or in the diagnostics of a model validation. Take the keys from `GET /api/v1/relation-types`.

### UNKNOWN_TIME_ZONE

<span class="rdm-status rdm-4xx">Status 422</span>

`PUT /api/v1/me/notification-mail` has a `digest.timeZone` that is not an IANA time zone name; `details.timeZone` is the value sent. Nothing was changed. Send a name such as `Europe/Berlin`.

### UNKNOWN_VALUE_MAP

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem in an import profile, listed in `details.problems` of `INVALID_IMPORT_PROFILE` and in a stored profile's `problems`. A column, or a related record's parent, names a `valueMap` that the profile's `valueMaps` does not define. Define the map or correct the name.

### UNSUPPORTED_FILE_FORMAT

<span class="rdm-status rdm-4xx">Status 422</span>

The file is neither an XLSX workbook nor a CSV file, judged by `format` in the request or else by the file name's suffix; `details.fileName` is the name. `POST /api/v1/source-files` and `POST /api/v1/imports` answer it. A legacy `.xls` workbook is refused, so save it as XLSX; if the name does not say the format, state `format` in the request. `POST /api/v1/imports` also answers it, with `details.format` set to `jsonl`, for a JSON Lines file sent with a profile: such a file holds batch items and is imported without one.

### UNSUPPORTED_PINNED_MODEL_SCHEMA

<span class="rdm-status rdm-4xx">Status 409</span>

The request works against a change set or publication pinned to a model release whose schema version this engine version does not support. `details.modelReleaseId`, `details.schemaVersion` and `details.supportedSchemaVersions` say which. It usually follows an upgrade of the engine past a release made long before. Retrying does not help; tell the operator.

### UNSUPPORTED_SCHEMA_VERSION

<span class="rdm-status rdm-4xx">Status 422</span>

The model release is written in a schema version this version of the engine cannot run in a workspace. `details` holds `releaseId`, `schemaVersion`, `supportedSchemaVersions` and `operation`. It usually means the release was installed by an older or newer engine. Choose a release whose schema is supported; the releases list shows each one's schema version.

### USER_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No person has the ID the request names: in `/api/v1/users/{userId}` and its sub-resources, such as sessions, passkeys and grants, in group member operations, or as the principal of `POST /api/v1/grants`. Read the IDs from `GET /api/v1/users`.

### VALUE_CARRIED

<span class="rdm-status rdm-4xx">Not a response status</span>

A migration's item code, never a response status. A value moves to the target release's attribute without changing its type. It is a `conversion` item with `before` and `after`.

### VALUE_CONVERTED

<span class="rdm-status rdm-4xx">Not a response status</span>

A migration's item code, never a response status. A value is converted to the value type of the attribute that carries it in the target release. It is a `conversion` item with `before` and `after`; it also appears for a relationship's value.

### VALUE_LISTED

<span class="rdm-status rdm-4xx">Not a response status</span>

A migration's item code, never a response status. A value is turned into a record of a list, as the type mapping asks. It is a `listed` item; the record it makes is a `RECORD_CREATED` item.

### VALUE_NOT_CONVERTIBLE

<span class="rdm-status rdm-4xx">Not a response status</span>

A migration's item code, never a response status. A value does not convert to the type of the attribute that would carry it in the target release, so it is lost. It is a `loss` item with `before`; accept the loss when confirming (`acceptLoss: true`), or correct the value first. A move's rows leave a value behind with the same code, in `leftBehind` with the source attribute's `pointer`.

### VALUE_TYPES_NOT_CONVERTIBLE

<span class="rdm-status rdm-4xx">Not a response status</span>

A problem of a model mapping, never a response status. It is an entry of the mapping's `problems`, at its `pointer` on the `source` or `target` side; an operation that would cause it is refused when applied. No value of the source attribute's type converts to the target attribute's type. Map it to an attribute of a type it converts to.

### VERSION_CONFLICT

<span class="rdm-status rdm-4xx">Status 409</span>

The request claims a version (`expectedVersion`) that is no longer the current one: somebody else changed the same thing since it was read. `details.currentVersion` is the current version; for the default workspace, `details.defaultWorkspaceKey` is the current default. Nothing was changed. Read the item again, check whether the change is still wanted, and send it again with the current version.

Publishing a change set (`POST /api/v1/change-sets/{change_set_id}/publication`, or an approving decision) answers it with `details.conflicts` when live data changed under a record or relationship the change set also changed, or collides with what it adds: each conflict has `kind` (`object`, `relation` or `mapping-set`), `id` and a `code` (`VERSION_MISMATCH`, `ID_COLLISION`, `DUPLICATE_EDGE` or `MAPPING_SET_CHANGED`), with the versions or counts compared; at most 20 conflicts of each `code` are listed, and `details.conflictsLeftOut` (present only then) counts the ones left out by code, so a change set with many conflicts answers in a bounded body; `mappingSetConflictCount` counts all the mapping-set conflicts. Nothing is published. Start a new change set from the live data and make the change again.

Every stale write answers it with `details.currentVersion`, the current version: a record, relationship, user, client, group, role, workspace, subscription, mail setting, source file, import profile, AI task, model draft or mapping. A model release answers it when `expectedStatusVersion` is stale, with `details.releaseId`, `status` and `currentStatusVersion` (the release's status counter, which `currentVersion` repeats). Replacing the targets of a mapping source answers it with `details.targetCount`, the first `targets` and `targetsNextCursor`, so the current targets are in hand.

A model draft answers it with `details.expectedVersion` and `details.actualVersion` besides. The operations, undo and redo of a draft also put in `details.operations` the history entries applied since the version you sent (at most 100, with `details.more` set when there are more), so a client can see what changed and decide whether its own step still applies. Read the draft again and send the step with its current version.

### VERSION_MISMATCH

<span class="rdm-status rdm-4xx">Not a response status</span>

A record's or relationship's conflict in the `details.conflicts` of `VERSION_CONFLICT`, never a response status. Publishing a change set found that the record or relationship was changed in live data after the change set's base publication: the item names its `kind` and `id` and the `expectedVersion` and `actualVersion`. Start a new change set from the live data, or reapply the change on top of it. When the change set is moved onto another release the same conflict is the item code `CHANGE_SET_CONFLICT`.

### VERSION_REQUIRED

<span class="rdm-status rdm-4xx">Not a response status</span>

A batch or import item would change something that exists and carries no expected version, and the request did not say `onExisting: "overwrite"`. This is an item's outcome in a batch or import (`GET /api/v1/jobs/{jobId}/items`, or the inline response of `POST /api/v1/batches`), not a response status; `details.pointer` names the missing field (`expectedVersion` or `expectedRelationSetVersion`) and `details.version` or `details.relationSetVersion` is the current version. Send the version you read, or declare `onExisting: "overwrite"` for the whole request.

### VIEW_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

`POST /api/v1/workspaces/{workspaceKey}/query-translations` names an application and view key that the model of the workspace does not have. Take them from `GET /api/v1/applications/{applicationKey}`.

### WORKSPACES_NOT_SERVED

<span class="rdm-status rdm-4xx">Not a response status</span>

A failure of a backup rehearsal, never a response status. It is the `failure.code` of a rehearsal in `GET /api/v1/system/backup-rehearsals`. After a recovery some workspaces would answer `503 MODEL_REGISTRY_UNAVAILABLE` because their model release cannot be served; the message names them and why. Fix those models before relying on the backup.

### WORKSPACE_ACTIVE_PUBLICATION_CONFLICT

<span class="rdm-status rdm-4xx">Status 409</span>

The workspace's active publication is not the one the request expects: another publication was made, or the active one was withdrawn, after the client read it. `POST /api/v1/change-sets/{changeSetId}/publication` (and approving a decision) answers it when `expectedActivePublicationId` differs from the active publication, and `POST /api/v1/publications/{publicationId}/withdrawal` when that publication is no longer the active one. Nothing was changed. Read the workspace's publications (`GET /api/v1/workspaces/{workspaceKey}/publications`), check what changed, and send the request again with the current ID.

### WORKSPACE_ALREADY_EXISTS

<span class="rdm-status rdm-4xx">Status 409</span>

A workspace with this key exists already, active or retired: a retired workspace keeps its key. Choose another key, or delete the other workspace if it is empty and was never published.

### WORKSPACE_CONTEXT_MISMATCH

<span class="rdm-status rdm-4xx">Status 422</span>

The request names a workspace and a change set or publication that do not belong together. A change set or publication belongs to one workspace. `workspaceKey` that is not the one of the `changeSetId` or `publicationId` answers it, with `details.workspaceKey` and `details.contextWorkspaceKey`. Reading records of several workspaces with a change set or publication does too (`details.workspaceKeys`, `details.parameter`). Leave `workspaceKey` out, or send the context's workspace.

### WORKSPACE_GRAPH_INVALID

<span class="rdm-status rdm-4xx">Status 422 or 409</span>

Two different refusals. Publishing a change set (`POST /api/v1/change-sets/{changeSetId}/publication`, or approving it) answers 422 when the change set, merged over the live data, makes the whole workspace invalid; `details` lists the diagnostics, each with `code`, `message` and `details`, at most 20 of each `code`; for each code with more, a last entry with `code` `DIAGNOSTICS_LEFT_OUT` and `details.leftOutCode` and `details.count` says how many were left out. Fix what they name in the change set, or in the live data that changed meanwhile. `DELETE /api/v1/objects/{objectTypeKey}/{objectId}` answers 409 when the record's hierarchy reaches into another workspace; `details` holds `workspaceKey`, `otherWorkspaceKey`, `objectId` and `edge`. Remove the link first, or delete from the workspace that owns the whole hierarchy.

### WORKSPACE_HAS_PUBLICATIONS

<span class="rdm-status rdm-4xx">Status 409</span>

The workspace was published at least once, and a workspace that has publications cannot be deleted, not even when the publications were withdrawn: its history stays. Retire it instead (`PATCH /api/v1/workspaces/{workspace_key}` with `status` `retired`).

### WORKSPACE_HAS_SUBSCRIPTIONS

<span class="rdm-status rdm-4xx">Status 409</span>

The workspace has webhook subscriptions, which belong to the integrations that created them and are never removed by deleting a workspace. Delete the subscriptions first, or retire the workspace, which suspends them.

### WORKSPACE_IS_DEFAULT

<span class="rdm-status rdm-4xx">Status 409</span>

The workspace is the default workspace, which cannot be deleted. Make another workspace the default (`PATCH /api/v1/workspace-runtime-state`), then delete this one.

### WORKSPACE_KEY_REQUIRED

<span class="rdm-status rdm-4xx">Status 422</span>

`POST /api/v1/objects` writes live data, without `changeSetId`, and has no `workspaceKey`. Send `workspaceKey`, or send `changeSetId` to write into a change set.

### WORKSPACE_NOT_EMPTY

<span class="rdm-status rdm-4xx">Status 409</span>

The workspace still has records or change sets. `details.objectCount` and `details.changeSetCount` say how many. Delete its records and discard its change sets first, or retire the workspace to keep them readable.

### WORKSPACE_NOT_FOUND

<span class="rdm-status rdm-4xx">Status 404</span>

No workspace has the key the request names. It usually means a misspelt key, a workspace that was deleted, or a key of another instance. List the workspaces to see the keys.

### WORKSPACE_RETIRED

<span class="rdm-status rdm-4xx">Status 409</span>

The workspace is retired, and the request needs it active: writing to its records, or making it the default workspace. A retired workspace stays readable. Reactivate it with `PATCH /api/v1/workspaces/{workspace_key}` and `status` `active`, or use another workspace.

### WORKSPACE_RUNTIME_STATE_MISSING

<span class="rdm-status rdm-5xx">Status 500</span>

The row that holds the default workspace is missing from the database. The engine's migrations always create it, so the database is damaged. Tell the operator; retrying does not help.

### WRITE_CONSTRAINT_VIOLATED

<span class="rdm-status rdm-4xx">Not a response status</span>

A batch or import item's outcome, never a response status. A batch's items are written together, and when that write meets a database constraint the rules did not foresee, each item is written again alone. The item whose own write meets the constraint is `rejected` with this code and nothing of it is written; `details.pointer` names the item, and the other items are applied. Under `atomic` the batch stops at it and writes nothing. Read the record the item names and send the item again; if the same item is refused again, tell the operator.
