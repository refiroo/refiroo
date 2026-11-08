# C11-FIX2 report

All page paths below are relative to `guide/src/content/docs/`. Existing pages were updated; no new pages or pictures were added. No commits or state-changing Git commands were run. No steer file existed at any unit boundary.

## C11-READER2

| Finding | Disposition | Page and change |
| --- | --- | --- |
| 1 | Fixed | `guide/use/arrange-records-in-a-tree.md`, `guide/use/add-a-record.md`, `guide/model/create-a-workspace.md`: create the first top-level record with Add, without a parent, then add its children; explain action and permission requirements. |
| 2 | Not changed | Supplied contributor setup, explicitly excluded by the assignment. No page defect. |
| 3 | Not changed | Supplied consumer credentials, explicitly excluded by the assignment. No page defect. |
| 4 | Fixed | `guide/use/follow-and-cancel-a-job.md`: names Cancel preview for a waiting batch, alongside the existing import/running-job labels. |
| 5 | Fixed | `guide/use/follow-a-workspace.md`, `use/inbox-and-approvals.md`: Notifications/digest opens an active publication; otherwise Publications. The bell uses Publications. Opening marks the notice read and does not restore lost access. |
| 6 | Fixed | `guide/use/open-a-retired-or-unavailable-workspace.md`: names the corrected “Retired: read only.” context band. The retirement guide already explains read-only behavior. |
| 7 | Fixed | `guide/use/load-the-next-version-of-a-workbook.md`: choose the comparison workspace; profile checking and saving use its model. Existing Accept/Ignore and load steps remain correct after the product fix. |
| 8 | Fixed | `guide/use/delete-many-records.md`: Preview again uses current versions for changed-version refusals; review the new dependent-record and relationship impact before confirming. |
| 9 | Fixed | `guide/model/work-on-a-draft-with-others.md`: intervening rename summaries identify old and new names. Existing review/retry procedure remains correct. |
| 10 | Fixed | `guide/use/edit-in-excel-and-import-back.md`: names Update them anyway and explains deliberate overwrite of saved workbook version checks; confines stale-record refusal to the guarded choice. |

## C11-HOST

| Finding | Disposition | Page and change |
| --- | --- | --- |
| 1 | No original page defect; brief corrected | `run/install-with-compose.md` always used `v<version>` and was already right. Removed this wave’s release-specific additions; retained the intended-deployment version placeholder and the reminder that Unreleased changes need a version containing them. A broken tag belongs in release notes. |
| 2 | Fixed | `run/install-with-compose.md`: replaces the hard-coded Docker volume and Alpine tgz with the engine service’s configured job-file mount and the same Python/plain-tar approach used in `run/backup-and-restore.md`. Adds archive listing and expected-empty-directory explanation. |
| 3 | Fixed | `run/https.md`: self-signed localhost certificate, explicit uncommented port/PUBLIC_URL settings, unprivileged-group readability, certificate/key public-hash comparison, trusted curl probe and browser trust/removal instructions. |
| 4 | Fixed | `run/command-line.md`, `integrate/security-model-for-integrators.md`: all ten predefined role keys next to screen names, plus custom-role discovery. Data owner uses owner; CLI grants are instance-wide. |
| 5 | Fixed | `run/sign-in-and-mail-setup.md`: public-origin token extraction into ACCESS_TOKEN with jq, failure handling, Browse check and first empty-workspace creation without a browser, with one-time client setup and cleanup. |
| 6 | Fixed | `run/install-with-compose.md`: Linux/GNU sed remains the main path; gives the BSD/macOS `sed -i ''` alternative next to the substitutions. |
| 7 | Fixed | `run/install-with-compose.md`, `run/command-line.md`: exact no-terminal refusal, exit 2, password-stdin and Compose -T. No person is created on refusal. |
| 8 | Fixed in pages | `run/install-with-compose.md`: names the closed-stdin Compose/buildx error and the scheduled-runner `</dev/null` remedy. This is a tooling behavior observed by the host rehearsal, not an engine defect. |
| 9 | Fixed | `run/backup-and-restore.md`: explicit matching engine image build before file restoration on a fresh host, with expected build progress. |
| 10 | Fixed | `run/https.md`: Caddy validation uses run --rm --no-deps -T instead of requiring a running container; gives Valid configuration as expected output. |
| 11 | Fixed | `run/upgrades.md`: explains that upgrading an older checkout can create assistant-claude. Both it and install-with-compose already included that volume in their kept-volume lists; those were retained. |
| 12 | Fixed | `run/monitoring.md`: management-token probe piped to urllib inside the running engine container, expected readiness metric and 401/403/public-404 meanings. JSON log example now follows JsonFormatter spacing. |
| 13 | Fixed | `run/command-line.md`: removes the obsolete no-argument-parsing claim; generate_key --help and database_upgrade --help print help without generating a key or preparing/migrating the database. |

### Correction to HOST 1

The brief incorrectly claimed that the guide named a broken release tag. The installation page always said `v<version>` and needed no particular replacement release. Following the owner’s correction, the page again names no specific release. This wave’s rehearsal-tag recommendation and broken-tag warning were removed. The independent reminder about Unreleased changes remains; broken-tag details belong in release notes.

## Remaining coverage gaps and released-field sentence

| Item | Disposition | Page and change / evidence |
| --- | --- | --- |
| Matrix Conflict | Fixed | `use/relation-matrices.md`, `guide/use/fill-in-a-relation-matrix.md`: this branch needs already-inconsistent data; normal writes refuse a second counting record under a uniqueness limit. Do not create invalid data just to follow the guide. Several may be valid. |
| Older model language | Fixed | `model/model-language-versions.md`, `guide/model/raise-a-model-language-version.md`: requires an older release already stored, usually retained through upgrade. This version accepts only 0.10 for new/imported drafts. Coordinate every workspace sharing that release and back up before in-place recovery. |
| Released-field “migration (planned for 1.0)” | Page guidance fixed; product defect remains | `guide/model/add-a-record-type-and-fields.md`, `model/json-view.md`, `model/migrations.md`: specialist JSON authoring, save/compare/install, then reviewed migration. `frontend/src/features/model-editor/OperationDialog.tsx:47` still says migration is planned, although the JSON route and migrations exist. Reader evidence: C11-READER2 findings “Incompatible activation correctly refused” and “Workspace migration completed”, plus screenshot 14. The defect is the misleading sentence; the guide does not suggest detaching/recreating fields or bypassing validation. |

## Pictures

Visually inspected existing files; no picture was edited or added.

- `tree-geography-chur.png`: refresh the editable Geography tree with its new **Add Canton** header control visible.
- `tree-modes.png`: refresh the editable Modes tree with **Add Mode** visible.
- `tree-move-dialog.png`: the dialog still illustrates the documented move, but its blurred Geography background also lacks the new Add control; refresh when exact background parity is needed.
- `model-conflict-editor.png`: shows a Required-setting change, not a rename; the rename fix does not invalidate it.
- `import-profile-next-version.png`: shows unresolved column differences and Needs a fix, which remains a legitimate state; the workspace-save fix does not invalidate it.

Reader evidence pictures 01/08/11/13/15 in C11-READER2 are historical defect evidence, not guide/public/screens assets. Do not replace them as though they were current product illustrations. No new screenshot is requested.

## Validation and limits

The source checks used TreeView root creation, inbox routes, retired-band constants, profile workspace propagation, bulk retry versions, draft history, jobs/batches workbook overwrite handling, CLI argument parsing, authorization catalogue and role migrations, model compiler/raising, object/workspace command schemas and routes, Compose files, Dockerfiles and JsonFormatter. The code and the recorded reader/host evidence were used together; this writing wave did not repeat browser journeys, host deployment, Docker operations or application test suites.

The isolated guide build, wording checks and local-link results are recorded below after the final run. Build output is retained only in this wave’s build.log. The private-term list is empty, so its passing check does not verify undisclosed private names.

Final validation: `GUIDE_OUT=_build/C11-FIX2 npm run build` passed, exit 0, 253 pages in 3.46 s. Existing /404 route-priority warning remains. `GUIDE_OUT=_build/C11-FIX2 npm run check:links` passed, 73,485 local links/sources in 253 pages. `npm run check` passed terms and brand. No new server or database process was started.

After the owner’s HOST 1 correction: isolated build passed (253 pages, 3.35 s); terms/brand and local links passed (73,485 links/sources). Existing /404 warning remains.
