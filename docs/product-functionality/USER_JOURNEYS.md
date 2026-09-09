# User journeys and simple-flow guardrails

These journeys express the shortest product flow that should satisfy a user goal. They are intentionally
more direct than implementation plans. A future change should not add ceremony unless it protects a
named risk in the journey. These steps describe the target flow; the current-channel label records
availability. Concrete data and expected outcomes are in [acceptance scenarios](ACCEPTANCE_SCENARIOS.md).

## J01 — Find and inspect a reference value

**Current channel:** Browser implementation for the default workspace and API for every workspace;
composed-browser validation is pending.

1. Select a workspace by label.
2. Select an application and view.
3. Search, filter or sort using the fields offered by that view.
4. Open a result.
5. Inspect its fields, path, related records and history.
6. Return to the exact list state.

Success means the user never needs a database ID, API knowledge or a second manual search. An empty
relationship section is an empty result, not an error. A failed page or panel can retry without losing
successful content.

Known gap: a non-default workspace is carried by the collection but currently lost by the detail,
history and relationship requests. That browser journey is not available until WP9 repairs the context
handoff.

## J02 — Make one routine live correction

**Current channel:** API; browser completion is 0.6 WP9.

1. Open the live record.
2. Choose Edit.
3. Change the necessary core or typed field.
4. Save against the version originally viewed.
5. See the updated live record and an audit entry.

Guardrails:

- Do not require creating, naming, validating and activating a workspace draft.
- Do not create a workspace revision for the edit.
- If another person changed the record, preserve the user's input and show what must be reviewed before
  an explicit retry.
- Do not split one coherent record edit into avoidable separate screens.

## J03 — Add a valid contained or dependent record

**Current channel:** API; generic browser form exists but the flow is not connected.

1. Start Add from the collection where a root record belongs, or from the parent/relationship where a
   contained or dependent record will be used.
2. Enter core fields and typed values.
3. Select a parent when required.
4. Select any required non-parent target in the same form.
5. Save once.

Success means the record, typed values, containment and required relationship all appear together or
none of them do. Candidate lookup searches the server and stays in the selected workspace.

## J04 — Delete with an impact preview

**Current channel:** API; browser dialog exists but the flow is not connected.

1. Choose Delete on a live record or a record in a design draft.
2. Review the returned children, owned dependants and relationships.
3. Cancel with no change, or explicitly confirm the cascade.
4. See the resulting live state or draft candidate and audit outcome.

Success means independent associated records survive. Live deletion is immediate; draft deletion does
not alter live data until activation. Historical snapshots do not change in either case.

## J05 — Prepare and activate a coordinated design

**Current channel:** API; browser completion is 0.6 WP9.

1. Open the workspace's Drafts area.
2. Choose a clearly labelled source: current live data or a historical snapshot. Empty drafts are
   development/bootstrap support, not the normal creation flow.
   The current-live option is implemented by WP8.1-B; browser controls for choosing it remain WP9 work.
3. Name the draft and make changes using the normal record controls.
4. Validate the complete candidate.
5. Review the source, current live context, model release, changes and validation result.
6. Activate once.
7. Open the new immutable revision and its lineage.

Success means live readers see no staged change before activation and see the complete merged result
afterward. A conflict or invalid graph publishes nothing and preserves the draft.

## J06 — Continue live work while a design draft is open

**Current channel:** Merge and current-live draft creation are available through the SQLite API; the
browser journey is pending.

1. A design draft starts from a private immutable copy of current live content.
2. Routine live edits continue without using the draft.
3. The design team edits other records in the draft.
4. Activation computes only the draft's changes.
5. Untouched live edits are preserved.

If both paths changed the same record, activation stops with a record-specific conflict. It must never
silently overwrite the live edit or delete live-only records.

## J07 — Retire a publication and start reviewed changes from history

**Current channel:** API; browser completion is 0.6 WP9.

1. Open workspace publication history.
2. Choose Retire publication and confirm the named current revision.
3. Observe that no revision is designated as the current publication. Live data and history remain
   readable; this action has not withdrawn live records or made the workspace read-only.
4. Choose a historical revision and create a new design draft from it.
5. Explicitly prepare the intended changes, review, validate and activate the new draft. Selecting an
   older base alone does not undo live content; untouched newer live records are preserved.

This is a workspace-level action. It must not show or update individual “retired objects.” Retiring a
catalogue workspace is a separate administrative action.

## J08 — Create and activate an application-model release

**Current channel:** Browser implementation and API when model mutations are enabled; composed-browser
validation is pending.

1. Open Models and inspect the active/installed releases.
2. Create or import an editable JSON draft.
3. Save and validate it.
4. Review compiled identity, semantic changes and stored-data compatibility.
5. Install it as an immutable inactive release.
6. Activate it using the fresh runtime-state values.

Saving is not installation; installation is not activation. A compatibility or concurrency failure
must not select the candidate. Read-only inspection and export remain available when mutation is
disabled.

## J09 — Maintain a translation

**Current channel:** API through generic records; browser completion is 0.6 WP9 and specialist coverage
is roadmap 0.8.

1. Start Add Translation from a translation group or the translated target.
2. Select the other required context (target or group/language).
3. Enter at least one translated content field and availability.
4. Save once.
5. See the translation linked to both contexts.

The generic flow must not hardcode the three starter target types. A duplicate active target/language
combination is rejected without leaving an incomplete record.

## J10 — Review and replace a mapping

**Current channel:** Roadmap 0.7.

1. Open a model-defined mapping grid.
2. Filter to mapped, unmapped or ambiguous rows.
3. Search server-side for a target.
4. Select a target, clear the mapping or resolve ambiguity.
5. Save the entire selected mapping set once.

The UI must not implement replacement as a visible delete followed by create. A stale mapping shows
the current bounded targets and changes nothing until the user reviews and retries.

## J11 — Exchange data at integration scale

**Current channel:** Roadmap 0.9.

1. Submit a bounded bulk change or an asynchronous import/export job.
2. Preview validation where applicable.
3. Track resumable status and per-item outcomes.
4. Retry safely using idempotency and continuation information.
5. Follow later changes through an ordered feed or retryable webhook.

The implementation must be a first-class service, not a browser or client loop over single-record
calls. No operation relies on an undocumented unlimited page.

## J12 — Recover from an expected operational refusal

**Current channel:** Operator workflow.

1. Observe that readiness is unavailable.
2. Read the concise message identifying the failed operation and sanitized target.
3. Follow the exact safe command or backup/review instruction.
4. Restart and verify readiness after the correction.

The normal operator path must not require interpreting a Python, SQL or framework traceback. The
underlying cause remains available through controlled diagnostics or escalation information.
