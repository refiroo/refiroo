## 2026-11-12T16:10:39+01:00

Finished `guide/src/content/docs/guide/model/shape-a-workbook-on-the-canvas.md`: placed all seven workbook canvas pictures beside the relevant instructions, with captions checked against the PNGs. The refused-row PNG shows the reason and See the rows, but no unmatched-value list, so the caption describes only what is visible. No steering file was present.

## 2026-11-12T16:11:06+01:00

Finished `guide/src/content/docs/guide/model/edit-a-model-on-the-canvas.md`: placed all nine model canvas pictures, covering the board, Add menu, attribute inspector, containment rule, navigation, views, consumer contracts, issues and history. Captions follow the PNGs where their definitions differ: the rule is containment, the consumer tab lists a contract, and the visible whole-model cards are Released. No steering file was present.

## 2026-11-12T16:12:00+01:00

Finished caption review for `administer/` and `guide/administer/`. Corrected `administer/clients.md`, `administer/sign-in.md`, `administer/signing-keys.md`, `guide/administer/create-a-client.md`, `guide/administer/find-who-changed-something.md` and `guide/administer/rotate-signing-keys.md`: the retakes show two active clients, an empty webhooks section, a disabled sign-in provider, one signing key and group activity. Other captions in these sections match their definitions; the roles screenshot still visibly includes Recent activity, despite its narrower definition. No steering file was present.

## 2026-11-12T16:12:42+01:00

Finished the model-release and history caption group: corrected `guide/model/add-a-record-type-and-fields.md`, `create-a-model-draft.md`, `edit-a-workspaces-model.md`, `install-and-activate-a-release.md`, `load-a-workbook-into-a-change-set.md`, `make-a-workspace-the-default.md`, `undo-and-review-the-draft-history.md`, plus `journeys/shape-a-model.md`, `model/releases.md`, `model/the-model-editor.md` and `model/workbook-onboarding.md`. The retakes show current release versions, a contract-version refusal, a workspace draft instead of its overview, and two saved edits instead of a move. Checked the related PNGs; the workbook load counts and progress still match. No steering file was present.

## 2026-11-12T16:13:39+01:00

Finished the steward screenshot group: corrected `guide/use/approve-a-change-set.md`, `change-how-refiroo-looks.md`, `correct-a-record.md`, `fill-in-a-relation-matrix.md`, `find-records.md`, `map-codes-between-systems.md`, `prepare-and-publish-a-change-set.md` and `relate-records.md`, plus `use/appearance-and-devices.md`, `change-sets.md`, `home.md`, `inbox-and-approvals.md`, `records.md`, `workspaces.md` and the webhook image description in `administer/webhooks.md`. Captions now reflect centred dialogs, immediate removal with Undo, mapped code T-0412, the current change-set banner, five themes and the larger Home/inbox lists. Publication 1 and Publication 2 captions were checked against their PNGs and still match, including the Withdrawn label. No steering file was present.

## 2026-11-12T16:14:22+01:00

Finished the remaining caption comparison across `about/`, `examples/`, `journeys/`, `model/`, `run/` and the older model screenshots without screen definitions. Corrected `administer/audit.md`, `guide/administer/find-who-changed-something.md`, `guide/model/review-an-assistants-workbook-design.md`, `guide/use/approve-a-change-set.md` and `run/configure.md` after checking their PNGs. The retakes show different audit entries, a different workbook proposal, the approval list above workspace cards and current container paths. Screens without definitions were checked directly where a caption made a specific claim; no image was renamed or removed. No steering file was present.

## 2026-11-12T16:15:29+01:00

The isolated build passed (259 pages). The first `GUIDE_OUT=_build/SCREENS-CAPTIONS npm run verify` stopped at the term check because a screenshot’s literal workspace name includes a delivery identifier. Corrected that caption in `guide/model/install-and-activate-a-release.md` to say “an example workspace” while retaining the pictured version, compatibility and unconfirmed state; rerunning verification. No steering file was present.

## 2026-11-12T16:16:32+01:00

Completed `guide/_coverage/notes/SCREENS-CAPTIONS/report.md` with every canvas placement and caption, each changed caption’s old and new text, image-description changes and the check results. Final `GUIDE_OUT=_build/SCREENS-CAPTIONS npm run verify` passed all checks: 259 pages, zero uncovered inventory items and 77,212 valid local links/sources. No new screenshots are needed. Existing screenshot references remain intact; definition/PNG differences and the 43 names without definitions are recorded in the report. No steering file was present.

