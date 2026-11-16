# Changelog

All notable changes to this project are documented in this file. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Upgrade script**: the job-files tarball is handed to the user who runs the script (`chown` inside the helper container, then `chmod 600`) and is checked with `tar tzf`; before, a root-owned file made the size listing print `0 B` and the script went on. `filesize` stops the script on a file that cannot be read or is empty. The script prints the checkout's version (`this checkout: engine X`) next to the running one, warns and asks when they are the same (with `--yes` it refuses unless `--force`), stops on an older checkout, and warns in the summary when the engine's version after the upgrade is not the checkout's. `docs/OPERATIONS.md`, Upgrades, names `git fetch --tags && git checkout v<version>` as the step before the script.

## [0.17.2] - 2026-11-15

Internal work after 0.17.1 (one version of each step, helper, component and stylesheet rule; the test
harness's side-by-side runs, lanes and selection by change), the defects found in the code reviews and in a
full read of the large modules, and the release review's findings (R172-F1 to F36). One API change: a write on
an out-of-date version is refused as `409 VERSION_CONFLICT` everywhere (SR3, SR-D4). One migration
(`20261204_01`) drops an unused database role. The release review covers every change since the released
0.17.1; the public `v0.17.1` tag already holds SR1, SR2 and the removal of the example model's names, made
after that release, so they are listed here.

### Fixed

- **R172-F1 (browser tooling)**: internal. `test:changed` follows a feature file's importers in other features (a dialog of one feature opened from another selects that feature's runners and groups); the shell that mounts the features is not followed.
- **R172-F2 (browser tooling)**: internal. A change to the shell's frame files (`AppShell`, `ShellFrame`, `TopBar`, `DataContextBand`) selects every accessibility and visual group.
- **R172-F3 (browser tooling)**: internal. `test:changed` fails, naming them, when a changed `src/` path is in no manifest entry; `backend/tests/browser_seeds.py` selects every runner and other `backend/` paths are listed as a note.
- **R172-F4 (browser tooling)**: internal. A runner's port reservation that is still empty (its owner has not written its process number yet) is held, not deleted and taken; an empty one is taken over only after it has stayed empty for 5 s.
- **R172-F14 (matrix cell dialog)**: on a phone the filter of a filled matrix cell's dialog takes its own width beside the dialog's other controls instead of a full row.
- **R172-F15 (model editor)**: a type in a cycle is no longer listed among its own ancestors in the breadth-first walk unless asked (`startInCycle`).
- **R172-F16 (writes)**: a handler of a refused or stale write that itself fails no longer leaves the person without a message or an unhandled error; the refusal is shown.
- **R172-F17 (permissions)**: a failed first read of a person's permissions is read again on the next use instead of staying failed until a 403.
- **R172-F18 (jobs)**: following another job no longer shows the previous job's read error.
- **R172-F19 (workbook canvas)**: the rule popover of another line takes focus when it opens in place of the previous one.
- **R172-F20 (matrix cell dialog)**: the uniqueness refusal names "the same record" when the refusal does not name the ancestor's type, instead of "under the same , …".
- **R172-F21 (design load, notifications)**: the load table's row reads "237 matched", not "237 matcheds"; the notifications count reads "3 matches" and "1 match", not the reverse.
- **R172-F22 (imports)**: a workbook sheet that declares more columns than its header fills keeps that width on every read, so the columns an import's headings reading or unpivot adds are where the plan put them and no value is lost or read from another column.
- **R172-F23 (change sets)**: an attribute patch or delete in a change set checks the relations into the record against the record as the edit leaves it, as an object update does.
- **R172-F24 (assistant sessions)**: the rule that a session uses only a draft it made or its task holds also holds for a draft named in a body or query (`POST /source-files` with `owner.draftId`, `GET /source-files?draftId=`, `POST /workspaces/from-workbook`, a workspace migration's `draftId`) and for a draft's source file by ID (`403 FORBIDDEN`, or `409 AI_TASK_DRAFT_HELD` for another task's draft); `GET /source-files` lists a session its own drafts' files only.
- **R172-F25 (migrations)**: a refusal without a record stores no ID in a workspace migration and in a change set move, not an empty one.
- **R172-F26 (migrations)**: a relation type mapped onto a type that a mapped relationship was just sent back to (a chain Y; X to Y; W to X) is refused as `DUPLICATE_EDGE` too, instead of the preview failing with `MIGRATION_FAILED`.
- **R172-F27 (jobs)**: a sweep that keeps failing is one outage in the job worker's log and health state; a job that runs between two sweeps no longer ends it and logs a full error again.
- **R172-F28 (assistant)**: a `retry-after` date written `-0000` is read as UTC instead of failing, and a connection that timed out before anything was sent is sent again like a refused one.
- **R172-F9 (notifications)**: the inbox stream sends a notice that commits long after a later one: the lookback is the start of the oldest transaction in flight under the engine's role, taken from the database at each read, not a minute of the application's clock; notices are made at the database's time (`now()`).
- **R172-F29 (frontend)**: internal. A test file FX1 left unformatted is formatted (`RelationTableView.test.tsx`).
- **R172-F30 (guide)**: the captions under the assistant's workbook proposal picture on "Work with an assistant" and "Loading with the assistant" describe the notes on names used twice, which the picture shows, not a Questions section it no longer has.
- **R172-F31 (private-terms check)**: internal. `scripts/check-private-terms.sh` run in a linked worktree reads the main checkout's `.dev/private-terms.txt` instead of skipping the check.
- **R172-F32 (query translation)**: the query-translation prompt, whose example changed when the example model's names were removed (SR1 and SR2 commit), is recorded as `query-translation/3`, so recorded AI calls tell the two prompts apart.
- **R172-F33 (code comments and docs)**: internal. Paths left from before the assistant task's split (`agent.py`) and the frontend's state layer (`features/jobs/ChangeSetLoad.tsx`) name the current modules; ARCHITECTURE's import tiers say what each layer imports, as the code does.
- **R172-F34 (frontend)**: internal. The candidate releases' comment is back above `groupedCandidates` in `ActivateDialog.tsx`.
- **R172-F37 (test harness)**: internal. `python -m tests.affected --help` prints the usage, and a name git does not know as a commit gives one line instead of a traceback.
- **R172-F38 (CI)**: internal. The F9 inbox test's `noqa` sits on the parameter it covers (Ruff failed CI), and Vitest's test timeout is 15 s on CI, whose runners took a 76 ms test past the 5 s default.
- **R172-F35 (record page)**: a record page that finishes loading no longer moves focus to its title while a popover is open, which closed the popover; the preview's Record choice, opened while the record page was still loading, closed at once.
- **R172-F36 (accessibility gate)**: internal. The accessibility scan switches animations and transitions off while it runs, so it never reads a button's colours half way through a 120 ms transition on a loaded machine, and a failure lists the measured ratio and colours.
- **The rule under applied filters runs the full width (SR6)**: on a list's "Applied search" row and a relation matrix's applied filters, the line under the chips stopped where the chips end; it now spans the view. The search box in the bulk relationships and related records dialogs again shows its icon beside the text, at the usual size (an SR5 regression, not released).
- **Proposing from a workbook says "applied" only when it was (SR4)**: the canvas confirmed proposals as applied also when the step came back stale; it now does so only when they were applied, as the model editor does. Cancelling a bulk relationship change no longer sends one more read per remaining batch.
- **A stop pressed again keeps its first time (SR-D3)**: asking a job to stop again no longer moves the time of the first request; eight places overwrote it, the background batch already kept it.
- **Defects from the full read of the large modules (FX2)**: a row an import refuses keeps its key, so with `missing: "delete"` its record no longer gets a delete item; a key cell that fails is a refused row under `rowsWithoutKey: "skip"` (only an empty key cell is skipped), so an import that skipped such rows now reports them; a CSV row shorter than its header and an XLSX file declaring a wrong `<dimension>` are read whole (a value in a column without a heading is still read); a re-read preview keeps `sourceFileId`; a NUL or lone surrogate in a cell, or a match value over 2,000 bytes, refuses its row (`INVALID_CELL`) instead of failing the import; a batch item meeting a database constraint is rejected alone (`WRITE_CONSTRAINT_VIOLATED`); a split relation cell is value-mapped once, non-ASCII digits in a version and unreadable XLSX shapes answer a refusal, not 500. Exports: a carriage return in text survives the round trip (`_x000D_`), so an unchanged file re-imports unchanged; a text over 32,767 characters fails the export with `EXPORT_TEXT_TOO_LONG` naming sheet, record and field; a ";" in a people relation column is written as "," as the matrix does; dates before March 1900 are written as ISO text; a link matrix over 250 value sheets is refused; control characters leave sheet titles; a table past 1M rows continues as filtered sheets; the views' column checks and the grid's 100-argument limit run in PostgreSQL; a CSV export can be cancelled during its COPY. The job worker's hourly sweep failing no longer stops every job (retried after 30 s), and an export failing after its file is written fails after three attempts instead of rerunning every 2 s. Model migrations refuse a relationship mapped onto a type that already links the same two records (`DUPLICATE_EDGE`) and never migrate to a retired release; the restructuring preview locks its change set; patching or deleting a change set's attribute runs the relation rechecks an edit runs; stale-version and graph refusals list at most 20 per code with a count of the rest (`details.conflictsLeftOut`, a closing `DIAGNOSTICS_LEFT_OUT` entry), shown on the change set page as "N more problems are not listed."; deleting releases still in use answers `MODEL_RELEASE_IN_USE`; a change set cannot start in a workspace being retired; a draft migration's landing reports errors other than its own mapping refusal. Consumer API: a live XREF's bound counts only the owner's workspace; `/resolve` refuses a body over its byte limit (`413 BATCH_TOO_LARGE`, `maximumBytes`); list, XREF and resolve each read one snapshot. Events: a failing workspace waits (2 s doubling to 5 min) while the others derive; each webhook sender takes the next subscription as soon as it is free; an engine error in a delivery backs off. The notification stream no longer skips a notice committed late; a message whose header cannot be built fails alone; one person's failing digest no longer stops the others. A profile check compares only with its own workspace's previous file. The assistant: a session reads, lists and changes only its own draft or the draft its task holds (403 otherwise); a turn is recorded when the undo after it fails; inference and the file summary count missing values, drift and parts in PostgreSQL and return the first 50 with the total; the session log is capped at 512 MiB; a long row number, a nested proposal, `put` onto a folder, an empty `AI_AGENT_COMMAND`, a token shorter than the session's time limit, the transcript sweep, moved legacy folders, `sync` on a task list and grants left after expiry are each fixed. Frontend: the canvas line popover takes focus once; a sheet-menu drop places the new card, not an existing one; the tree finds its revealed record again after a reload; a stale model reload no longer overwrites a newer navigation and an unanswered restore no longer blocks navigation; an empty page number no longer jumps to page 1; no-op steps are not saved; a board's saves go out in order; listeners and timers end with their board. The assistant's session network in a container (SR-D6): when the engine container has `NET_ADMIN` (`compose.yml` grants it), the session users reach only the engine and an allow-list proxy for the provider's hosts (`AI_AGENT_ALLOWED_HOSTS` adds hosts); the engine drops the capability before it starts; without the capability the session runs unrestricted, logged once at start and shown by `GET /ai/status` (`assistantNetwork`); a rule that fails to apply stops assistant turns with its cause.
- **Defects from the code reviews (FX1)**: a kept AI request and answer no longer outlive `AI_LOG_CONTENT_DAYS` when no new call is recorded (the call log leaves out content past its days and the worker's hourly pass empties it; recording a call still does); a call to a provider is sent again after a wait (the provider's `retry-after`, else 1 s then 2 s, up to three sends) for both the Claude and the OpenAI-compatible adapter, and never after a timeout; the import profile page and a model release's page read the item again after a stale-version refusal, say it was changed by someone else and no longer refuse every later save; one set of initials for a person everywhere (letters only: Admin reads A, 2nd line reads NL; a name with no letter keeps its first two characters); a relationships table reads its rows again after a stale version by the refused item's code, not its wording; the password reset screen shows the engine's own wording of a wait (a wait of 60 to 89 seconds reads "2 minutes", as on the sign-in screen) and takes its tone from the answer; Home reads where a person approves in one request (`GET /me/action-groups`) instead of one per workspace; an omitted `ai` flag with a send level above the instance's ceiling answers false before anything else is checked; the record tree writes its stored choices after rendering, the journey bar drops its per-task mark once the task is loaded or cancelled, the unknown-parameter check keeps its cache on the route instead of by `id`, and two stale comments are corrected.

### Changed

- **R172-F5 (test harness)**: internal. The reach map check also fails on any app module (the command line tools aside) that is in no entry, so an edit to it selects no test; code that runs only at import (the schemas, constants) is recorded as reached by every test module that starts the application. The map is not yet recorded again.
- **R172-F6, F7 (test harness)**: internal. The two postgres_server tests that call the real `stop()` patch `_USE`, `STARTED_MARK`, `DATA` and `PORT`, so they no longer release the run's registration or touch the shared server.
- **R172-F8 (test harness)**: internal. A seed's template is named per fingerprint (`seed_<name>_<fingerprint>`), so runs with different seed inputs no longer rebuild each other's; a clone is made under the seed's lock; templates of other fingerprints unused for an hour are dropped.
- **R172-F10 (J50 journeys)**: internal. The stand-in assistants' wait on a job's event stream has an overall 120 s deadline and fails naming the job's last state.
- **R172-F11 (test harness)**: internal. A change to `tests/run_ids.py` or `tests/durations.py` selects the whole suite, as `conftest.py` does.
- **R172-F12 (test harness)**: internal. The volume clone wait test no longer depends on volume clones other live runs hold.
- **R172-F13 (test harness)**: internal. A volume clone held by another worker of the same run is waited for as long as it is held; the 30 minute bound stays for another run's clone.
- **One stylesheet rule for each look (SR6)**: the popovers' surface is one `.popover`; a chip's or pill's corner is `--pill-radius` and a hue-coloured chip reads the `[data-hue]` convention; the matrix's applied filters have their own class (`.filter-chip-applied`) beside the toggle chips of lists and logs, which shared one class and a mix of two definitions; `.truncate`, `.list-reset` and `.wrap-row` replace identical blocks; split selectors are merged; a type size that is equal in every theme reads `--text-xs`, `--text-sm` or `--text-md`; z-index values are `--z-*` tokens in today's order; padding, margins and gaps equal to a step read `--space-*`; 39 classes nothing uses are gone from the stylesheets. Nothing looks different in any theme, light or dark, at desktop or phone width.
- **One component for each frontend element (SR5)**: a write with its conflict and error notices (`useGuardedWrite`, `ActionNotices`), the discard question, the activation verdict, job progress, the saved flash, edit in place, undo toasts, the switch, the stale-preview dialog, migration outcome cards, bulk dialog policies, the active/deactivated list page (People, Clients, Groups), the new-workspace fields, the search box, the workspace select and the record picker each exist once, and repeated words ("Untitled change set", "Every workspace", "Sign out everywhere", "Written by hand") have one source. Visible (SR-D2): a record changed while its page was open is a warning titled "Not saved" reading "This <noun> changed while the page was open. It is shown as it is now; review it and choose again." everywhere, the sign-in page and the AI task page included; a release whose activation needs a migration is titled "Activation needs a migration" in every dialog; a field saved in place shows "Saved" for 2.5 s everywhere (the workspace page showed it 4 s); the inbox quotes names as “name”. Cancel or Close on a dialog with unsaved input now asks "Discard your unsaved changes?" in every dialog (before, most Cancel buttons closed without asking, the workspace admin's among them); a prefilled dialog asks only when its values differ. The stale-preview alerts of the move editor and the migration page have their buttons in the footer, as every confirm dialog (same words and buttons); a move's values not carried and a model comparison's changes stack on a phone. Nothing else changes in look or place.
- **One version of each frontend helper and loader (SR4)**: following a job, reading every page, workspace lists, cached reads (the signed-in person, the system's static parts, permissions), error parsing and stale-write recognition, clipboard, stored preferences, numbers and plurals, dates, names of types, relations and fields, newest release first, value coercion, the nearest scrolling ancestor and a type's ancestors each exist once. Visible: numbers, decimals, dates and 12/24-hour times follow the browser's locale everywhere (SR-D1; four pages hard-coded British English); a workspace list longer than one page is complete everywhere; a type the model does not name shows its key (SR-D2) where some pages said "Record" or nothing; the Timeline's relative times read as elsewhere ("yesterday, 17:40", the time of day kept beyond a week); copying in the model editor says the same sentence for every refused write.
- **One stale-version refusal (SR3, SR-D4)**: an API change. A write made on an out-of-date version is refused as `409 VERSION_CONFLICT` with `details.currentVersion` everywhere. The codes `AI_TASK_VERSION_CONFLICT`, `IMPORT_PROFILE_VERSION_CONFLICT` and `MODEL_RELEASE_VERSION_CONFLICT`, and the mapping replacement's `MAPPING_VERSION_CONFLICT`, are replaced by it; the replacement's `details.mappingVersion` is now `currentVersion` (its `targetCount`, `targets` and continuation stay), a release keeps `releaseId`, `status` and `currentStatusVersion`, and a model draft keeps `expectedVersion`, `actualVersion`, `operations` and `more`. `CHANGE_SET_VERSION_CONFLICT`, `RELATION_SET_VERSION_CONFLICT` and the mapping targets read's `MAPPING_VERSION_CONFLICT` are unchanged. The interface recognises the stale write through one `isVersionConflict(cause, codes?)`; the AI task, import profile, mapping grid, relationships table and model release pages read the new code. API.md, the reference, the journeys and the guide's integrate pages name the one code.
- **Unused database role dropped (SR3)**: migration `20261204_01` drops `rdm_derived_reader`, which `20261119_04` made for derived sheets and nothing used; it runs only where the database user may manage roles and leaves the role when another database of the cluster still holds something of it.
- **One version of each backend step (SR3)**: internal; behaviour, both OpenAPI documents and the database stay as they were (the page-size row leaves both documents byte-identical; the hash of every canonical-JSON caller was checked on the dev database before and after). `require_version` / `version_conflict` (`errors.py`) replace about 30 hand-written version checks and four `_stale` helpers. `jobs/background.py` holds `request_stop`, `CANCELLABLE` and `replace_earlier_job` for the nine stops and the four replace-an-earlier-job flows; `jobs/inline.py` holds `earlier_job`, `keep_key`, `workspace_key` and `check_change_set_claim` for both batch submissions; the worker has one cancelled exception (`JobCancelled`) and one lease check; job kinds are one registry (`jobs/kinds.py`) that the worker's dispatch, the claim order, the groups and the API's kind lists read. `EngineModel.application_of_type`, `CopyRows` (`common/copy_rows.py`), `canonical_json` and `sha256_hex` (`common/encoding.py`), `value_json` (`records/values.py`), `management/sse.py`, `common/chunks.py`, `common/counts.py` (`count_noun`), `identity/lookup.py` (`user_by_email`, `load_user`), `escape_like`, `PageSize` (`management/paging.py`), `common/versions.py`, `common/addresses.py`, `management/sign_in_messages.py`, `workbook_of` / `job_of` and `discard_set` (`tasks/store.py`), and in the change set and migration code `capture_base`, `remove_base`, `claim_active_workspace`, `guarded_execution` and one relationship state replace the copies; `openpyxl`'s column letters replace `xlsx.column`. The dead derived-sheet constants of `draft_plan.py` are removed.
- **A package leaves its screens' checks passing (TS1)**: internal. `frontend/e2e/manifest.mjs` names the source paths each browser runner and each group of accessibility and visual scenarios covers; `npm run test:changed -- <commit> [--list]` lists and runs (through `test:lanes`) the runners and scenarios a diff touches, a change in `ui`, `state`, `lib`, `model` (and `api`, `routing`, `types`, `app`) selecting the entries of every file importing it, read from the imports; the accessibility and visual gates take `--scenario <group>,...` and fail a scenario no group names; `test:gate-helpers` fails on a manifest path that is missing or a runner or scenario without an entry. AGENTS.md and the implementer's instructions now say a package that changes a screen is finished only when its runners and accessibility scenarios pass, its changed screenshots are looked at and re-recorded and its guide pictures follow the retake rule. The security screenshots were not stable between runs (table columns sized by the width of a time such as "11 minutes ago", and the sign-in screens' build line changing with each commit): times and the build line are now fixed in width before each capture, and 25 security baselines were re-recorded. The sidebar tree runner (`s6-sidebar-tree`) waits for the group's next page to arrive instead of pausing a fixed 200 ms per scroll step, so it no longer fails on a loaded machine. No application change.
- **Fixed waits out of the slowest tests (TS5)**: internal. The stand-in assistants of the J50 journeys wait for their jobs on the job's event stream instead of polling every 0.2 s; the journeys' waits for a file or a state are one helper (`wait_for` in `tests/journeys/scenario.py`, 20 ms checks, a bound and a message naming what it waited for) and `_run` returns the moment the session ends; the sleeps that prove something stay. What each test checks is unchanged. One application change: an assistant session's run now ends as soon as its process exits, instead of up to 2 s later (`engine/tasks/agent/run.py` waits on the process rather than sleeping).
- **Tests chosen by what they import, with their expected time (TS4)**: internal. `python -m tests.affected` selects the test modules that import a changed app module, directly or through other app modules (the closure stops at `app.main`, which mounts every router), and the tests that start the application and reach it over HTTP, from a checked map (`backend/tests/reach_map.json`, recorded by `python -m tests.journey_trace --record` with Coverage.py; a harness test fails when it names code or a test that no longer exists or lacks a module that starts the application); a changed test or test helper selects the tests importing it; inputs of the `schema` seed select everything and those of the volume seeds the tests using the volume fixture. Every pytest run writes each test's duration (not `budget` or `serial` tests, not in CI) to one file beside the test server's data, merged under a lock so runs side by side keep each other's; `tests.affected` prints the selection's expected time from it, how many tests have no record, and says when it is over the 3-minute package ceiling; a full-suite run ends with its ten slowest modules. Two flaky journey tests are fixed (a reset token holding the digits the mail check looked for; an authenticator code computed twice across a 30-second step). `pytest-testmon` and its data file are removed (`coverage` stays as a direct dev dependency); AGENTS.md, the execution guide, the strategy and the harness plan say so. No application change.
- **Browser runners in lanes, waiting tests on workers (TS3)**: internal. `npm run test:lanes -- <runner>... | all` runs a list of browser runners and the accessibility and visual gates in 1-4 lanes sized to the free memory (`--lanes` or `RDM_LANES` overrides) and writes one summary (per runner: lane, result, duration, bounded log); every runner takes its servers' ports by reservation (`helpers/ports.mjs`) instead of probing, three runners that started a backend without a folder of their own for export files now have one, only one visual runner writes baselines at a time, and a runner needing a fixed port runs alone on it or is refused with a message. A backend selection holding journey or assistant tests runs with `-n 4` whatever its size, then its `-m serial` part (`tests.affected` prints it so). A runner's temporary evidence folders are removed when it passes (kept and named in the summary when it fails or with `--keep`). No application change.
- **Test runs side by side on one server (TS2)**: internal. Test databases are named with a run ID (process number and start time; the browser runners use the same scheme), so a starting run drops only the clones of runs that ended and never a live run's; a volume seed is cloned only when no live run holds a volume clone (browser runners included), so one copy exists at a time; the shared server is stopped only by the last run using it, and starting and stopping it are serialised by a file lock; a run refuses to start below 10 GB free or on a data folder in a synced place; `python -m tests.clean_copy` runs a package's final checks on the last commit plus the paths it names. AGENTS.md's one-pytest-at-a-time rule is replaced. No application change.
- **The assistant task's code split by concern (SR1)**: internal. `engine/tasks/agent.py` is now the package `engine/tasks/agent/` with `sandbox`, `files`, `words`, `run` and `outcome`; no behaviour, API, prompt or database change.
- **Frontend features import shared state from one layer (SR2)**: internal. App-wide state and hooks move out of single features into `src/state/`, parts several features show into `src/ui/`, `src/lib/` and `src/model/`; a lint rule (ADR-046) keeps features from importing each other beyond a short list of deliberate edges; two import cycles are gone. No behaviour change.

## [0.17.1] - 2026-11-13

Fixes after 0.17.0: exports for people offer their drop-down lists in every workbook and open as pop-up
menus in Numbers, and load back unchanged (checked through Numbers itself for a type, a set of types, a
tree and an application workbook); Stop works at once when proposing from a workbook; a record page's
Details stays open. No images were built for `v0.17.0` (its CI did not pass), so 0.17.1 is the first
0.17 release with images.

### Fixed

- **Two relation columns naming the same shared name import back unchanged (R17-F50)**: a row whose cells in two columns (different relationships or directions) named the same value several records share was refused as ambiguous although nothing was edited, because the turns for a repeated name were counted across the row's links instead of per relationship and direction. They are counted per relationship and direction now.
- **Stop works at once when proposing from a workbook** (R17-F49): pressing Stop before the engine had answered the start request did nothing and the inference carried on; the job is now cancelled as soon as it is known and nothing is applied.
- **A view with an `ancestor:<type>` column can be exported for editing**: a mapping grid or table that shows the ancestor of a record (for example a system value's system) was refused with "is no column a table can show". The column is for reading (marked not imported), holds the name of the record's ancestor of that type as the path names it, is read in PostgreSQL with the rest of the sheet, and the file imports back unchanged.
- **A tree, type, application or workspace workbook offers drop-down lists again**: the sheet-per-type workbooks had none. A parent column and every relationship column holding one record now offer the records they may choose, from list sheets shared per type and rule as in a people workbook; a parent found by its hidden ID stays as it was. A column that may hold several records offers the list too, as a soft one (pick one, or type several separated as the cell lists them, as a link matrix's cells do). A column made read-only because its records' names clash writes no list sheet.
- **A mapping grid's export edits its mapping**: the mapped column covered every type the relationship reaches, so it was read-only with no list. It now covers the grid's target type alone: editable, with a list of that type's records, and an import replaces only the mappings to that type (mappings of the same relationship to other types stay).
- **Lists open as pop-up menus in Numbers again**: list sheets were named "List · …", and Numbers makes no pop-up menu of a list on a sheet whose name holds "·" (checked in Numbers itself; Excel read them). They are named "List - …" now; a file exported before still imports.
- **A table's main sheet edits a relationship holding one record, with its list**: the Export dialog gave every relationship the table shows a sheet of its own, which made its main-sheet column read-only. It now gives a sheet only to a relationship that needs one (holding several records, carrying its own fields, or shown by a field other than the name); Advanced still adds any.
- **A relationships table offers lists**, for both records of a row, and every relationship sheet's first column (the row's own record) offers the records it may name.
- **Yes/No values of a relationship import back**: a relationship sheet's or a relationships grid's Yes and No were refused as "must be boolean". A profile's relationship value takes `valueMap` (`relation.attributes[].valueMap`) as a column does, checked like it, and the exports name the Yes/No map.
- **A name several records share imports back unchanged**: in a link matrix, a cell naming one of several same-named records of its column was refused as ambiguous. A value several records match now means the ones the row is already related to by the link's relationship (in turn, for a name listed more than once), found in the same set statements; a name matching none of the row's records stays ambiguous.
- **A relationship stored with an empty value is unchanged by a file that leaves the cell empty**: a value stored as null and a value left out are the same, so an unchanged file no longer updates such relationships.
- **Every workbook for people says the same about its lists**: the About sheet's "How it loads back" names "Choose a record" and "List sheets" wherever cells offer lists, and "Editing in Numbers" gives the steps to type other values (Format, Cell, Data Format: Automatic) or add a choice, shared with the link matrix.

### Changed

- **A record page's Details stays open for every record**: once opened (ID and version), it is open on the next record too, until it is closed again; the choice is kept per browser. Frontend only; no API change.

## [0.17.0] - 2026-11-13

0.17, the plain path, released together with 0.14, the management API reference: a workbook shaped on a
canvas and made into a workspace in one step, the canvas as a full model editor, themes with their
frames, a page for each workspace, Settings by task, a field that saves when it is left, an e-mail
template, account security messages, the e-mail as the sign-in name, any view in a navigation group,
exports that follow the view, and the complete management API reference with its error catalogue.
It also holds what shipped earlier as 0.16.1-alpha.1 to alpha.5 (0.13, the documentation) and
0.16.2-alpha.1. The release review's findings are under "Fixed (the 0.14 and 0.17 release review)".

### Added (0.17: upgrade and first-deploy scripts for Docker deployments)

- **`scripts/upgrade.sh` upgrades a Docker Compose installation in one command**: it checks the host (Docker, `compose.yml`, the env file, the running database, free space of twice the database's size), backs up with one time stamp (the database as `pg_dump -Fc` proved readable with `pg_restore --list`, the `job-files` volume, the env file at mode 600, optionally the assistant volume; old backups stay), pulls the registry images, builds, stops the engine, runs `python -m app.cli.database_upgrade`, starts everything, waits for `/health` and prints the engine version and database revision before and after with the commands that restore the backup. A failed migration leaves the engine stopped and prints those restore commands. Options `--backups`, `--with-assistant`, `--skip-backup`, `--yes`, `--dry-run`, `--force`, `-f`, `-p`, `--env-file`.
- **`scripts/deploy.sh` makes the first deployment**, on a server or a laptop (`--local`): it asks for the address, the HTTPS mode (automatic certificates, your own files, a load balancer, or plain local HTTP) and the first administrator, writes the env file from `.env.example` with generated secrets (mode 600, never printed, never over an existing file without `--force`), checks Docker, Compose 2.24+, the ports and the disk, builds, creates the database, starts everything, waits for `/health`, creates the administrator and prints the next steps. It refuses a host that already holds an installation. Both scripts share `scripts/lib/ops.sh` and take `--yes` and `--dry-run`.

### Fixed (the 0.14 and 0.17 release review)

- **Every error response in the API reference has an example body**: each code an operation lists shows the refusal's `{"error": {"code", "message"}}` envelope, instead of an empty response.
- **A provider's e-mail address is taken only when it can be trusted** (R17-F20): an `email_verified: false` claim is never taken as a person's sign-in name; a provider has a new setting, `emailsTrusted` (Settings › Security › Sign-in, `POST|PATCH /sign-in-providers`), and when it is off (the default for a new provider) an address is taken only with `email_verified: true`, else the sign-in is refused (`email_unverified`) and tells the person to ask an administrator; the same rule applies when a later sign-in brings a new address; the "address is taken" message no longer names the address; two people moving to the same new address at once no longer end in a server error (R17-F26).
- **The e-mail template's text keeps links and names intact** (R17-F21): Markdown marks are removed from the template alone, so an underscore in a link's token or `*x*` in a name stay as they are.
- **A queued message is sent with the logo it was rendered with** (R17-F22): the logo is kept by its checksum while a waiting message refers to it, the logo is no longer read for every message, and a replaced logo does not change a message already queued.
- **An uploaded SVG logo is checked as XML** (R17-F23): a script in any namespace, an `on*` attribute, a link that is not `#` or an inline image, an imported or external style, `foreignObject`, a DTD or a stylesheet instruction is refused.
- **Every mail greets once** (R17-F24): inside the operator's template the message's own "Hello" is dropped and the template greets (as the default does); without a template the message greets itself.
- **Placeholders in the template are filled in one pass** (R17-F25): a name, address or message that looks like a placeholder or a stand-in is never filled again.
- **The first save of the e-mail template at the same moment no longer fails** (R17-F26): the second request is answered `409 VERSION_CONFLICT`.
- **The export reference says how a matrix cell is listed** (R17-F27): `cellField` is `name`, the display attribute or any other text or long text attribute the type binds, and left out the cell lists the record by its name alone.
- **The navigation reference says a group entry may be any view** (R17-F28): `OutlineNavigationEntry.view` and `entries` no longer speak of relation matrices only.
- **Three error lists are complete** (R17-F29): the e-mail preview also answers `MAIL_TEMPLATE_TOO_LONG` and `REQUEST_VALIDATION_ERROR`, the logo upload `REQUEST_VALIDATION_ERROR` for a missing file, and an export `REQUEST_VALIDATION_ERROR` when it names neither a scope nor a view.
- **The reference test looks deeper** (R17-F30): it checks the descriptions of fields nested inside a schema and validates every recorded example body against its operation's request or response schema.
- **The guide coverage check is stricter** (R17-F31): text in headings no longer counts, a one-word label counts only beside a context word on the page, and the inventory lists mail message kinds, search boxes and Docker build arguments; the entries now uncovered are in `guide/_coverage/notes/r17-uncovered.md`.
- **A workspace made from a workbook cannot be made twice** (R17-F14): a success raises the draft's version, so sending the same request again is `409 VERSION_CONFLICT` and makes no second workspace and import (the route takes no `Idempotency-Key`: that key is scoped to an existing workspace, and this request creates it).
- **Placing new cell records is worked out in the database** (R17-F15): the containers under every column record, their ancestor chains and the candidate criteria are read for the whole set of column records in recursive statements instead of one Python walk of every container per column record; the answers are the same and the statements do not grow with the number of column records.
- **A workspace from a workbook refuses a draft that is not free** (R17-F16): `409 DRAFT_HELD_BY_WORKSPACE` when another workspace remembers the draft, `409 AI_TASK_DRAFT_HELD` when an assistant task names it, as opening a workspace's model never takes either.
- **Two workspaces made at once under one name no longer fail with a server error** (R17-F17): the choice of a new workspace key is taken one request at a time, so the second gets the next free key, or `409 WORKSPACE_ALREADY_EXISTS` for an explicit key.
- **Dropping a reading unmaps every binding that names its added columns** (R17-F18): not only a binding's `column` but its `columns`, a relationship's ID, version and value columns, a related record's ID, version and parent column, and the key's version and name columns, as documented, instead of failing with `COLUMN_NOT_FOUND` when the next file is read.
- **A filled-down value no longer carries across a heading** (R17-F19): with `headings` and `fillDown`, each heading row starts a new group, so an empty cell never takes a value from the group above.
- **A sheet tab has a menu** (R17-F1) with "Make an object type of this sheet", by mouse or keyboard and on a phone, so making an object type of a sheet no longer needs a drag.
- **Two quick gestures on the canvas both apply** (R17-F2): steps are sent one after another, each at the version the previous answer returned; a real conflict from someone else still shows the stale notice.
- **A rename on the canvas says what happened** (R17-F3): no "Renamed." when the draft had moved on and nothing was saved, and the rename toast has an Undo.
- **A toast's Undo takes back its own step** (R17-F4), not the draft's latest one; the toolbar Undo still takes the last.
- **The canvas no longer has its own "Remove object type"** (R17-F5): it never removed a type loaded twice or related, yet said it was removed. The editor's "Remove type" is in the same menu, and "Don't load this list" stays in the sheet's panel.
- **Renaming an object type on the canvas sends what the editor's heading sends** (R17-F6): the name alone, the plural name left as it is; one shared builder, checked in the parity test.
- **Reading a row as the header changes only the list the preview shows** (R17-F7), not every list on the sheet.
- **A relationship row's rename says "Name of the relationship …"** (R17-F8), not "attribute".
- **A refusal is shown even before the model outline is read** (R17-F9) instead of being dropped.
- **Consumer APIs names the chosen workspace's own model release** (R17-F10): the release row and "Open the release" followed the default workspace even when another workspace's APIs were listed.
- **A tab left open across a deployment reloads once** (R17-F11) instead of showing the error screen when a page's code file no longer exists; a second failure still shows the error.
- **The e-mail template asks before you leave with an unsaved draft** (R17-F12), as other unsaved edits do.
- **The change set band shows who and when again, and the submitter's comment** (R17-F13); Details names the publication a change set started from by its number, no longer by its identifier.
- **Settings paths in the project documents use the new groups** (R17-F34, documents): You, Workspaces and models, People and access, Connections and This instance replace Security, Integration, Administration and Data operations in OPERATIONS, CURRENT_FUNCTIONALITY, USER_JOURNEYS, UI_ACCEPTANCE, PRODUCT and ARCHITECTURE.
- **The 0.17 upgrade warning about e-mail addresses** (R17-F35, OPERATIONS): the upgrade stops, changing nothing, when an active person has no e-mail address or two people share one ignoring case; the section gives the queries to find them, what to do, and says the database stays at its previous revision.
- **ARCHITECTURE covers the 0.17 mechanisms** (R17-F36): the e-mail template, security messages and the per-e-mail failure counter, the assistant session in a container, the webhook private-address refusal, `FORWARDED_ALLOW_IPS`, the content security policy, managed sign-in, a workspace from a workbook, the canvas layout storage and the removed username.
- **The current-functionality list names 0.17's group entries and security messages** (R17-F37): any view can be placed in a group; people are mailed when their password, second factor or passkey changes.
- **The mail chapter of OPERATIONS describes the e-mail template and the security messages** (R17-F38): where the template is edited, that it wraps every message and that it is in the database, so in the backup and restore.
- **The 0.17 plan no longer names the sample workbook's content** (R17-F40).
- **The guide's navigation-group pages describe any view as an entry** (R17-F32): the group page's **Find a collection or view** and its messages, a view entry's kind and **Opens on**, and **Move to group…** on every view.
- **The guide describes the sidebar's Find a list** (R17-F33) instead of saying the sidebar has no list search.
- **Settings paths in the guide name today's groups** (R17-F34): **Workspaces and models › Import profiles** and **Copy and move**, **This instance › Jobs** and **AI**.
- **The upgrade page warns before the e-mail becomes the sign-in name** (R17-F35): two checks to run on the old version, what to fix, and that a stopped upgrade leaves the database as it was.
- **The mail page gives the notification e-mail location correctly** (R17-F39).
- **The guide names the 15 controls the stricter coverage check found undescribed** (R17-F31): the workspace and Home searches with their ⌘K boxes, the canvas's find box and sheet menu, the search boxes of Settings › Model and Workspaces, Notifications, a group's members and a panel's related records, the Search or ask switch, the panel tools menu, and the build-reference arguments `REFIROO_BUILD_COMMIT` and `REFIROO_BUILD_TAG`. Route entries and search fields now carry context words, so a one-word label counts only where its place is named.
- **The guide's sign-in pages describe Trust the e-mail addresses … sends** (R17-F20): when to turn it on, what a person sees when an address is not confirmed, and that the upgrade switched it on for existing providers.
- **A stopped assistant session is collected, not left a zombie** (R17-F41): when a turn ended by a stop, a timeout or a failure, the engine ended the session's process group but never collected the process, so it stayed a defunct child of the engine until the engine exited and was reported as "still running" when its handle was dropped. The turn now waits for it (and kills it if it has not gone after five seconds).
- **Tests brought up to date with the changes they followed** (R17-F42): the MCP clients of the agent-access tests use `streamable_http_client` (mcp 1.30 deprecates `streamablehttp_client`); the relation matrix volume test patches `matrix_read.current_pairs`, where RF2 moved it; the batch statement budgets for live creates and upserts count the job response's origin read (0.13 JG); the narrowing and public-route lists of J47 name the job re-read, the deletion-impact read and the docs example route; API_JOURNEYS.md lists the e-mail template and from-workbook error codes with their journeys (J46.12 now also covers `MAIL_TEMPLATE_TOO_LONG`); J47.9 follows SM1 (turning on an authenticator app is told by mail); the startup tests expect migration `20261203_01`; the column-containers journey follows MC1 (an empty container is never the default); the import places statement test compares two sets that both need the proposal reads and counts only its own thread's statements; the starter-key check no longer meets an example key in a docstring.
- **The workbook pane's sheet tabs pass the accessibility check beside their menus** (R17-F43): a sheet tab's actions menu button stood inside the Sheets tablist, which a tablist may not hold; the list now owns its tabs and the menus stand beside them.
- **"What changed" on a workspace's Activity tab no longer skips heading levels** (R17-F44): the section was an `h3` straight under the page's `h1` (and its facts an `h4`), which the accessibility check reports as a skipped level; the section is an `h2` there and its facts an `h3`, and stay `h3`/`h4` on a record's History.
- **Home no longer scrolls sideways at 390px** (R17-F45): the page's one column grew to the widest content of its sections and the "New workspace from a workbook" button, which does not wrap, pushed the section head past the screen; the column may now shrink and the heading and its action wrap under each other.
- **A workspace's Activity tab no longer skips a heading level** (R17-F46): the day headings were level 3 under the page's level 1 whenever the AI summary above them is not offered (it then draws no heading); they are level 2, which reads in order with or without it.
- **The new sign-in provider dialog spaces its two switches** (R17-F48): each switch and its explanation stand as a field, so the trust switch's explanation no longer runs into the next switch.
- **A list's columns fit the values they show** (R17-F47): a table lays its columns out from the rows first drawn and keeps them still, so another page or rows scrolled to with a longer value (`long-9`, then `long-20`) ended in an ellipsis while the name column had room to spare. A column that a drawn row cuts now grows to its widest value, up to the table's per-column cap, taking the room from the name column and never narrowing it below its own width; columns only grow, so they do not move back and forth while the list scrolls.
- Visual baselines re-recorded after looking at every differing scenario: the 0.17 frame, Settings family, themes' current look, dialogs as popovers, views as tabs, PL5 identifiers out; masks moved to the new markup.
- **Browser runners brought up to date with the changes they followed**: `test:browser:authoring` (UX2: Escape is pressed once the refused field has its focus back), `authoring-a4a` (R17-F2: waits for the queued Undo before reading the draft's version), `authoring-a4c` (UX2: a choice from a list saves as made, no Save button), `authoring-r` (ST1: Import profiles is a list in a Profiles region), `pl3b` (waits for the workbook pane at 390px), `publications` (a change set names its starting publication by number).
- **Browser runners brought up to date with the changes they followed (second batch)**: `wp12` (SH1: the release header is the item header), `s5` (the lens switch's one-row mapping probe is not the grid's read), `workspace-x5` and `workspace-r` (the workspace page's actions are a menu worked by arrow keys), `settings` (ST1: Deployment is rows of settings, so the content holds no tab stop), `security-r` (ST1: People and Groups are rows in regions; a person's page is headed `h1`; roles are chips in a list named Roles in <place>), `changes` (UX1: Show more; a person's page is `h1`; See changes is an item of More actions), `sign-in-providers`, `i4` and the shared security surfaces (R17-F20: the harness provider sends no `email_verified`, so it is added with its e-mail addresses trusted), `operations` (ST1: earlier rehearsals are setting rows), `ai` (ST1: Settings and Calls tabs, durations in seconds, Deployment rows; PL3b: the session stand-in stores its profile on the draft, so a keyed load first clears the profiles earlier loads saved), `ap12` (the dialog's intro holds the words the wait looked for), `ap13` (a session that has said nothing shows "Starting"), `ao2` (heading levels, R17-F44), `ao3` (UX1: the kinds' choices are radio groups in a fieldset; EM1: the follower is found by the e-mail address the run sets), `link-mail` (a person's page no longer holds the people list), `ex1` (NG1: a view in no navigation group is headed by its type's plural name), `v1` (the bundled console's token fields are named Token).

### Security (the 0.14 and 0.17 release review: provider e-mail addresses)

- **A provider's unverified e-mail address could be squatted** (R17-F20): the e-mail is the unique sign-in name, and some providers let people set it, so an address could be taken by someone else and later receive roles granted by pasted address. See the fix above. The upgrade sets every existing provider to trusted so production sign-ins keep working; review each provider's **Trust the e-mail addresses it sends** and turn it off where people can set their own address. Contract change (additive): `emailsTrusted` on `SignInProviderCreate`, `SignInProviderUpdate` and `SignInProviderResponse`; a provider created through the API without it starts as not trusted.

### Changed (0.17: the view name comes first and shows when it is empty)

- **In the model editor**, every view's form, Add a view for each kind and Change on an existing view, now starts with
  **Name** instead of ending with it. The field has a red border while it is empty or only spaces, and the border goes
  as soon as you type something.

### Changed (0.17: the lens row under a parent lists the mapping views that have mappings there)

- **On a collection narrowed to a parent**, the view tabs under the heading list only the mapping views that already have a
  mapped record under that parent, besides the tables, trees and relationship views and the view you are on. When no mapping
  view has a mapping there, or the answer cannot be read, every view is listed as before; without a parent nothing changes.

### Changed (0.17 NG1: any view can stand in a navigation group)

- **A navigation group places a view of any kind**, not only a relation matrix: a table, a tree, a mapping grid, a
  relationships table or a relation matrix. `{ "view": "<key>" }` beside collection keys, in the group's one order, now
  accepts any view of the application (schema 0.10, additive; `INVALID_REFERENCE` for a view the application does not declare,
  `INVALID_MODEL` for a view in a second group, as for collections). `placeCollection` with `view` places, moves and takes out
  any view, and removing a view or giving it a new key drops or follows its member as it did for matrices. A grouped view has
  one sidebar entry in its group, named after the view, and its collection keeps it among its view tabs (PP-D11 to PP-D13).
  The sidebar and the group page show every kind as its own entry with the glyph of its kind; **Move to group…** on a view's
  row in **Views** and **Add to group…** in the group's panel offer every view; `groupOperations` (the canvas's group drop)
  takes a view through the same `placeCollection`. A document that named a table or tree in a group was refused before and is
  valid now.

### Added (0.17 SM1: a message when a person's sign-in changes)

- **A person is written to when their sign-in changes**, so a change they did not make is noticed: their password was changed
  (by them, with the current one) or reset (with a one-time link), an authenticator app was added or removed, a passkey was
  added or removed (by them or by a security administrator). Choosing a first password sends nothing. The message says what
  changed and when (UTC) and to contact an administrator if it was not them, sits in the saved e-mail template with its
  plain-text part, and carries no password, code or link that signs in (D421). It is queued with the change in one
  transaction, as the activation mail is, so a refused change sends nothing. A person cannot switch these messages off; with no
  mail set up or no e-mail address the change is made and nothing is queued. The mail outbox lists them as kind `security`
  (additive); `identity.product` now holds `product_name`, which was in `identity.second_factor`.

### Changed (0.17 CE1: shared pieces of the model editor, first part)

- **An Editor | Canvas switch** stands at the top of the model editor in place of the Open as canvas link, and the canvas page
  mounts the same one. A draft opens on the view the person used last (remembered per draft in this browser), and on the canvas
  from a workbook flow.
- **What a load does with the records no row names** (the API's `setMissing`) now has a place in the interface: on a list's
  panel, Report them or Delete them, changed where it stands. Delete asks once and says what a load will then delete. It is not
  shown for a list with no key or one that loads no records of its own.
- The canvas document of a draft (`GET`/`PATCH /api/v1/model-drafts/{id}/canvas`) also keeps the folded cards and the chosen
  scope (`model`, `changed` or `workbook`), merged by key and replaced as the positions are, outside the draft's version, history
  and releases (additive).
- The editor's steps and refusals, operation dialogs, notices, workbook dialogs, More menu actions and the type preview are
  pieces another page mounts with props only; the editor uses the same ones.
- **The canvas shows the model editor's own issues and history drawer** (the same bar, counts, tabs, height and dry run), in
  place of its own foot and the "n to fix" in its strip. An issue about a relationship now selects and centres that relationship's
  line; it used to do nothing for a parent-and-child relationship, and the drawer no longer changes height between its tabs.
- **The canvas's strip holds its tools**: Find, Undo, Redo, Tidy and + moved from the top bar into the strip, after the Whole
  model | Changed in this draft | From the workbook switch. The switch, the tools and the summary (applications, object types,
  changed) each stand in a rounded box of their own quiet hue.
- **"From the workbook" is offered only with a workbook**: on a draft without one, the canvas's switch shows Whole model and
  Changed in this draft, and a scope kept on the draft falls back to the whole model.
- **Add a workbook… stands beside that switch** on a draft without a workbook, and the empty workbook pane is gone: the board
  takes its width. Once a workbook is added the workbook pane shows as for an import, and a draft that had no scope chosen
  stays on the whole model rather than switching to the workbook's (still empty) lists.
- **Applications stand side by side** when the canvas lays the board out (a draft with no places kept, or Tidy): as many
  application frames per row as fit, each with its share of the width, instead of the first one taking the whole row.
- **A card is carried by its name too**: a press on an object type's name moves the card once the pointer moves, and a click
  still renames it. Only the small grip and the gaps in the card's top bar carried it before, so a card seemed not to move.
- **Folding a card closes up its column**: the cards under it in the same application move up by the space it gave up (and
  down again on unfold), so its frame and lines shrink with it instead of leaving an empty area. Space left by folds made
  before this change goes with one press of Tidy.
- **The canvas's layout editor and preview use one line in place of the strip**: the type, Layout editor or Preview, the
  record to show, the note, and Undo, Redo, Preview (or Edit layout) and Back to the board, packed to the left. The
  application and workspace choices are left out there; the model editor's band keeps them. On a phone the line wraps, and
  the preview now stands as tall as the board (it had collapsed to a sliver).

### Added (0.17 CE1: the canvas edits the whole model)

- Names of object types and attributes on the canvas are no longer cut short where the row has room; a name
  that is still too long shows in full on hover.
- **The canvas does what the model editor does**, on the same draft, with or without a workbook. The page uses the editor's
  editing hook, dialogs and notices, so every list, field, relationship line, navigation group and application frame is a target of
  the editor's own operation table: its menu (the ⋯ button, right click, Shift+F10) is the editor's `OperationsMenu`, with the
  canvas's gestures (Put under…, Relate to…, filters) in a Canvas section, and its forms are the editor's. A test
  (`parity.test.ts`) fails when the table gains an operation of a kind of target the canvas has no place for.
- **The whole model on the board**: a switch Whole model | Changed in this draft | From the workbook (kept on the draft), a frame
  per application with its name on its border, Tidy inside the frames, released lists nothing changed drawn quieter, the editor's
  New / Changed / Released mark on each card, Find (Ctrl or Command with K; Enter centres and selects), zoom (− 100% + Fit,
  Ctrl or Command with the wheel; kept in the browser), a card folded to its top bar (kept on the draft). Opening a model,
  moving cards, Tidy, folding and zoom change neither the draft's version nor its model.
- **By hand**: the editor's own Add menu in the header (one shared component, `AddMenu`: Application…, Object type…, Attribute type…,
  Relation type…, group, with the editor's forms; an object type made there is selected and the board centred on it) and the
  editor's New attribute button at the foot of every card; names of object types and attributes change where they stand. The
  canvas uses the editor's words (object type, attribute) and "Propose again…" in More actions. An attribute row dragged onto another
  object type's card moves there (the editor's Move to…), and up or down within its card, or with Alt+ArrowUp / Alt+ArrowDown,
  changes its position (the editor's Move up / Move down; a line shows where it will land). A draft without a workbook folds the
  workbook pane away and offers Add a workbook….
- **Inspector** (Inspector, Navigation, Views, Consumer APIs): the editor's element, column and list panels (with what a load
  does with the records no row names), a field's rows, the group operations, a list's tables and record page in the editor's
  preview and layout editing in the main area (Back to the board), the consumer API pane and panel. A click on a line opens its
  rule popover (how many, required, the fields it carries, which records may be chosen).
- **Issues and History** in a foot drawer: an issue selects its card, field or line; a chosen step is undone, and a refused undo
  says what it depends on. The selection is kept in the address (`?show=canvas&element=…`).
- Header: the Editor | Canvas switch, Find, Undo, Redo, Tidy, the editor's Add menu, Propose again… (in More actions), Create workspace…
  or Apply to this workspace… and Install and activate…, and ⋯ with Load into a change set…, Add a workbook…, Open as JSON, Delete draft….
  The load into a workspace the canvas had is now the editor's own Load into a change set….
- **A layout stored before the cards grew is read apart**: a card whose box overlaps another's is moved down below it, keeping its
  column, and the moved places are written back once to the draft's canvas (not as a model step), so no Tidy is needed.
- **What the Add menu makes that has no card is shown**: an attribute type or a relation type made there is selected in the
  inspector (its own panel), a navigation group in the Navigation tab, each with a toast and Undo. The inspector's panel for such an
  element is held by the page and cleared by the next pick on the board. The Find field is wide enough for its hint.
- Browser runner `test:browser:ce1` (a model built from nothing and installed; a released model opened whole). Decisions PP-D86 to PP-D89
  are numbered after the duplicate PP-D83 to PP-D85 of the same day were resolved (the PL3b ones keep their numbers).

- **The model editor sets the workbook's three readings too** (0.17 CE1, PP-D77): a column's panel offers Fill blanks from the
  cell above, Rows holding only this column are headings… and Read these columns as rows… (which asks which columns, then
  the two new columns' names and the object type they are added to, the list's own at first), each with its Stop entry while it is on; a sheet's list offers Read these columns as rows… beside
  its other actions; a column that a reading is on carries a mark in the source pane. The operations and the questions are the
  canvas's own, built once (`model-editor/readings.ts`, `ReadingAsks.tsx`); each entry is one request and one undo step.

### Added (0.17 PL3b: the workbook canvas)

- The workbook canvas page: sheets dropped on the board make lists; a column onto a list, a field or a list's Filters is one
  request and one undo step; Connect finds the column that names the other list over every row and binds it with the link (a
  tie is asked); several chosen columns are read as rows; the sheet's first rows with a pressable header row; fill down and
  heading rows from a column's menu; the reasons for refused rows with a value-map correction; Proposed on cards, fields and
  columns; keyboard paths and a one-column phone layout; Create workspace…, Apply, Load into an existing workspace…; Open as
  canvas in the model editor; PL4's Adjust opens the canvas.
- The model editor shares the canvas's draft steps, dependants dialog, workspace choice and Proposed logic.
- Fixed: the canvas read a column of numbers as text, and drew a line for a list that contains itself.
- Fixed (found by trying three workbooks): the canvas's Create workspace… now lands on the workspace's own page, where
  the load's progress and result are shown. A sheet dropped on a draft with no application, or on a board where a list
  already reads it, no longer fails or makes a second list. A column dropped on the empty board is now a new list of its
  values, linked back, with a source of its own, in one request; a column that already fills a field is not made a second
  field. Connect finds the column that names a parent when both lists read the same sheet. Headers in CamelCase read as
  words. A card made by a drop sits at the drop point, at least 16px in from the board's edge. The toolbar hides Create
  workspace…, Load into an existing workspace… and Tidy where an empty board could not finish them.
- Fixed: a session's log file handle was never closed after a turn (the AI journey J50 failed at teardown with an
  unclosed-file warning).


### Fixed (0.17 UX1: dialogs in the middle of the window)

- **Every dialog opens in the middle of the window again** (PP-D69), in every theme and frame arrangement. UX1 had
  drawn forms as a sheet at the right edge, as tall as the form, so a short form such as a matrix cell's stood in the
  top right corner. Dialogs have the widths they had before; a long form scrolls inside the dialog and its buttons
  stay at the dialog's foot. A phone shows the dialog full width, as before.

### Changed (0.17 ST1: Settings as one family)

- **Every Settings page has one shape.** The header carries the page's group, its glyph on a tile in the group's
  colour, one or two sentences and the page's one main action. Under it come groups: what the group is about on the
  left, its values, switches, choices and facts as rows in panels on the right; a table takes the full width.
  Account and Notification email give up their centred columns; Mail's form and every other form saved as a whole
  sits in one panel with Save in its foot.
- **Every list opens its item as a page.** People, Groups, Clients, Sign-in, Import profiles and Webhooks are
  full-width lists, as Workspaces and Model were; a row opens the item's own page, whose first line leads back to
  the list. The narrow list beside the item is gone.
- **An opened item** has a header in its colour with at most two actions; the rest are in a ⋯ menu, what cannot be
  undone last (a person's Deactivate and Sign out everywhere, a workspace's Retire and Delete, a webhook's Rotate
  key and Delete).
- **Logs are on a tab.** Mail (Server, Messages), AI (Settings, Calls), Agent access (Access, Calls) and Jobs
  (Jobs, Limits); the tab is in the address (`?tab=`). A log words a time as "today, 16:34" with the full time on
  hover, right-aligns numbers, gives a duration in seconds and minutes, has its states as chips and, on Mail and
  AI, its totals above; below it says how many are shown ("n of m" where the engine gives a total) with **Show
  more**. Jobs, Signing keys and Agent access keep their name column first, and Import profiles still reads
  further rows as the list is scrolled.
- **Colour.** Each Settings group has a colour, shown on the index, beside each page's title and on its rows'
  tiles; a person and a client have their initials in a colour of their own; a role keeps its coloured chip in
  the People list and on a person's page; activity stays a line by day with a marker in its kind's colour.
- **A person's, group's or client's access is grouped by place:** a line for every workspace first, then one per
  workspace by name, each with its roles and its consumer APIs as coloured chips and a "+" to grant more there. A
  grant held through a group says so in its chip and links to the group; only the page's own grants can be removed.
  The chip is the one a workspace's Access list uses (`features/security/GrantChip`).
- **A person's, group's or client's access is set in one dialog.** Opened from their page it is "‹name›'s access":
  what they hold is ticked, unticking removes it and ticking adds, and one **Save** does both; it was an add-only
  dialog in which everything already held was ticked, grey and locked. A role narrowed to some lists, and a person's
  role held through a group, are not offered there and stay removable by their chip. The chip's trash button is
  always shown on these pages. A removal asks no confirmation; every saved change offers **Undo**. From a
  workspace's Access the dialog still asks who and only grants.
- **The index** lists every page with one line saying what it is for.
- **Deployment** shows each setting as a row: its name with what it controls, its value, the default only where
  the value differs, and where the value came from.
- **One person's changes** (`/changes?actorId=…`) is drawn from the same parts, begins with a way back, and marks
  each kind of change with its colour.
- No route, permission or capability changed. The People list has no Groups column: the people list of the API
  carries no group data.

### Changed (0.17 UX2: one field saves when it is left)

- **A single field edited in place has no form any more** (PP-D68). Clicking a value's pencil turns the value into
  its input where it stands: in a list's cell, in a record's details and header, in the record beside its list, in a
  relationship's value, on the names in Settings and in the model editor. Leaving the field saves it, as Enter does
  (in a text of several lines Enter is a new line and Ctrl or Cmd with Enter saves); a choice or a tick saves as it
  is made; Escape puts the old value back; an input left as it was saves nothing. The Cancel and Save buttons and the
  **No value** tick are gone.
- A saved value is told **‹Field› saved** with **Undo**, also for a value set for the first time (Undo takes it out
  again) and for a relationship's value. An optional field left empty is the value removed, told **‹Field› removed**
  with **Undo**, as the remove icon tells it; a required one left empty is refused under the field.
- A refusal (a rule of the model, a record changed elsewhere, a change set conflict) keeps the field open with the
  reason under it and the input kept; **Cancel** and **Save again** then stand under the reason, and leaving the field
  again saves only once the input has changed.
- Another field can be opened while one is open; the first saves as it is left. A list's value cell shows one toast
  instead of two. A one-line field keeps the height of its row.
- "Cleared" (a stored null) and "Empty text" are still shown, but a field no longer offers to set them (a JSON
  field still takes `null` as typed); the API sets them as before.

### Added (0.17 PL3b: the workbook canvas, engine and API)

- **Three readings of a source's table** (PP-D6, PP-D7, PP-D48), in the import profile, so they hold for any import, a
  dry run, a profile check and a profile saved for the next file: `unpivot` (a wide table read as rows: each filled
  cell of the listed columns becomes a row, the column's header in a new column and the cell in another), `fillDown`
  (columns repeated by blanks) and `headings` (a row holding only a heading is the parent of the rows beneath it).
  Bindings name the added columns like any column; a name the table already has is `COLUMN_CLASH`; a column the next
  file lacks takes its reading with it. A source without readings is read exactly as before.
- **Six operation kinds** to set and clear them on a draft's source, each undoable and validated, with refusals by
  code: `setUnpivot`, `clearUnpivot`, `setFillDown`, `clearFillDown`, `setHeadingRows`, `clearHeadingRows` (PP-D49).
- **`POST /api/v1/model-drafts/{id}/join-candidates`** compares a column of one table with the columns (or one named
  column) of another over every row in PostgreSQL and answers the candidates with their figures; two that match
  exactly as much are a `tie` with no `best`, so a client asks (PP-D8, PP-D51).
- **`GET`/`PATCH /api/v1/model-drafts/{id}/canvas`**: where each card of the workbook canvas sits, by card key, merged
  by key, validated, with the draft's permission. Not part of the draft's version, its history, an undo step or a
  release (PP-D54; migration `20261202_01`).
- **An assistant's design must carry its profile** (PP-D55): when its last check read the workbook through a profile
  sent with the check and the draft stores none, or another one, the task fails with a plain reason.
- The other drops of the canvas need no new route: each composes from existing operations in one request, one undo
  step (PP-D52, J58.1). Journey J58 (`test_j58_workbook_canvas`). The canvas itself is built separately.

### Added (0.17 PL4: a workspace from a workbook)

- **New workspace from a workbook** (PP-D1, PP-D44 to PP-D47). A dialog on Home, in Settings › Workspaces and on a
  workspace's page: drop a workbook, name the workspace (prefilled from the file's name), read what refiroo found
  (each list with its rows, what loads and what does not and why, every row checked), then **Create workspace**. It
  lands on the new workspace's page, which shows the load's progress and what did not load. **Adjust** opens the model
  editor on the draft; **Cancel** removes it; **More ways to start** leads to today's New workspace. The action is
  left out for a person who lacks any step's group at the instance.
- **`POST /api/v1/workspaces/from-workbook`** installs a workbook's draft as a release, creates the workspace on it and
  queues the workbook as an import job into its live data (`independent`: a refused row is reported, the rest load),
  and answers 202 with the workspace, the release and the job. A release version or an import profile key another model
  holds is replaced by a free one, never refused; a draft's profile now starts under a key no stored profile holds.
  Refused with the draft's problems: `422 INVALID_MODEL`, `422 INVALID_IMPORT_PROFILE`, and `422 DRAFT_HAS_NO_WORKBOOK`
  (new). Needs Workspace administration, Install a model (or Model release) and Bulk and import, the last two at the
  instance. New action `workspaces.create-from-workbook`.

### Fixed (security sweep)

- `POST /api/v1/jobs/{jobId}/reread` is in the security oracle, and its reference text names the group that starts the
  job's kind, as the route checks (it said Bulk and import in the workspace). The consumer sweep expects `404
  CONSUMER_API_NOT_FOUND` for a key the workspace's model does not declare, as the consumer API's text says.

### Fixed (0.17 PL3b and PL4, from a workbook)

- A column whose header ends in a space, on a sheet whose header row is not row 1, can be mapped: a header named as the
  source-columns read lists it is matched without its surrounding whitespace, as the import reads it, and saved trimmed.
- **New workspace from a workbook** no longer stops with "No proposal of the draft's inference is open" when
  refiroo reads no list from the workbook by itself: it says so and offers **Adjust**, which opens the canvas. A
  reading that fails no longer leaves its draft behind.
- On the canvas, a sheet dropped on the board becomes one list named for the sheet with each column a field, and
  the first list of a draft without an application brings its application with it.

### Fixed (0.17 UX1)

- AI tasks that move whole types: when the instance already holds a release with the draft's exact content (the same
  change made earlier for another workspace), installing returns that release and the task lands on it; it failed as
  "The session installed no release the moves fit".
- Layout editor, a panel's Columns… dialog: a containing type already chosen (Language on Name translations) no longer
  drew the panel's own columns under the "Where it sits" heading; the own columns come first, then "Where it sits".
- The guide's picture runner stops at a failed screen, because later screens may build on its state; `--keep-going`
  runs on.
- Settings › E-mail template: the Markdown box is tall again (about thirteen lines). Settings' shared field rule had cut
  it to two lines.
- A publication's band no longer squeezes its sentence ("Read-only. A publication's records never change.") into a
  narrow column beside the Viewing bar: the sentence stands on a row of its own under the bar.
- A record opened beside its list no longer clips the remove button of a value or lets its details card scroll
  sideways: the row's controls stay inside a card that has no padding.
- **Expand to full page** replaces the record beside its list in the browser's history, so Back returns to
  the list.
- A page's actions wrap at phone width; Settings › Workspaces no longer scrolls sideways at 390px.
- A change set's dialog (Change model version, Submit) stays open when the window crosses the phone width.
- A record opened from the top bar's search inside a change set or a publication stays in that change set or
  publication.
- In a publication's view the sidebar tree reads beyond its first 50 rows: a group that started reading while
  the publication was loading reads again once it is there.
- At phone width a row opens the record's own page, with its relationships, and no longer a reduced view.

### Changed (0.17 UX1: Instrument's type, Hearth's titles)

- **Instrument reads more clearly.** Its text is set in Inter (bundled, OFL-1.1; `@fontsource-variable/inter`
  5.3.0) in place of Instrument Sans, which stays for page and record titles; codes keep JetBrains Mono. Its
  sizes no longer sit half a pixel under the other themes': table cells, labels and small text are 12 to 13px
  (were 11.5 to 12.5px), running text stays 13.5px, and nothing is smaller than 11px. Colours, frame, corners,
  control height and row height are unchanged, and so are the other four themes. A long list or group name in
  Instrument's list panel shortens with an ellipsis and no longer pushes the panel's content past its edge.
- **Hearth's titles are set in Fraunces** (bundled, OFL-1.1; `@fontsource-variable/fraunces` 5.3.0) at weight
  500, in place of Instrument Serif, whose single light, narrow weight looked thin beside the sans section
  headings; the Instrument Serif package is no longer bundled. Title sizes are unchanged from 761px up; on a
  phone Hearth's page and record titles are 23px (were 26px), so a long name still takes two lines. Hearth's
  text, colours, corners and frame are unchanged.

### Added (0.17 UX1: themes with their frames, and one way to edit)

- **Themes.** Settings › Appearance offers Current (the look refiroo has had, the reference), Hearth, Studio,
  Instrument and Website purple, each in light and dark. A theme sets colours, the title typeface (Fraunces
  in Hearth, Bricolage Grotesque in Studio, both bundled, OFL-1.1), corners, type sizes and control height.
  Every theme's colours are held to the same contrast minimums by `tokens.test.ts`; the palettes are in
  `frontend/tools/gen_themes.py`, which writes their token blocks.
- **A theme arranges the frame** (PP-D39). Current, Hearth and Website purple keep the top bar and sidebar.
  Studio has one side column (mark, applications, lists) beside a raised page. Instrument has a narrow strip
  (mark, applications as tiles, Help, Inbox, Settings, account), the lists as a panel, and the data context as a
  status line along the bottom; a page with no search has no bar. From 761px up; on a phone every theme keeps
  the bar and the drawer. Hearth, Studio and Instrument also have quiet scrollbars, controls that answer the
  pointer and surfaces that arrive with a short motion (off under "reduce motion").
- **The theme base.** Stylesheets no longer write a type size or a corner: 16 size tokens (`--fs-*`) and four
  corner tokens replace about 320 hard-coded values, with shadow, motion and button-corner tokens beside them.
  Current's values are unchanged.
- **One way to edit** (PP-D40), in every theme:
  - a form opens as a dialog in the middle of the window (the side sheet this package first gave it is withdrawn,
    PP-D69); a confirmation no longer carries a "Please confirm" line;
  - a value edited in place becomes its field, with no box and no repeated label; "Set null" reads "No value";
  - a yes or no in a record's details is a switch that saves itself, as it was in tables;
  - a saved value offers Undo in a toast (a record's name, and an attribute that had a value before);
  - a confirmation that destroys nothing has a plain main button, not a red one (`ConfirmDialog` `tone`).
- **Settings and security pages** follow it. A passkey's, client's, workspace's or group's name, and a group's
  description, is changed where it stands (`ui/TextInPlace`), and the saved change offers Undo. The "Keeps local
  sign-in" switch saves at once when turned on and asks only when turning it off removes the password way in.
  The dialogs that remain are forms: a line names the Settings group, the title reads "New ‹thing›" and the
  main button "Add ‹thing›" (Add group, Add role, Add person, Add client, Add webhook, Add provider, Add
  assistant, Add workspace, Add grant); "Save", "Rotate secret", "Rotate key", "Rotate recovery codes", "Remove
  grant" and "Remove second factor" replace the earlier wording.
- **The record area** follows it. Removing a relationship, or clearing an optional value, no longer asks: it is
  done and a toast says "‹thing› removed" with Undo, which creates it again under the record's fresh version. A
  related panel with five rows or fewer folds its Search, Display and Sort behind one ⋯ menu; a larger panel
  keeps them. The sheets' footers are unified: Cancel is the secondary button beside one main button, progress
  text sits in the body, and the mapping sheet's Remove mapping moved into its form. Labels follow one word per
  action: Save, Add ‹type›, Delete ‹type›, Delete N records, Apply for picking several. A record's edit form
  says Save (was Save changes); starting a change set from a publication uses Name and Start change set, as
  the new change set form does; an Undo that is refused because the record changed again says so. A list's header has a
  pin button that brings the list to the person's shelf.
- **Deleting a record is one confirmation.** A new read, `GET
  /api/v1/objects/{objectTypeKey}/{objectId}/deletion-impact` (`changeSetId` for a change set), returns what
  deleting a record would take with it, live or in a change set, without deleting anything: the records and
  relationships, their counts, the record's own relationship count, whether the delete needs `cascade=true`,
  and the `deletionPreviewToken` that confirms exactly that impact. It needs what the delete needs (Edit live,
  or Work in change sets) and computes the impact with the delete's own code, so the two always agree. The
  delete dialog reads it when it opens, shows what is lost with one danger button, and deletes under that token;
  if the impact changed meanwhile it shows the fresh impact once and asks again, and if it cannot be read it
  says so and offers Retry.
- **The model editor.** An operation with one or two controls (42 of them: renames, keys, value types, a
  pick-several list) opens as a small popover under the control that started it (`ui/AnchoredPopover`), with the
  same fields, checks and undo step as the sheet; three or more controls keep the sheet. The buttons say Save,
  Add ‹thing›, Move or Apply.
- **A table row opens the record beside its list first** (PP-D41), with the list still in place; Expand to full
  page goes to the record's page. On a phone the row opens the page.
- **Search.** ⌘K (Ctrl+K) puts the caret in the search. The top bar's search also finds the workspace's lists by
  name. Home has a search over every record of every workspace the person may browse, grouped by workspace.
- **The workspace's page is redrawn**, at the window's full width. A person's **shelf** holds the lists and other
  views (a matrix, a tree) they bring there from any application, as tiles with the number of records, in their
  own order. A list comes to the shelf by dragging it there from an application, by Add a list, or by the pin
  on the list's own page; a tile is moved by dragging it or from its menu (also on a right click). The shelf is
  kept in the browser. Above it is
  the search; under it the applications with their lists one click away, the person's change sets that wait, and what
  changed by day, with repeats of one change folded ("4 in a row").
- **Home** follows a large window up to 1680px, with more cards across, and shows what waits for the person
  (approvals, their own change sets) before the workspace cards, not after them.
- **A file is chosen or dropped in one place:** the file field is a drop area in every dialog that takes a file.
- **Tables fold their columns on first load**, also in a tab opened in the background. A wide column in the
  middle (a long identifier) no longer hides the narrow ones after it: those that fit stay.
- **Fixed:** a change set's band no longer runs past the page's edge (seen in Website purple): its name and state
  take the first row and its actions a row of their own when they do not fit.
- The guide and the API reference know Current and Website purple only and show the other themes in Current.

### Changed (0.17 PL1 and PL2: change sets in two clicks, plain add and edit)

- New change set asks for a name only; the start point and the model version are under Options (the version list
  is offered only to Model release). The change set bar holds Review changes and Publish, with Validate now,
  Change model version, Rename and Discard under ⋯. Publish checks first: if the check passes, one plain
  confirmation names the records and relationships that go live and what happens on a conflict; if it fails,
  nothing is published and the page lists the problems with links to the records. A model-version mismatch is
  said in words instead of a disabled Publish.
- Adding a record from a page says "In ‹parent› · Change" instead of a parent picker (the picker's list no longer
  runs into the next field); required fields come first and are marked, the optional ones wait under More
  fields (n), remembered per type in the browser; missing and wrongly typed values are said under the field,
  never in the browser's bubble. The dialog's line above the title names the collection, the title is "New
  ‹type›" and the button "Add ‹type›". The relate dialog says "Add a ‹type› to ‹record›" where the relationship
  is known, and the words "object", "Connect an object" and "(outgoing)" are gone.

### Added (0.17 MT1: the e-mail template)

- An operator can change how every mail refiroo sends looks. Under Settings › This instance › E-mail template,
  the Operator role edits one template for the instance: Markdown with placeholders for the message's own text
  (`{{content}}`, exactly once), the product's name, the instance's address, the person's name and a logo. A
  PNG, JPEG or SVG logo up to 512 KB can be uploaded and is sent inside each mail. A live preview shows the
  result with sample values, on light and dark paper and as plain text. **Send a test to me** mails it to your
  own address, and **Reset to default** goes back to refiroo's own layout, which is used until a template is
  saved. Invitations, password resets, notices, digests and the mail test all use it, with a plain-text version.
- A template with an unknown placeholder or without exactly one place for the message is refused by code
  (`MAIL_TEMPLATE_UNKNOWN_PLACEHOLDER`, `MAIL_TEMPLATE_CONTENT_REQUIRED`); raw HTML, images and unsafe links in
  the Markdown are not carried into the mail; an SVG logo holding script is refused (`MAIL_LOGO_UNSAFE`).
- **API:** `GET`, `PUT`, `DELETE /api/v1/mail-template`, `PUT`, `DELETE /api/v1/mail-template/logo`, `POST
  /api/v1/mail-template/preview` and `/test`, under the new action `mail-template.manage` in the Operations group
  (the Operator role holds it). Migration `20261201_01` adds the one-row table `mail_template`.
- **Dependency:** `markdown-it-py` (already installed through another package) is now a direct, pinned one.
- Not done: template changes are not written to the security audit; the mail was not opened in a real mail
  client (Outlook may ignore the card's width, and many clients do not draw an SVG logo).

### Changed (0.17 PL5 and PL6: plain words, import file-first, grouped draft steps)

- **Import from a collection opens on the file.** A profile is chosen for the person when exactly one valid
  profile fits the file (they may still pick None or another); otherwise the fitting ones are listed; invalid and
  other models' profiles are not shown. The three loading switches sit under Options with the same defaults.
  A file "fits" by this rule: a JSON Lines file takes no profile, a CSV file takes profiles with a CSV setting or
  a single source, a workbook takes any valid profile.
- **Your changes and Home's latest** fold consecutive steps on one model draft into one expandable line with
  their count ("12 steps on the draft ‹name›"); expanding shows the steps as before.
- **Plain words** on record pages and pickers: "Record unavailable", "Cleared" instead of "Null", "Top level"
  instead of "Root object", "record" where "object" showed, "the workspace's live data" where a workspace key
  showed; a picker's lines show the record's path without the application key. The search also takes a person
  to places by name ("Change sets", "Settings", "Home") under "Go to".

### Changed (0.17 SH1: one frame, one location line)

Frontend only; no engine or API change. The frame said where a person was three to five times and some journeys
changed the data context without saying so; now it says it once.

- **A page for each workspace.** A card on Home opens `/workspace?workspaceKey=…` in the shared frame: a search over
  every type's name in the workspace (the cross-type lookup `GET /objects?search=`; results grouped by type with
  where each stands, Down and Up through them, Enter opens), the applications, the person's change sets that wait
  there, the five latest changes, **Edit model** (WM1's action, `useEditModel`) and a ⋯ menu to Settings ›
  Workspaces (Rename, Access, Approval, Retire) and Copy and move, each left out for a person who may not use it.
  The same search (`WorkspaceSearch`, over `SearchField`) is in the top bar on every page of the workspace.
- **Top bar.** Applications that do not fit go under **More**, the current one always kept among the tabs. In
  Settings the bar shows "← Back to ‹workspace›" (the workspace the person came from, the default one when Settings
  was opened directly, never one just deleted) in place of the application tabs; the Settings link stays current.
- **The band is one row** on desktop: it no longer repeats the workspace and the application (the phone band keeps
  both). A change set's row is its pill, name, change count and state, with who, when, version and model under
  **Details**; the description shows once, on the review page.
- **One line above a record:** "← ‹the list it was opened from›" and the records above it, in place of Back to list,
  the breadcrumb's application and type entries and the repeated type label. The model's `detail.breadcrumbs` and
  `detail.header` flags still decide whether ancestors and the type show (the type once, as the eyebrow, when either
  type flag asks for it; the application entry is no longer drawn). A record's ID and version are under **Details**;
  **Copy ID** is in its ⋯ menu beside Copy link.
- **Settings opens on an index by task** (You; Workspaces and models; People and access; Connections; This
  instance, About last), and its menu uses the same groups. Every page stays reachable under the permission it had.
  `Breadcrumbs` and `TrailBar` are one component (`ui/Trail`): the line says where the page is, with no Back
  button beside it, and an opened item's own name is the page title.
- **A page is titled by its sidebar entry** (`pageTitle`): a type's lenses are tabs under its name; a relation matrix
  placed in a navigation group is its own entry and keeps its name.
- **Browse records is folded** in the sidebar until opened (remembered in this browser) and has no search box of its
  own; the top bar search finds a record across the workspace.
- **A change set opened from the list lands on its changes** ("See the data with these changes" leads to the lists);
  one just started, Continue on Home and the band's link to a person's own open change set still open the data.
- **Tables that fit.** In record lists and a record's relationship tables the name column is never cut and columns
  that do not fit fold behind "Columns · n of m", which is the phone layout's column toggle (`mobile-secondary-column`)
  on a wide screen; widths a person set keep winning. The model list's facts take the width of their values, the draft
  list's names and Home's cards get the room they need.
- **Columns fold by what their content needs.** A folding table measures each column with its cells on one line
  (`measuring-columns`), keeps a column only if its content shows whole (a long free-text value ends in an ellipsis
  past 320px), folds from the right until the rest fits, and then fills its container. Home's cards show the roles
  on one line (the first two, then "and n more", the full list as the line's title and for screen readers) and the
  model name on one line, the tile beside the name. A record header's Details and ⋯ are centred on the title block.
  Settings' index links use the app's link colour. On a phone the Settings drawer leads with "← Back to ‹workspace›".
  The model editor no longer offers "Breadcrumbs start with the application" (the flag is still accepted and does
  nothing). The change set band stays on one row at desktop widths; only the name ends in an ellipsis. The record
  page's side column sticks below the band, not under it.
- **Folding runs on the first rows and fills the room.** A folding table finds its container when its rows arrive (not
  only at mount), and the room the kept columns leave goes to the capped ones up to their content, then to the name.
  Home's card holds tile, name, badge and Follow on one row, with the model and the roles under it across the card;
  the roles end in "and n more" when they shorten.
- **Fixed:** a record's title clipped under the band when the side inspector opens (the inspector sticks below the band);
  a long version overlapping the draft count in the model list; avatar initials taking a bracket from "Name (temporary)"
  (letters of the name only); a change set's description shown twice on its review page.

### Fixed (0.17 RF7: clean test output)

- **Backend and CI log without warnings.** SQLAlchemy 2.1 deprecations are gone at the cause: no
  `Result.tuples()` (a row unpacks as a tuple) and `DISTINCT ON` is written `.ext(distinct_on(...))`
  (`sqlalchemy.dialects.postgresql`), which needs SQLAlchemy 2.1 (lower bound raised from 2.0). Starlette's test
  client wants `httpx2`: it is a dev dependency and the test harness uses it (the engine itself keeps `httpx`).
  The tests that build an HMAC token to show it refused use a 32-byte key. Actions run on Node 24
  (`checkout`, `setup-python`, `setup-node` v7, artifact actions and Docker actions on their current majors).
  The CI PostgreSQL runs as a step, and its log (with the refusals tests provoke on purpose) is printed only when
  the job failed.
- **Warnings fail the test run.** `filterwarnings = ["error"]` in pytest's configuration, with no exceptions.
  That showed three real faults, fixed: the consumer events read asked for REPEATABLE READ on a connection
  already open, so the level was ignored and the request failed (`begin_snapshot_read`); test doubles that left a
  progress log, subprocess pipes and the fake mail server's TLS sockets unclosed.

- **No button inside a button.** A navigation group's label in the editor tables held its link inside the edit
  button; the link is now a link beside the pencil, which is the edit button (`EditInPlaceValue` `holdsControl`),
  and both are reached by Tab.
- **Unique keys.** The Views table's "Shows" links no longer share a key when a relation matrix shows a type as
  rows and as columns.
- **Test output is checked.** A frontend test that logs through `console.error` or `console.warn` fails and
  prints the message, unless it says so with `expectConsoleError`/`expectConsoleWarn`; the Vitest reporter is
  pinned, so a run in a coding agent's session shows the same output as CI. Two test fixtures were corrected (a
  short `GET /system` mock, a history out of order).

### Changed (0.17 RF3: review findings, frontend)

- **The reset token leaves the address bar.** The application's `/reset-password?token=` page replaces its
  address by the bare path as soon as it has read the token; the token stays in that history entry's state, so
  a reload before the password is set still shows the page, and is dropped once the link is spent or refused.
  The engine's own `GET /oauth/password?token=` page answers a valid token with `303` to `/oauth/password` and a
  `Lax`, `HttpOnly` cookie (`oauth_reset`, 60 minutes, path `/oauth/password`) that holds it, so neither the
  address bar nor the history carries it; a reload shows the page while the cookie lasts, then says the link is
  gone; setting the password ends the cookie. A used or unknown token is still refused at once with `410`.
- **One search box.** Ten search boxes beside `ui/SearchField` use it now (entity lists, access list,
  explorer, record panels, relation panels, restructuring, tree move, mapping and matrix candidate searches);
  the field gained `type`, `autoFocus` and `disabled`. The record checklist, the field menu and the matrix
  cell filter keep their own markup (their own look).
- **No event is lost across a reconnect.** The event stream client sends `Last-Event-ID` when a stream gives
  `id:` lines (the engine's do not), and dispatches `reconnected` when a connection follows an earlier one; the
  inbox reads its lists again then. The job stream needs nothing: each event carries the whole job.
- **Pages load when opened.** The application, Settings, notifications, change set review and navigation group
  pages are their own chunks; the sign-in and reset screens no longer carry the application. The entry script
  is 208.7 kB (was 2,108.8 kB for everything).

### Security (0.17 RF4: review findings, build and deployment)

- **Pinned versions.** Claude Code in the engine image is installed at a named version (`ARG CLAUDE_CODE_VERSION`, default 2.1.295) instead of the newest on the day of the build. Every base image is named by tag and digest (`node:22-alpine`, `python:3.14-slim`, `nginxinc/nginx-unprivileged:1.28-alpine`, `postgres:17-alpine`, `caddy:2`, and CI's `postgres:17`). The backend has a lock: `backend/constraints.txt` (every runtime and development dependency, made with `uv pip compile`), which the image's `pip install` and CI use as constraints. How to move each is in OPERATIONS, Deploying.
- **The application has a content security policy**, sent by `web` (`frontend/nginx/snippets/csp-app.inc.template`): everything from its own origin, no inline script, no plug-in, no other base address, no frame. The theme script that sat inline in `index.html` is now `public/theme-init.js`, so scripts need no `'unsafe-inline'`. What the engine serves keeps its own policies (sign-in pages, guide, API reference); `web` adds only `frame-ancestors 'none'` to them, as before.
- **CI has a `permissions:` block** (`contents: read`); the image workflows already had theirs.
- **`AI_AGENT_SANDBOX=container` is set in the engine image and in `compose.yml`**, so a container never runs the assistant session without it, whatever `.env` says.
- **The engine believes forwarded addresses only from the compose network's private ranges** (`FORWARDED_ALLOW_IPS`, default `10.0.0.0/8,172.16.0.0/12,192.168.0.0/16`), not from every address (`*`). Behind another proxy, set it in `.env` to that proxy's range (OPERATIONS, Deploying).

### Security (0.17 RF5: assistant sessions in a container)

- **A session in a container cannot read another task's folder or transcript, or another running session's environment, and permissions are the barrier, not a name.** Each task has a folder (its gate) under a random name in `data/assistant`, which session users may enter but not list (mode 2710). The gate belongs to the engine alone (0700); for the length of a turn it is given to the group of the one session user that runs it (0710), so no other session user and no session between turns can enter it. It holds `work` (the working folder and `$TMPDIR`), `claude` (the task's own `CLAUDE_CONFIG_DIR`; the image sets none and the shared `assistant-claude` folder and volume are gone) and the engine's stream log of each turn (mode 0600). They are made once, before any session runs, where a session has no write right; afterwards the engine never changes a mode or writes in them by following a path a session controls: files it hands the session are made through a directory descriptor with `O_NOFOLLOW`, what it reads (`proposal.json`) is a plain file of at most 8 MiB, and the turn's log is read through the descriptor it opened.
- **A pool of session users, each with a group of its own.** The image creates `assistant-1` to `assistant-N` (build argument `ASSISTANT_USERS`, default 8), each in its own group (the engine's user is a member of every one) and in the common group `assistant`, each with a home of its own. A turn takes a free one through an exclusive lock on a file in `data/assistant-slots`; two sessions at once are two users. With none free the turn does not start: the task fails with a note naming `ASSISTANT_USERS`.
- **A reset around every turn.** The sudoers rule names the pool and two commands: the Claude Code binary and `/usr/local/bin/refiroo-session-reset` (root's, not writable). Run as the session user, never as root, before and after each turn, it makes that user's files in the task group-readable and writable (so the next turn, under another user, can resume the session), empties its home and its files in `/tmp`, and ends every process it runs. After the second review the reset ends every process of the user first, repeatedly until none is left, then empties the home and `/tmp`, `/var/tmp` and `/dev/shm`, then makes the files group-readable, and ends processes once more; it runs before the gate opens (a failure fails the turn and opens no gate) and, after a turn, while the gate is still open, which closes right after; the folders reach it on standard input, not on its command line. A reset that does not finish before a turn fails the turn. `compose.yml` gains `init: true` on the engine service, a reaper for the processes the reset ends. A gate left open is read again through its descriptor once its user's lock is held before it is closed. After the third review the reset also removes the user's System V shared memory, semaphores and message queues and its files in `/run/lock`, `/dev/mqueue` and `/var/mail`, and a turn closes every gate still open for its user's group (left by an engine killed mid-turn) before it opens its own.
- **Nothing secret on the command line.** In a container the words go to the session's standard input and the `filesystem` and `network` parts of `--settings` (inert there) are dropped. The session ID stays on the command line, as stopping a left-over session finds it there.
- **A named list of passed variables** (`PASSED_NAMES` in `agent.py`) replaces the `ANTHROPIC_*`, `CLAUDE_*`, `AWS_*` and `NODE_*` patterns, in the engine and in the sudoers `env_keep`: the provider's credentials (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`), `ANTHROPIC_BASE_URL`, the model variables, `NODE_EXTRA_CA_CERTS`, and Bedrock's names only when `CLAUDE_CODE_USE_BEDROCK` is on. A unit test holds the Dockerfile's line equal to the list. **A variable passed before by pattern (`CLAUDE_CODE_USE_VERTEX`, `ANTHROPIC_CUSTOM_HEADERS`, an `AWS_*` name with Bedrock off) is not passed now.**
- **At the upgrade** the first sweep moves each task's folder into the new layout, storing its random name first, closes `data/assistant` to listing and closes every gate no turn holds; a folder no task names is removed only after an hour. Transcripts of tasks begun before the upgrade stay in the old `assistant-claude` volume and are not moved: such a task starts a new session, with its files, when the person next tells it something. `compose.yml` no longer mounts that volume.
- **Known limits, in OPERATIONS:** the provider's key or token still reaches the session, and nothing limits where a session connects. A relay in the engine that kept the key from the session was offered and left out by the user's choice of 2026-11-11. A third: isolation between tasks inside one container rests on Unix permissions and the reset around each turn, reviewed twice with defects found each time; a container per session is stronger and is not built.

### Security (0.17 RF6: webhook addresses on private ranges)

- **After review:** a NAT64 address (`64:ff9b::/96`) is judged by the IPv4 address in its last 32 bits (so a private or link-local one is refused), and the local-use NAT64 range `64:ff9b:1::/48` is refused unless the setting is on (link-local always). The refusal an author reads no longer names the address a host resolves to; the delivery log keeps it, as before RF6. A subscription edit or resume looks the host up before it locks the subscription's row.
- **A webhook address on a private range is refused by default.** A subscription whose URL is, or whose host name resolves to, a loopback, private (RFC 1918), unique-local, shared (100.64.0.0/10), unspecified, multicast, reserved or IPv4-mapped address of any of these is refused when it is created or edited (`400 INVALID_WEBHOOK_URL`, saying private addresses are refused on this instance) and again at every delivery, with every resolved address checked and the connection made to an address that was checked. A refused delivery is a failed attempt of kind `address` in the delivery log. Link-local addresses (cloud metadata) stay refused whatever the setting says. Redirects are still not followed.
- **New setting `WEBHOOK_PRIVATE_ADDRESSES_ALLOWED`** (off by default) allows the private ranges, for receivers inside the organisation's network and for development; plain HTTP to `localhost` works only with it on.
- **Existing subscriptions on private addresses stop delivering until the setting is on:** their batches fail with `address` and the delivery log says why. Set the setting before upgrading when receivers are inside the network. A sign-in provider's requests keep their own rule.

### Changed (0.14 VD: the API documentation discrepancies resolved)

The 20 open discrepancies between `docs/API.md` and the code, decided by the user 2026-11-11: API.md is corrected where the code is right (11), the code is fixed where it is wrong (9). Contract changes are named as such.

- **`docs/API.md` corrected (no code change):** the feed needs the Feed action group (`feed.read`); `WORKSPACE_ADMIN_MUTATIONS_ENABLED` switches the workspace operations and Workspace administration (`workspaces.manage`) guards who uses them; `GET /system/configuration` has the setting group `ai`; `POST /objects` lists the live answers (`422 INVALID_OBJECT_TYPE_FOR_APPLICATION`, `404 UNKNOWN_APPLICATION`) and the change set's (`OBJECT_TYPE_NOT_IN_APPLICATION`, `422 UNKNOWN_OBJECT_TYPE`, `422 PARENT_WRONG_SCOPE`) separately; the at-least-one-of rule in a change set is left to validation by an update and an attribute `POST`/`PATCH` and checked at once by a create and an attribute `DELETE`; a stale version on a cascading delete is `409 DELETION_PREVIEW_CHANGED`; the workspace edge list takes `seek`; `CHANGE_SET_SOURCE_INVALID` is no longer listed (it can never be answered: the request schema, with `derivedFromPublicationId`, refuses the same cases with `422 REQUEST_VALIDATION_ERROR`); a model release's `PATCH`, `DELETE` and `…/raising` are always registered and guarded by `model.install`, and `PATCH` only retires or reactivates; an AI call's `purpose` has all eight values; `design.outline`'s `name` is only in the assistant's outline.
- **Contract change: attribute `POST` and `PATCH` in a change set** answer the record's `path`, filled as the object writes do (it was empty).
- **Contract change: `GET /objects/{type}/{id}/parent-candidates` no longer takes `publicationId`.** A request that sends it is refused `422 UNKNOWN_PARAMETER`; the model is selected by `workspaceKey` or `changeSetId`. The operation's access check no longer reads `publicationId` either.
- **Contract change: an export job's `parameters` hold the request as it was sent**, by alias (`not`, not `not_`) and without what the request left out (no `view`, `layout`, `people` as null). A job stored before holds `not_` and is still read.
- **Contract change: `POST /agent-access/applications/{id}/block` and `/restore` answer `signedIn`** with the people who have an open session for the assistant, as the list does (it was always 0).
- **Contract change: `ModelMappingOperationEntry` has `removed` and `migration`** as a draft's history entry does (always empty for a mapping).
- **Contract change: `ModelCompatibilityResponse.classification` lists `compatible` and `migration_required`.** `invalid` is produced by one answer only, `compile` of a draft that does not compile, so `CandidateCompatibilityResponse` keeps it and its reference line says so.
- **Contract change: `AiTaskResponse.check` is `DesignCheck`.** `TaskCheck`, `CheckTable`, `CheckFix`, `CheckSummary` and `RefusedGroup`, which no code produced, are removed from the document and from the frontend types.
- **`POST /moves`** describes `mode` and `stage` in the router's description; `MailMessageResponse.kind` and `lastErrorKind` name `digest` and `stopped`.
- The reference text and its recorded examples follow each change; the OpenAPI lock is re-baselined on the tree as it stands.

### Added (0.14 V9: the management API reference, webhooks and the close of Track V)

- **`consumer subscriptions` is documented on `/docs/api`** (11 operations): create, list, read, edit, suspend, resume, rotate the signing key, delete, the deliveries, one delivery and the resend of an event. The overview says what a subscription is and the sequence a receiver follows; how a request is signed and verified, batched and retried, and why a subscription is suspended, are in the fields that carry them. The recorded examples come from a test that starts a receiver on the same machine and stops it again: it answers `503` once, so the examples show a request being retried and then delivered, and a resend signed with both keys after a rotation. The signing key is a placeholder in every example.
- **A schema's own description can be written in the content files** (a line of plain text under its `### Schema` heading), replacing the one in the code. All 254 schemas whose description named a package, a decision or a release got one, as did 33 field descriptions and two parameter descriptions; a test fails on any description in the document that carries such a number.
- **The reference is checked for completeness** by `backend/tests/test_reference_complete.py`, which replaces the gap list (`reference_gaps.json` is deleted): every operation has its section and example, no parameter or field is undescribed, every code the backend raises has a catalogue entry (the extraction now also reads a conditional status and a conditional pick of two codes), every entry is listed on an operation or says it is no response status, every guide link to the reference names a tag or operation it has, and no example holds a secret.
- **The catalogue** gains `APPLICATION_IN_USE` and `APPLICATION_OBJECT_TYPE_IN_USE` (findings of a compatibility check and of a migration), ten entries that are an item's, a job's or a plan's code say so instead of carrying a status, `POST /api/v1/model-drafts/{draft_id}/operations` lists `409 AI_TASK_DRAFT_HELD`, and `UNKNOWN_PARAMETER` and `UNKNOWN_OBJECT_TYPE` say where a subscription's filter answers them.
- **The diagnostic codes of a compatibility check and the item codes of a migration are in the catalogue** (29 entries, each badged as no response status and saying where an integrator meets it: `diagnostics`, the `details` of `MODEL_MIGRATION_REQUIRED`, a migration's items, a publication's merge conflict); the completeness test reads the files that write them, so a new code of these families needs an entry.
- **Every other code a client can meet is in the catalogue** (50 more entries): a change set's whole-graph diagnostics and a publication's conflicts, a move's reasons, a mapping's problems, an import's row errors, a draft's profile warnings, the assistant check's findings, the consumer contract and model validation findings, a subscription's suspension reasons and a backup rehearsal's failures, each badged as no response status; the completeness test reads the files that write them.
- **A link straight to an error code's entry lands on it** (`/docs/api/#management/description/<code>`): Scalar rewrote the address and showed the Introduction. The page's own script now keeps the address, scrolls to the heading once it exists and stops when the reader takes over; checked on the instance page under a root path and on the static build, in light and dark.
- **`docs/API.md` starts with a pointer to `/docs/api`**; the public build of the reference was rebuilt and checked in light and dark. The OpenAPI lock is re-baselined on the tree as it stands (descriptions, summaries and responses only). The management document is 2.52 MB compact; the examples stay in separate files.

### Added (0.14 V12: the management API reference, AI, mail and notifications)

- **`ai`, `mail` and `notifications` are documented on `/docs/api`** (36 operations): the provider's status, test and call records, a question turned into filters, accounts of a model change and of what changed, assistant tasks from their request to the change set they load; mail settings, the test message, the outbox and a person's own notice mail with its digest; the inbox, its stream and following a workspace. Each has its title, a short section, parameter notes, error lines read from its code path and a recorded example on the reference data (the fake provider, the harness's SMTP server and a stand-in assistant session; the examples say which). The `ai` overview states what a provider is sent at each send level. 86 schemas have every field described, the dry run of items among them. The gap list's `ai`, `mail` and `notifications` groups are empty (724 to 143 items). Five differences between API.md or OPERATIONS.md and the code are in `docs/TODO.md`. The OpenAPI lock is re-baselined on the tree as it stands (it holds the other sessions' uncommitted changes).

### Added (0.14 V11: the management API reference, security)

- **`security`, `oauth` and `agent-access` are documented on `/docs/api`** (79 operations): a person's own sessions, password, authenticator app and passkeys; people, their password links and provider identities; groups and members, roles, grants and who has access to a workspace; clients and their secrets; the token signing keys and the security events; sign-in providers and local sign-in; the OAuth endpoints (token, revocation, registration, keys and metadata); and agent access (the settings, agent clients, assistants and calls). Each has its title, a short section, parameter notes, error lines read from its code path and one recorded example on the guide's reference data; the three overviews say who may do what and how a client signs in. Every field of the 77 schemas they use is described, and the gap list loses the three groups (1,176 to 724 items). No real secret is in an example: client secrets, tokens, reset links, authenticator seeds, recovery codes and passwords are replaced by fixed placeholders when the examples are written (`SECRET_MASKS`). Passkeys and the provider sign-in are made as a browser makes them, with the harness's software authenticator and OpenID Connect provider.
- **The model administration operations list `404`, not `405`, for a switched-off setting**: their addresses do not exist while `MODEL_ADMIN_MUTATIONS_ENABLED` is off, so the framework answers `404 HTTP_ERROR`; the `405` text of V8 and the catalogue's `HTTP_ERROR` entry were wrong for them (the model mappings' and workspaces' lines were right). The OpenAPI lock is re-baselined on the tree as it stands (descriptions, summaries, examples and responses only; it also holds other sessions' uncommitted changes).

### Added (0.14 V8: the management API reference, the model)

- **`model`, `model administration`, `model mappings` and `moves` are documented on `/docs/api`** (64 operations): model reads, releases with their diffs and activations, validations, drafts with their operations, outline, consumer API reads, dry run, inference, installation and migrations, model mappings with their operations and inference, and moves. Each has its title, a short section, parameter notes, error lines read from its code path and one recorded example on the reference data, including a second release of the Graubünden model, a third it is migrated to, a second model and a move between workspaces on the two models. The four overviews are short; the model's concepts are in the schema fields (about 1,450 gap items emptied).
- **Every operation kind is a schema with typed, described parameters.** The 66 draft kinds and the 12 mapping kinds (`Mapping<Kind>Operation`) each list their parameters with types, which are required (and when a parameter is needed only under a condition) and what they mean; `POST /model-mappings/{key}/operations` takes the union of the mapping kinds, as the draft route takes its own. The schemas only describe: the kinds keep checking and keep their refusal codes. The three kinds only the server writes appear in the history reads. A unit test holds both registries and their schemas in agreement. `engine/moves/mapping_kinds.py` now declares its parameter names once (`PARAMETERS`). The OpenAPI lock is re-baselined.

### Security (0.14 V8)

- **`POST /imports` with `sourceFileId` no longer reads a file the caller may not use.** A caller with Bulk and import in one workspace could import another workspace's profile file, or an assistant task's workbook, by naming its ID. The import now applies the rule of the source file routes through one shared check: `403 FORBIDDEN` for a profile's file of a workspace where the caller has no Bulk and import (the uploader still may), `404 SOURCE_FILE_NOT_FOUND` for a task's workbook.

### Added (0.14 V7: the management API reference, jobs, imports and source files)

- **`jobs` (with `exports`), `imports` and `source files` are documented on `/docs/api`**: batches with every item kind, exports, jobs (read, list, outcomes, rows, file, events, cancel, confirm, read again), import profiles and their checks, imports, and stored files with their profiles (30 operations). Each has its title, a short section, parameter notes, error lines read from its code path and one recorded example on the guide's reference data; the import examples use the guide's fictional bus company workbook. Every field of the schemas they use is described, and the catalogue gains 29 codes (an import profile's problems, an import file's mismatches, an item's reasons, an import's notices and `IMPORT_PROFILE_MODEL_MISMATCH`). The gap list loses the three groups (3,222 to 2,622 items). The OpenAPI lock is re-baselined on the tree as it stands, which also holds other sessions' uncommitted changes.

### Fixed (0.14 V7)

- **`/docs/api` and `/openapi.json` work with an optional surface off.** The reference text named operations that `WORKSPACE_ADMIN_MUTATIONS_ENABLED=false` or `INTEGRATION_JOBS_ENABLED=false` remove, and the document could not be built. Text for something the document lacks is now skipped when the application builds it; the tests merge it strictly into the all-capabilities document and build the document with each optional surface off.

### Added (0.17 SA1: sign-in managed by an administrator)

- **A person's sign-in can be managed by an administrator** (`signInManaged`, default false). It is read on `GET /me` and on every read of a person, accepted by `POST /users` and changed by `PATCH /users/{id}` with the person's `expectedVersion`, and shown as one checkbox on the person's form (new and edit). Migration `20261129_01` adds `users.sign_in_managed`.
- **While it is on, the person's own credentials are out of their hands** (`403 SIGN_IN_MANAGED`, one rule in `engine/identity/managed.py` that each own-credential operation calls before it checks anything else): changing the password, starting, confirming or removing a second factor, new recovery codes, and registering, renaming or removing a passkey (the engine's registration page too). `GET /me/sessions` lists only the session of the request, and ending another session or all of them is refused; signing out the own session works.
- **A forgotten-password request for a managed address answers as for any address and queues nothing.** An administrator's reset link and its page, removing a second factor or a passkey, and signing a person out are not refused. An instance that requires a second factor no longer asks a managed person without one to set it up at sign-in.
- **The account page hides the password, passkeys, second factor and other-session parts for such a person** and says in one line that an administrator manages the sign-in. The security log words the change as "Sign-in managed by an administrator" or "Sign-in no longer managed". The OpenAPI lock is re-baselined (additive).

### Added (0.14 V3: the management API reference, its conventions, catalogue and first areas)

- **The reference text is merged into the OpenAPI document** from `backend/app/management/reference/content/`, shipped as package data: `index.md` (signing in, the error envelope), `errors.md` (the error catalogue, each code an anchor on `/docs/api`, its status a badge), one file per tag (a short overview, one section per operation headed by method and path with its title, parameter notes and error lines, and a `## Schemas` section whose field lines become the schemas' property descriptions) and `examples/`; `README.md` there is the writer's guidance (one recorded example per operation). A section naming a route that does not exist fails when the document is built. Each operation lists its error responses by status, each code linked to its catalogue entry. `index.md` holds the conventions; `errors.md` the 347-entry catalogue (every code the backend raises that a request can reach). `workspaces`, `system`, `changes` and the two health checks are written in full, with 21 recorded examples; the other areas follow, each emptying its group of `backend/tests/reference_gaps.json`, which may only shrink (`test_reference_gaps.py`). The examples' request and response bodies are files the document references (`externalValue`), served at `/docs/api/examples/…` and written by `static_site`; the page makes the document address absolute so Scalar loads them. A change to a management route updates its text and examples in the same change (`AGENTS.md`).
- **A `reference` test group records the examples** from a run on the guide's reference model and its `docs` set: `RDM_RECORD_EXAMPLES=1 python -m pytest -m reference` writes them normalised (stable placeholders for IDs, times and cursors) and short; without it the steps only assert status and code.

### Added (0.14 V4: the management API reference, records)

- **`objects` and `attributes` are documented on `/docs/api`**: create, read, update and move, delete (with the cascade preview), the per-type list, the cross-type lookup, the model-aware query, parent candidates and history, and the four attribute-value operations (13). Each has its title, a short section, parameter notes, its error lines read from the code (live and change set, which word several refusals differently) and one recorded example on the guide's reference data; the 28 schemas they use have every field described. The gap list loses its `objects` (204) and `attributes` (37) groups. Where `docs/API.md` and the code differ, the reference follows the code and `docs/TODO.md` lists the five differences found.
- **A parameter note can name a parameter with placeholders** (`filter.<field>.<operator>`), so the list's filter family is described.

### Fixed (0.14 V4)

- **The reference's example files load when the instance runs under a path prefix.** Their addresses are relative to the document, so they follow its `root_path`; the static build still writes its own.
- **The guide's links into the reference point at tags the document has**: `#tag/clients` is `#tag/security` and `#tag/mappings` is `#tag/mapping`; the consumer API index, which is not in the management document, is linked without an anchor. The OpenAPI lock is re-baselined (descriptions, summaries, examples and responses only).

### Added (0.14 V5: the management API reference, relations and mappings)

- **`relations`, `mapping` and `relation-matrix` are documented on `/docs/api`** (18 operations): add, list, read, change, remove and batch relationships, the grid change, the held read, the workspace edge list and the relationships grid; the mapping coverage, candidates, targets, replacement and AI proposals; the relation matrix and its two cell reads. Each has its title, a short section, parameter notes, its error lines read from the code (live and change set) and one recorded example on the guide's reference data; the 41 schemas they use have every field described. The gap list loses its `relations` (116), `mapping` (129) and `relation-matrix` (73) groups. The error catalogue gains `RELATION_BATCH_REFUSED`. Where `docs/API.md` and the code differ, the reference follows the code and `docs/TODO.md` lists the one difference found (`seek` on the workspace edge list).
- **An operation with several tags is written in the file of its first tag** (`content/README.md`), so the edge list and the relationships grid, tagged `mapping` and `relations`, are in `mapping.md`. The OpenAPI lock is re-baselined (descriptions, summaries, examples and responses only; it holds the tree as it stands).

### Added (0.14 V6: the management API reference, change sets and publications)

- **`change-sets` is documented on `/docs/api`** (23 operations): list, start, read, rename, discard and move a change set onto another release or onto the workspace's release (a `migration` job), its record and relationship changes, the check, the restructuring plan and apply, publishing, the submission, withdrawal and decision, the publication requests, the approval policy, and the publications with their withdrawal. The overview says how a change set merges onto live data, what a conflict is, how approval works and what a publication snapshot is. 80 schemas have every field described (424 fields), including the job, export, binding report, move and migration summaries the migration job returns. Each operation has one recorded example (`tests/test_reference_change_sets.py`: a change set with a new stop, a corrected name and a stop moved by a restructuring is reviewed, checked and published; the workspace then requires an approval by a second person, made through the API; a change is submitted, sent back, withdrawn, resubmitted and approved; the publication is withdrawn; one change set is discarded and two are moved onto a second release).
- **The error catalogue** says what a publication's `VERSION_CONFLICT` carries (`details.conflicts`, their codes and the mapping-set count).
- **Fixed in the earlier areas' text:** the pinned-model refusals (`UNSUPPORTED_PINNED_MODEL_SCHEMA`, `PINNED_MODEL_INVALID`) were listed as 422; the engine answers 409, as the catalogue says. The OpenAPI lock is re-baselined on the tree as it stands (it holds the other sessions' uncommitted changes).

### Fixed (0.17 SA1)

- **A link a person asked for does not outlive the switch.** Switching `signInManaged` on removes the links the person asked for by e-mail address, and such a link of a managed person is refused as an expired one; an administrator's link still sets the password.
- **Closing the grant dialog no longer asks to discard changes when nothing was changed.** The dialog compared the person, group or client it was opened for by object identity, so any refresh of the page behind it made it count as edited, and Escape or Close then asked "Discard your unsaved changes?". It now compares by ID. Found through the security browser runner, where the step failed now and then.

### Fixed (0.17 RF2: review findings, engine)

- **After review: using a password link ends the person's other links, and a link the person asked for stops working when an administrator manages their sign-in.** Setting a password through one link deletes the others in the same transaction, so a link asked for beside an administrator's cannot set the password again. Switching `signInManaged` on deletes the links the person asked for (an administrator's link stays), and a requested link of a managed person answers `410 link_gone` on the page and when used.
- **A CSV export holds no text a spreadsheet runs as a formula.** A name, path or `text`/`longText` value starting with `=`, `+`, `-`, `@`, a tab or a carriage return is written with a single quote in front (the OWASP rule), in PostgreSQL where the file is written. Numbers, dates, booleans and JSON are as stored, so a negative number stays a number. XLSX already wrote every text as a text cell and is unchanged. A text that already starts with quotes and then such a character is escaped too, and the import of the table layout from CSV takes exactly one quote off the name and text columns, so an unchanged export sent back changes nothing (a real `'=x` is written `''=x` and read back `'=x`); a hand-made `'=x` imports as `=x`.
- **Placing new matrix cells in an import reads once.** `PlaceReads` keeps the records of a set of types, the cell counts of a view and the containers in use, each read by one statement for the whole import instead of once per column record; the places chosen are the same.
- **Two first sign-ins of one new person through a provider at once make one person.** The person is created in a savepoint; the second sign-in, failing on the address or the subject the first just made, finds that person and signs in. Matching by e-mail stays refused (D363, 0.12 I3), so `email_verified` is not consulted.
- **A forgotten-password request no longer cancels a link an administrator made.** `password_reset_links.requested` (migration `20261130_01`) marks links an ask made; an ask replaces only those, an administrator's link still replaces every earlier one.

### Fixed (0.17 RF1: review findings)

- **Approving a change set no longer risks a deadlock with publishing it** (RF1-F1). A decision that publishes now takes the workspace's lock before the change set's, through the one function publishing uses (`lock_workspace_for_publication`), so an approval beside a direct publication or a change-set move of the same change set waits instead of ending in PostgreSQL's deadlock error. Sending a change set back keeps its lighter lock.
- **Reading an import preview again never touches a confirmed import** (RF1-F2). The re-read locks the waiting preview, replaces it in the transaction that commits the new one, and removes the old file only after that commit. A preview confirmed meanwhile is refused with `409 JOB_NOT_AWAITING_CONFIRMATION`: nothing is created and the confirmed import is not cancelled.
- **A failed file cleanup no longer keeps background work off** (RF1-F3). When clearing the job files a stopped process left behind fails at start, the failure is logged with its cause, the job worker, exporter, assistant, listener, deriver and dispatcher start anyway, and the cleanup runs again at the next start.

### Fixed (0.17 CA1: the Apply dialog names a consumer API's changes)

- **A change to a consumer API shows in "What changes in the model".** Renaming or re-sourcing a field of a released related block (the parent's or the object's) is a breaking change that needs a higher contract version, but the Apply and Install dialogs listed no difference for consumer APIs and said "Nothing new", which read as the edit having done nothing. The model diff now names the consumer API by its key, and the dialogs list "Consumer APIs changed: <name>" beside the contract notice that offers the version raise.

### Added (0.17 CA1: the parent carries fields and related blocks)

- **A consumer API's parent serves what the object can** (PP-D29). `object.parent.fields` is written as the object's `fields` are: an output name to its sources (`objectType`, `id`, `code`, `name`, an attribute a parent type binds, or `ancestor:<type>.<field>`), `null` where the record's parent has none; and `related` blocks written as the object's. One level: the parent has no parent. The short list form still works: a built-in name keeps its role's output name and any other source is served under its camelCase words (`master-id` is `masterId`). A parent source no parent type can read, a parent block over a relation no parent type has and an object block named `parent.…` are refused at the pointer the author wrote. Read in the same statements as the object's blocks, however many records a read holds.
- **A related block is served always or on request** (PP-D30). Every related block, the object's and the parent's, takes `served` (`always`, the default, or `onRequest`). An on-request block is read and served only when the request names it in `include` (`include=translations&include=parent.systemVariants`, repeated or comma-separated) on get by ID, lists and XREF, and in each item and in `defaults` of a batch resolve; a name that is no on-request block is `400 UNKNOWN_INCLUDE` with `details.valid`. The OpenAPI document lists the names as an enum on those operations and types an on-request block as an optional property; `include` is a reserved filter name. Events and deliveries leave on-request blocks out.
- **An On related filter may name a block of the parent** (PP-D31, PP-D32): `onRelated: "parent.systemVariants"` limits that block as it limits the object's, and `keepOnlyMatching` drops the results whose parent has no match; the filter narrows the results without `include`, and the block is then not served. `crosswalk` stays on the object's own blocks.
- **Events follow what the parent shows.** A change to an attribute or an ancestor field the parent reads, to an item of one of its related blocks, or a relationship it gains or loses makes `updated` for each child of that parent (output: the parent's).
- **The contract check:** adding parent fields, parent blocks, `include` and filters is compatible; serving a block only on request that was served always is a breaking change that needs a higher contract version. Every existing definition answers exactly as before.
- **The editor's Fields tab has a Parent section** (its output name, its fields chosen from the built-in names and the attributes of the parent types, and its related records with Add related), the related tables have a **Served** column (Always or On request), the Operations tab lists the names `include` accepts, and the filter dialog's block picker offers the parent's blocks; an On related filter's Matches on lists every field of the records the block reaches (as its Fields… picker does, the system a value sits under included), for the object's blocks too.

### Added (0.17 EX1: Export says what it exports)

- **An export can name a view** (PP-D18). `POST /exports` takes `view` (application, view key, the page's state, the field a link matrix's cells list) in place of `scope`; the engine derives the file from the view: a table, a tree (a sheet per type), a relation matrix that creates or links, a relationships table or grid, a mapping grid. Every list view hands its state to Export through one hook in the view host; the dialog opens on **This view**, then the type, the application or the workspace, for editing or (a table, a type, an application, a workspace) technical, and asks where a matrix's new cells go.
- **A type, an application or a workspace for editing is a sheet per type** (PP-D21): fields, parent by name (by hidden ID where names clash), relationships by name, loaded from the later sheet only; the file imports back unchanged.
- **Every XLSX export has an "About this export" sheet**, second (PP-D22): what was exported, what it holds, how it loads back, where new matrix records go.
- **Import profile, generically**: `relatedRecord.idColumn` (a related record named by an ID cell, `parent` optional) and `relation.within` (a column's part of a relation set). A record is written in its own application, a cell's `not loaded` pair is left out whole, and an empty set on a required relationship that is already empty is unchanged, not refused. `suggestedContainerId` on the matrix containers read. Additive contract change.
- **The Export dialog says what "This view" holds**: rows × columns (a table, a relation matrix, a relationships grid), rows (a relationships table) or records (a mapping grid, a tree), with the change set, publication or live data it is read from, counted as the page counts it (the same filters, search and change set); nothing is said of a size the page does not know. No API change.

- **A new matrix cell goes where the relationship's candidate rules allow** (PP-D24, MC1 and EX1). The containers read, the cell dialog, the export and the import offer or use only the containers a record created there meets the `ancestor:<type>.<field>` criteria under, found by the candidate evaluator the write rule uses. Equalities on one ancestor type that the model lets sit under the column fix one place; when the column has none, creating a cell creates that place with its values and the record in one change (the dialog sends one atomic batch and says "(will be created)"; an import adds the place as its first item). Criteria that fix no place create nothing: the place is then the container under the column that already holds cells of the view (the one holding most; none on a tie), and a container holding no cells is never preselected or used automatically, even as the only one; the dialog lists it under "Other groups (not used in this view)", and an import refuses a new cell there in plain words. `GET …/relation-matrix/containers` reports `derivedPlace` and each container's `cellCount`; `suggestedContainerId` is gone.
- **A matrix export asks which field a cell lists** (PP-D25). `view.cellField` (the name, the display attribute or a unique text attribute of the cell type) replaces `newCellContainers`; the dialog's container section is gone. The file records the choice (`relation.within.field`) and an import reads it back; a value finding two records is refused, naming its row.
- **An import shows how a matrix or relationship column is read, before anything is written** (PP-D26). A file that does not record a column's field is guessed in the database from the column's existing records and says so. The binding report's column `reading` and the preview section "How the file is read" give the field, the values matched, where new records go and a choice of another field; `POST /jobs/{jobId}/reread` runs the preview again; the choice can be saved into the stored profile. Profile: `relation.within.field`, `relatedRecord.under`.
- **A link matrix's export has a value sheet per column** (PP-D27, EX1). Each column's records (those the column offers and those linked in it) are listed as full rows in an Excel table, "Values · <column>": every bound field, the group and the record's ID and version, hidden. The main sheet's cells list the chosen field (any text field of the cell type, the name by default; the unique-only rule of PP-D25 is gone) and their warning-style dropdown reads the sheet's column through a defined name over the table column, so a renamed or added row shows in it and free typing is allowed. The import reads each sheet as a source (`Source.under`): a row with an ID is an update under its version, a row without one a new record in the column's place (where the view creates; a view that only edits refuses it), a main-sheet value equal to a value-sheet row's field is that record, a value typed in both places is one record, a value found in neither is a new record named by it (holding it in the field when that is not the name), and a row nothing picks is still created. All of it is set-wise in the database (`import_value_rows`). A matrix whose cells hold the record's own fields has no value sheet. The binding report's reading counts a sheet's `updatedRows` and `newRows` and a column's `fromValueSheet` and `createdValues`. Decided by recommendation: a created record's name is the value, plus the attribute when the field is not the name; link-only views get the sheet for reading and the dropdowns, with new rows only where the view has `create`; the value sheet carries a hidden version beside the ID so an edit is refused when the record changed. The About sheet of a file with such lists has a section "Editing in Numbers": Numbers turns a cell list into a pop-up menu that takes only its items, so it gives the few clicks that make the cells plain text (Format, Cell, Data Format: Automatic) or add one choice; the "New … go into" section now says where the data or a proposal puts a new record instead of the older refusal wording.
- **A column with no group gets a proposed one** (PP-D28, MC1 and EX1). Where neither the rules nor the data give a place, `derivedPlace` is a proposal (`proposed: true`): a new container under the column of the type the view's other columns' containers have, named as most of them are (a tie to the first name), only for a type that asks for no value and only when a group so named meets the binding's ancestor criteria; no model rule is added. The cell dialog says so in a sentence, lets the name be changed and creates the group and the record on one OK (`createObjectInNewPlace`; "Use an existing group instead" keeps the unused groups choosable); an import's preview says "will create group … under …" (`newRecords.typeName`, `under`) and loading the file creates it. The containers read gives `derivedPlace.applicationKey` and each container's `applicationKey`, which the dialog creates the group and the cell in (a record stands in its parent's application; the dialog took the first application that lists the type, which a model listing a type in several applications refuses with `PARENT_WRONG_SCOPE`), and an import creates a new place in its column record's application.

### Changed (0.17 EM1: the e-mail is the sign-in name)

- **A person signs in with their e-mail address; the username is gone** (PP-D14). `users.username` and its index are removed; `email` is required for an active person and unique ignoring case (`409 EMAIL_TAKEN`, which replaces `USERNAME_TAKEN`; `422 EMAIL_REQUIRED` for an active person without one, also when restoring one who has none). A deactivated person may have no e-mail, which frees the address (PP-D16). The password page, the application's JSON `password` step (`{request, email, password}`), the reset request (`{email}`), the failed-sign-in counter (per e-mail, case folded) and the rule that refuses a password equal to the account name (`PASSWORD_REJECTED`, `details.reason` `email`) all use the e-mail. `POST /users` takes `{name, email}`; `UserResponse`, `MeResponse` and the sign-in answers carry `email` and no `username`; a group's members read `email`; adding members takes an ID or an e-mail; `create_admin` takes `--email`; the Users pages, the New person dialog (which also asks for the e-mail of a person restored without one) and the member pickers show and ask for the e-mail. New security events record `email`; events from before keep the `username` they recorded. The OpenAPI lock is re-baselined (breaking, pre-1.0).
- **A provider's person needs an `email` claim** (PP-D15). Matching stays by provider and `sub` (D363), never by e-mail. A first sign-in without the claim is refused (`no_email`, the message names the claim and that the provider's administrator adds it); an address another person holds, active or deactivated, refuses it (`email_taken`, `403`; a security administrator resolves it, OPERATIONS). At later sign-ins the e-mail follows the token unless another person holds the new one; then the stored one stays and the sign-in succeeds. Linking an identity onto an existing person frees the deactivated person's address.
- **The migration `20261128_01` stops on what it cannot settle** (PP-D17). An active person without an e-mail whose username is an address takes it as the e-mail; if an active person still has none, or two people share an address ignoring case, the upgrade stops and names them, and nothing is invented. Check an instance for active people without an e-mail and for shared addresses before upgrading.

### Changed (0.17 MC1: reuse or create in any matrix cell)

- **A filled matrix cell offers Create as well as Link existing** (PP-D23), each where the view's `cellActions` hold it. Create showed only for an empty, inactive or history-only cell. A cell that may hold only one record keeps today's dialog: the binding's `uniqueToAncestorTypeKey` is the column type read outgoing (the cell's conflict rule), or its cardinality lets the row's end hold one. A record created from a filled cell uses the same form and container choice as from an empty one, and the engine's uniqueness checks still refuse what the model forbids. Frontend only; no API change.

### Fixed

- **Settings › Integration › API reference and Consumer APIs follow a chosen workspace.** A workspace choice at the top of both pages (shown when more than one workspace is available, kept in `?workspace=<key>`) lists that workspace's consumer APIs, and the links to the reference page and the OpenAPI documents carry it, so a non-default workspace's consumer APIs open on `/docs/api`. Without a choice the default workspace is listed as before. The application also remembers the workspace being worked in (`refiroo.workspace`, shared with the documentation site and the reference page), so `/docs/api` opened from the "?" help link and the guide header lists that workspace's consumer APIs; an explicit `?workspace=` in the address always wins. The OpenAPI document of a non-default workspace marks `workspace` required (that key the only value), so a test request composed from it from the reference page reads that workspace instead of the default and no longer answers `403 FORBIDDEN`. A consumer token asking for a key the requested workspace's model does not declare now gets `404 CONSUMER_API_NOT_FOUND` (as `docs/CONSUMER_API.md` says), with `details.workspaces`, the active workspaces where the client holds a grant of that API, and the message says to add `?workspace=`; a key the workspace declares, read without a grant, stays `403`.
- **A list's search box keeps focus while typing.** In a table, tree or matrix list the box was rebuilt each time its search was applied (250 ms after the last key), so typing slowly or editing the text moved the focus out of the box. It now stays in place while its own search comes back. A search changed outside the box (back, Clear search, an answer in words) replaces the text in every list's box, which the relationships table, mapping grid and matrix did not do before. Frontend only.
- **The public API reference builds from a clean checkout.** `app.management.reference.static_site` imported the application before setting its throw-away `SECRETS_ENCRYPTION_KEY`, and importing it builds it, so a checkout without a settings file stopped with "SECRETS_ENCRYPTION_KEY is required". It now imports the application once the key is set. Found by the 0.16.1-alpha.5 public site build, which was made with this file overlaid.
- **Moving a submitted change set to a new model release keeps it submitted.** Confirming the move used to answer `409 CHANGE_SET_SUBMITTED`. The move now completes and the request stays submitted; approvers decide it on the moved version. Only the submitter or a holder of Approve publications may move it. The request's history shows the step.
- **The Management API page in the API reference offers a client's credentials while signed in.** R13-F35 gave the signed-in person's session token to `engineOAuth`'s client-credentials flow, so the page showed only that token and no Token URL, Client ID, Client Secret or scope. The session token is now a scheme of its own, `signedInSession` (a bearer token, preferred while signed in, renewed as before), and `engineOAuth` always shows the client form with `management` ticked. The auth type list is a multi-select: tick `engineOAuth` and untick `signedInSession` to send with the client's token only. Signed out, only `engineOAuth` is offered. Consumer API pages are unchanged (`oauth2` only, `consumer` ticked, no session token).

### Fixed (wide screens)

- **Application pages fill a wide window.** Lists, relation matrices, mapping grids, relationship tables, trees, record pages, group pages and change-set pages stopped at 1440px with empty margins either side on a wide display; they now span the main column, and its side padding is proportional to the window, so the margin looks the same on every screen: about 1.4% of the width (20px at 1440px, was 32px; about 27px at 1920px and 36px at 2560px), at least 16px and at most 40px. Home, Changes, Notifications and Account keep their reading widths. The browser runner `lb-list-browsing` checks the list card and a relation matrix at 1920 and 2560px, and UI acceptance now names a wide layout (1920 and 2560px) beside the narrow one.

### Fixed (the 0.13 release review)

Findings of 0.13 R's full review of every change since 0.16.0, numbered R13-F1 onwards.

- **`sc07` brought up to date.** Its large-set step expected the starter's 25-target row to be `ambiguous` / "Ambiguous (25)"; since the cardinality rule ("A mapping row with several targets is \"Mapped\" where the relation lets a source hold many", above) it is `mapped` / "Mapped (25)". The runner names the change; 9 checks pass.
- **The Add members dialog of a group has the dialog's margins.** Why: its content sat directly on the dialog's edges (no `dialog-body`), and the paste box had no field styling, so its text touched the border. It now uses `dialog-body` and the paste box `field-input`, like every other dialog; the security runner (`test:browser:security`) takes a screenshot of both tabs. Reported by the user during 0.13 R.
- **Known limit, not fixed (decided by the user 2026-11-10).** In a container all assistant sessions run as the one `assistant` user, so a session could read other tasks' folders and transcripts and a concurrent session's token; the engine's secrets stay out of reach. Stated in `docs/OPERATIONS.md` (`AI_AGENT_SANDBOX`); a user per session is planned later.
- **R13-F1.** `images.yml` reacted to every successful `CI` run whose branch was named `main`, and a fork's pull request from its own `main` is one: its commit was built, pushed and tagged `:main`, and the smoke step ran the fork's `compose.yml` with the registry login present. The `prepare` job now needs the run to be a push (`workflow_run.event == 'push'`) to this repository (`head_repository.full_name == github.repository`). `images-cleanup.yml` has no `workflow_run` trigger (schedule and manual only) and needed no change.
- **R13-F2.** Every third-party action in `images.yml` and `images-cleanup.yml` (`actions/*`, `docker/*`) is pinned to a full commit SHA with its tag as a trailing comment, so a moved tag cannot change what runs with the registry token.
- **R13-F3.** With a managed identity (`identityMode`), the host's `api://AzureADTokenExchange` token was posted as `client_assertion` to whatever `authorityUrl` an administrator saved. With an `identityMode` the engine now accepts only Microsoft's sign-in hosts (`login.microsoftonline.com`, `.us`, `login.partner.microsoftonline.cn`, `login.chinacloudapi.cn`): any other address is `422 REQUEST_VALIDATION_ERROR` at `authorityUrl` on save, and an address saved earlier is refused (`connection`) before anything is sent.
- **R13-F6.** An assistant task's accept loaded into the task's workspace the items of an items dry run that may have been made against another workspace, and `POST /model-drafts/{id}/dry-run` with `items` needed only Model authoring, not read access to the workspace it previewed against. A task whose check is of another workspace now fails when the proposal lands and again at the accept, loading nothing; an items dry run needs Browse in its `workspaceKey` (`403 FORBIDDEN`).
- **R13-F7.** After a first accept installed the draft's release and rebased the draft on it, words and a second accept found no model change, selected no release and made the change set on the workspace's release while the items were checked against the draft's. The accept now installs the draft's release only when the model changed, and otherwise makes the change set on the draft's own release when that is not the workspace's.
- **R13-F8.** A Stop during the accepted load raised the cancellation but left the change set and the release the accept installed, though the task's note said the change set was discarded. The accept now discards the change set and withdraws the release it installed, then ends the load as stopped.
- **R13-F11.** A new items dry run of the same draft during an accept deleted the checked items, and the batch started with none. While an accepted task of the draft is loading, a new items dry run is refused (`409 AI_TASK_STATE`); and if the stored items are gone when the load copies them, the task fails saying so, with no change set or release left.
- **R13-F9.** `ClaudeCodeProvider` passed the whole context as one command-line argument, which Linux caps at 128 KiB (`E2BIG`), so a large context failed as "the claude command could not be run". The context now goes to `claude -p` on standard input; only the fixed instructions and schema stay on the command line.
- **R13-F10.** A Claude Code reply that was an error (or a non-zero exit) carrying `usage` and `total_cost_usd` raised `ProviderError` without them, so `ai_calls` recorded no tokens or cost for a call the account was charged for; `ProviderError` now carries them and `ask` records them. The Claude Code child process also got the engine's whole environment (`DATABASE_URL`, `SECRETS_ENCRYPTION_KEY`); it now gets `PATH`, `HOME`, `LANG`, `LC_*`, `TMPDIR`, `USER`, `LOGNAME`, `SHELL` and the `ANTHROPIC_*` and `CLAUDE_*` variables only.
- **R13-F25.** The public API reference (`app.management.reference.static_site`) built the management document with job creation off and every other gated setting at its default, so it lacked model drafts, jobs, imports and assistant-task writes, model mappings, source files, inference, moves, dry run, change-set migration and all consumer-subscription operations, and the guide's links to those tags went nowhere. It now builds the application with every gated setting on (`INTEGRATION_JOBS_ENABLED`, `MODEL_ADMIN_MUTATIONS_ENABLED`, `WORKSPACE_ADMIN_MUTATIONS_ENABLED`, `CONSUMER_SUBSCRIPTIONS_ENABLED`) and job files in a scratch directory it removes; a test asserts the drafts, jobs and consumer-subscriptions paths are in the document. An instance's own `/docs/api` is unchanged on purpose: it describes what that instance has switched on.
- **R13-F26.** `guide/tools/inventory.py` imported the application with default settings, so `management-api.json` lacked the gated operations (248 operations; now 294), and `check.mjs coverage` counted every operation with a `summary` as covered although FastAPI words one for every operation. The inventory is now written with every gated setting on, and records `writtenSummary` (a summary that differs from FastAPI's generated one). An operation counts as covered when a page links its tag in the API reference (`#tag/<tag>`), names its `operationId` or its method and path, or its code carries a written summary. The count is now 18 uncovered entries (listed in `guide/_coverage/inventory/uncovered.md`), not 0.
- **R13-F27.** `npm run verify` read the committed inventory without checking it, so a settings change (`AI_AGENT_TIMEOUT_SECONDS`) never reached it, and a setting key counted as covered when a longer key containing it stood on a page (`AI_LOG_CONTENT` by `AI_LOG_CONTENT_DAYS`). Verify now runs `npm run check:inventory` (`inventory.py --check`: it needs no database, writes the inventory to a scratch directory and fails when the committed JSON differs, ignoring line numbers), and keys match as whole words, paths not running on into a longer path.
- **R13-F28.** A build for an older version (`PUBLIC_GUIDE_BASE=/docs/0.13`) kept the `/docs/...` links and `/docs/screens/*.png` images that page bodies write, so they pointed at the latest version. The build now rewrites them to the configured base (`guide/tools/rewrite-base.mjs`, an Astro integration over the built pages, so raw HTML in a page is covered too), and `check.mjs links` takes the same base from `PUBLIC_GUIDE_BASE`. Checked with a `/docs/0.13` build: its pages, screens and downloads carry `/docs/0.13/` and the link check passes.
- **R13-F29.** The plan and the guide's process text named a `status: stub | written` front matter and a build refusing stubs that never existed: a page is in `src/content/docs/` only when it is written, and briefs are outside the content collection. The plan's exit gate and its lines on the schema and checks now say so, the guide-home title item is marked closed, `AGENTS.md` names `npm run verify` as the guide step, `docs/testing/EXECUTION_GUIDE.md` says `/docs` (not `/guide`) and `verify`, and `guide/package.json` and the `check.mjs` header no longer say `/guide` or "not in verify yet".
- **R13-F30.** The troubleshooting page told operators `ENGINE_UNREACHABLE` in the browser meant DNS, TLS or proxy trouble; that code exists only in the Vite development proxy. The row now describes the production symptom: nginx's plain `502 Bad Gateway` or `504 Gateway Time-out` when the engine is down or unreachable, with what to check.
- **R13-F31.** The API reference's script policy hashed only bare `<script>` elements, so an attributed inline script in a host theme's header would have been blocked; it now hashes every inline script and not a script with a `src`. The documentation at `/docs` allowed `'unsafe-inline'` scripts; its inline scripts are a fixed set (ten, the same on every page), so each served HTML page now names its own by hash (`guide_site._page_headers`, cached by file and modification time) and `'unsafe-inline'` is gone from `script-src` (styles keep it).
- **R13-F32.** The guide's sidebar skipped a listed page that did not exist and omitted a page its section did not list, silently. `check.mjs sidebar` (part of `npm run check` and verify) now fails on a listed slug without a page and on a page not listed (only `index` and `404` are unlisted).
- **R13-F33.** The 0.13 plan, the C13-AI-REST notes and the C1 notes named the internal example model's workbook, its types and an outside product. They now say "the example model" and use neutral type names, and "a CRM".
- **R13-F34.** The guide pages for the 18 capabilities the real coverage check found uncovered.
- **R13-F35.** On a consumer API in the API reference, "Try it" failed with `401 TOKEN_INVALID` (`reason: audience`) and the person could not get a working token there. The page's sign-in configured both `engineOAuth` and `oauth2` on every source: a consumer source offered `engineOAuth` with no scopes (Authorize then issued a `management` token, which consumer data routes refuse), and the signed-in person's session token (always `management`) was prefilled into `oauth2` in place of Client ID, Client Secret and scopes. Each source now carries its own `authentication`: the Management API source `engineOAuth` (Token URL, scope `management` ticked, the session token prefilled and renewed as before), every consumer source `oauth2` only (Token URL, scope `consumer` ticked, no session token), so Authorize with a consumer client's ID and secret issues a token the contract accepts.
- **R13-F21.** A model proposal that came with both a load and moves showed no Accept at all (the header button needed no load, the bottom block no moves), and nothing carried `journey-accept`. Now the header shows "Accept the model" (with `journey-accept`) whenever the proposal has moves, and "What the load does" no longer says "Accepting loads exactly this" there: it says accepting loads none of it, because the records move by the migration you confirm first.
- **R13-F22.** The install and apply dialogs started the workspace migration without the draft's mappings when Install/Apply was pressed before `GET /model-drafts/{id}/migration` returned or after it failed, and kept the figures of the previous workspace or version when those changed. The migration read is now kept per draft, workspace and version; Install/Apply wait until it is read, and a failed read is shown ("The migration could not be read") and starts nothing.
- **R13-F23.** In the relationships grid's Change values dialog an unreadable typed value kept the "not a valid value" error, no preview and a disabled Apply after Clear was chosen, and after another attribute was chosen. The error now counts only under "Set to" and is reset when the attribute changes.
- **R13-F24.** Settings > Appearance drew four of its radio groups by hand and none linked its help text from the radio buttons. All five groups now use the one segmented choice component (`Choice`, which `ThemeChoice` also uses), each radio is described by its group's help text, with the same look as before.
- **R13-F4.** The dispatcher woke a webhook only for events stored under the API's own key, but an earlier contract version's events are stored under `<key>@v<n>`, so a subscription on a kept version was not woken by a change only that version derives (a delivery then waited for an unrelated change). `claim` now also matches the kept version's store key.
- **R13-F5.** `20261127_01`'s Microsoft 365 check compared `ms_identity_mode = 'direct'`, which is NULL, not false, for a row with a secret or a certificate, so such a row passed without its tenant and application IDs. A new migration `20261127_02` replaces the check with `IS NOT DISTINCT FROM 'direct'` (the model's constraint too); `20261126_01` and `20261127_01` now say in their docstrings that their downgrade deletes the Microsoft 365 or managed-identity mail settings.
- **R13-F12.** A type newly listed in several applications was given the alphabetically first one as `toApplicationKey` in the draft's migration, so records could move to an application that only borrows the type for a view. It now names the application where the type is own (a `table` view of it or a `tree` view including it); with none or several own ones it names none, and the preview refuses with `APPLICATION_TARGET_AMBIGUOUS`.
- **R13-F13.** Records refused `APPLICATION_TARGET_AMBIGUOUS` were kept out of the loss cascade but still deleted when the preview executed the migration; with children the parent key failed, the preview job errored and `GET /model-drafts/{id}/migration?workspaceKey=` answered 500. Such records are now never detached, emptied or deleted; the refusal is listed.
- **R13-F14.** `setKey` rewrote the current consumer API definition but not the earlier versions it keeps, so a kept version went on naming the old key and the draft became invalid. Every kept version's slots are rewritten too, and `keyChanges` names the API when only a kept version reads the old key.
- **R13-F15.** A relationship whose relation type was renamed by `relationTypeMappings` and that also had a value changed was advanced twice: the feed and history said version v+1, the row held v+2. It is advanced once.
- **R13-F16.** `GET /model-drafts/{id}/migration?workspaceKey=` needed only Model authoring at the instance but answered with record counts and example names of that workspace. With `workspaceKey` it now also needs read access to records there (`403 FORBIDDEN`, group Browse).
- **R13-F17.** A subscription filter on a `relation:<attribute>` match field checked that a value exists (`FILTER_MATCHES_NOTHING`) across every workspace's relationships. It now counts only relationships of the subscription's workspace.
- **R13-F18.** An error answered before the read began (an operation the version does not offer, a bad parameter, a bad events request) on a kept contract version lacked the `Deprecation` and `Sunset` headers every answer of it should carry. The error handler adds them.
- **R13-F19.** The record a split or list conversion creates took the first moved value as its name without a limit, so a value over 500 characters failed the migration on the name column. The name is cut at 500 characters.
- **R13-F20.** A migration advanced relation set versions only for the relationships it removed. It now advances the sets of every anchor whose relationships it creates (a split or conversion), renames (the set it leaves and the one it joins) or removes.
- **R13-F36.** The 0.13 RV change added the view `system-value-mappings` to `model/rdm-starter.json` without raising `release.version`, so an instance upgraded from 0.16.0 refused to install the starter at startup ("changed without a new release version", logged; the engine started) and the view never arrived. The starter is now `rdm-starter@0.10.1`. At startup the engine installs that release beside 0.10.0 and gives it only to workspaces that run no release yet; a workspace already on 0.10.0 stays there until a person with model management rights activates 0.10.1 there (Settings › Model, or the workspace's model activation), see Upgrades in `docs/OPERATIONS.md`. A test now holds the starter's content hash by version, so a content change without a new version fails the suite.
- **R13-F37.** Settings › Jobs, in the Grouped view, listed a job that belongs to no group without saying **Cancel requested** after a person cancelled it, so a cancelled running job showed no sign the request had been taken until it ended. The single job's row now shows it, as the flat list and a group's rows do.
- **R13-F38.** The model pane listed a type twice, under the same key, when several views of one application borrowed it ("From other applications"; React logged duplicate keys), and listed an unused type placed in a navigation group a second time under "Listed, used by no view here". The pane now shows each type once per application, as the editor change "borrowed types shown apart" says: a borrowed type stands at its first place, and a type in a group stands in its group only (with the count of the unused list following). Vitest cases hold both.
- **R13-F39.** Moving a type to another place (`setContainment`) left a relations panel on another type's page sorted by an ancestor type the related type no longer sits under (`cannot sort by 'ancestor:…'`), so the draft held an error nobody had made and the next step could be refused. The move now drops such sorts (an ancestor sort in `sortFields` or `defaultSort` of a panel that lists one related type), and its undo puts them back. A unit test in `test_layout.py` holds it.
- **R13-F40.** `setLabel` refused `reverseName` ("Unknown parameter") since the kinds declared their parameters (0.13 AQ), so a relation type's reverse name could not be edited in place in the editor. `reverseName` is a declared parameter of `setLabel` again; the generated kind tests now apply it to every relation type with a reverse name.
- **R13-F41.** "Activation needs a migration" listed the note "A step replaced the whole model" once per such step, so a draft with several of them rendered duplicate keys (a console error) and the same sentence several times. The note is now made once, and the notice keys each note by its place. A Vitest case holds it.
- **R13-F42.** A matrix cell's dialog could not be edited by keyboard: since 0.13 RV a cell's records are a table edited where it stands, and its edit pencils were out of the tab order (as a list's are, which has the row's Edit record for the keyboard), so only Open reached the record. The pencils of this table are tab stops (`EditInPlaceCell` takes `tabbable`, passed by `RelationMatrixCellTable` to the record fields and to `RelationValueCell`) and show while focused; pointer users see no change. A Vitest case holds it and `a4-relation-matrix` now reaches the pencil by Tab and opens it by Enter.
- **R13-F43.** On a phone, a change set's name in the pinned band was cut to "Co…" (the waiting pill and the Withdraw button took the row since the compact band, 0.13 FX). The name now has a row of its own on a phone and the pill and button follow it.
- **R13-F44.** On a phone, a type's page in the model editor put the tile alone on a row above the name since the facts chip read "Released: a key change needs a migration" (0.13 MG): the title block's width was its chips side by side. It now shares the row with the tile and the chips wrap inside it.
- **R13-F45.** The visual gate's `publications-view` scenarios (light and dark) did not mask the publication ID and the publish time, which differ on every run, so they sat at the 0.5% threshold and failed or passed by chance. They are masked.
- **R13-F46.** The model editor pane's "Model | Consumer APIs" tabs and its ＋ button scrolled away with the rows, and half of them were hidden when a selection was scrolled into view (seen in the re-recorded `editor-proposed-type-light`). The strip now stays at the top of the pane's scroll area with the pane's background, and rows scrolled into view stop below it (`scroll-padding-top`). On a phone, where the page scrolls, it is as before.
- **R13-F47.** A borrowed type's row in the model pane cut its kind chip and status mid-word ("Codelist matrix C…", "Master value mapp"). The name now gives way with an ellipsis (its full text is in the row's tooltip); the detail ("view · relation · from home") shrinks first, then the name, and the kind chip stays whole.
- **R13-F48.** On a phone, the change set's facts line ("Version … · Created by … · Submitted by …") wrapped so that lines started with "·". The separator now follows the fact before it, so a wrapped line ends with one and never starts with one; desktop reads as before.
- **R13-F49.** The model editor's pane lost its first row's place: the "+" that stays with the sticky tab strip (R13-F46) was lifted onto the strip with a negative margin that also pulled every row 56px up, so the strip covered the first rows and the Consumer APIs tab could not be hovered or clicked. The lift is now given back below the button, so the rows keep their place under the strip, which still stays visible when the pane scrolls. Checked by `authoring-a4a` and a screenshot of the scrolled pane.
- **R13-F50.** The build reference (0.13 BR) lived in `app/build_reference.py`, which two routers imported across the tiers (`test_tiers_hold`); it moved to `app/common/build_reference.py` (it needs only `config`), behaviour unchanged.
- **R13-F51.** A record list whose first rows asked for more width than the window had (RDM Systems › System values, with its relation columns) froze its columns wider than its container, so the last column's pencil and trash and the row menu were cut at the right edge with nothing showing the table scrolls. The table now takes the excess off its widest columns (their one-line cells end in an ellipsis; none goes below 120px) so it fits, and a table that still overflows shades the edge that has more beyond it.
- **Visual baselines retaken for 0.13 (build acceptance, R block 5).** 67 scenarios differed from baselines last recorded in 0.12 or earlier; each difference was looked at and explained by an intended change (top bar Help link and refiroo mark, the workspace actions menu, the compact change set band, model version 0.10.1, build reference on About and sign-in, Microsoft 365 on Mail, Theme on Appearance, grouped Jobs, the AI and Agent access settings pages, relationship tables, borrowed types and groups in the model editor), and the baselines were re-recorded.
- **Browser runners brought up to date.** `authoring-a4a`: a type that contains itself and a type placed in a navigation group now stand once in the pane ("Editor: borrowed types shown apart", c120ff18), so the runner asserts one row (the group's, one level under the group row), unique row keys, and the history for a drag to the top level. `a4` and `a5`: a matrix cell opens as a table with values edited where they stand, Active as the flag itself with the refusal as a notice over the cell, and unlink as a row's own button ("matrix cell dialog as a table", 67044f34); a cell shows the first of its cell fields with a value ("matrix cells show their fields", 89042b4d), so the runners read the translated name or the code. `workspace-v1`: the migration page's done notice reads "<change set> was published with the move, as Publication N." (0.13 AB, 5d97640e). `wm1` needed no runner change (R13-F41). `authoring-a4b`: the drag of a hidden panel back into main now scrolls the panel's grip into view first (the page scrolls inside the window since "Wide screens", so the grip could lie above the view); the header names it.
- **Browser runners brought up to date (Settings and assistant).** `m1-mail` looked for the Settings link "Mail" by a name that also matched "Notification email" (two different pages; the runner now asks for the exact name). `u3-settings` expected a keyboard order without the top bar's Help link and the AI and Agent access entries, and pressed Shift+Tab a fixed 17 times back to Model; it now expects them and counts back from the order it asserts. `ap1-ai` expected the values send level to read "up to 20 per column"; 0.13 CP made it "with no limit per column". `ap12-change-model` (and `helpers/reshape-stand-in.py`): the engine offers no change that loses what the person did not ask to remove (2026-11-09), so the stand-in's part-of-a-type proposal now lists the split type as a removal with the person's words and `movedTo`; the runner also waits for the first step's button before counting it. `u4-integration` follows the F37 fix; `ao1-impact-summary` passed on three runs without a change (the axe failure seen in the release run did not recur).

### Added (list browsing: Find a list, a table's inactive records and a matrix's empty columns, 0.13 LB)

- **The sidebar's Collections have a Find a list box once an application has more than ten entries.** Why: with many lists the way to one was scrolling. Typing narrows the collections and placed matrices across every group and those in no group to the names that contain the words (case-insensitive, the match in bold, "N of M" announced politely); a group with a match opens with only its matches, a group without is hidden; Enter opens the first match, Escape clears. The reader's own folds are never written while a search stands, so clearing returns them. `features/objects/Explorer.tsx`, `model/collections.ts` (`narrowNavigation`).
- **A table view may declare `availabilityField`, a yes/no attribute of its type (schema 0.10, optional).** Why: a list keeps retired entries, and a reader needs them out of the way without losing them. A record whose value is false keeps its row, its name in the secondary ink with a neutral **Inactive** pill ("Not <attribute>" when the attribute is not called Active), and the toolbar gains **Hide inactive (N)**, which applies the ordinary filter `<field> ne false` (not false, so a record with no value stays and is not marked; the pill reads "Active: not No") as a pill in the address; N is one count read through the list's own count of the records whose value is false, exactly those the switch hides. The list query gained `ne` for yes/no attributes (`filter.<field>.ne=false`; `docs/API.md`). A field that is no boolean attribute of the type is refused at `…/config/availabilityField`; a renamed attribute is followed and a removed one takes the setting away, as a tree's. A model that does not use it keeps its content hash. The model editor's table settings offer **Inactive records…**. `models/schema.py`, `validation/application_rules.py`, `engine/reads/object_query.py`, `engine/model/candidates.py` (`filter_operators(listing=True)`), `authoring/references.py`, `ui/ObjectTable.tsx`, `features/objects/ObjectToolbar.tsx`, `features/model-editor/layout.ts`; OpenAPI lock re-baselined (additive); journey J33.10, `ExplorerFind.test`, `CollectionView.test`, runner `e2e/lb-list-browsing.mjs`.

- **A relation matrix can hide its empty columns (0.13 LB-D8).** Why: a matrix over many languages or systems shows mostly empty columns. A toggle **Hide empty columns** beside Filter (off by default, kept per view in this browser with the column widths, `useTableDisplay`) leaves out the columns with no related record in any row the search and parent scope leave, and the line "N empty columns hidden · Show all" says how many; columns chosen in Filter win and the toggle then says it has no effect. The engine decides it for every matching row in one statement and skips the columns in the column pages themselves (`hideEmptyColumns`, `RelationMatrixPage.emptyColumnsHidden`), so column paging stays exact; a change set and a publication read their own values. `management/projections/relation_matrix.py`, `features/objects/RelationMatrixView.tsx`, `ui/TableDisplay.tsx`; OpenAPI lock re-baselined (additive); `test_relation_matrix`, `RelationMatrixView.test`, `e2e/lb-list-browsing.mjs`.

### Fixed (mapping grids and relation matrices on the shared table, 0.13 FX)

- **A mapping grid's record names open the records, its columns resize and a cut-off value shows whole.** The "Map to …" views and the matrices ("… by system") were drawn with tables of their own, so the source record's name was not a link, the columns could not be sized and a value cut off at the column's edge could not be read. Both are now drawn with the table every record list uses (`ui/DataTable`, extended with row-header cells, per-cell attributes, a header of its own and a grid's role and keyboard handler, which a matrix needs): columns resize and keep their widths per view, and a cut-off value shows whole when pointed at or focused. In a mapping grid the source's name and each target chip open the record; a click elsewhere on the row and **Map**/**Change** still open Change mapping. The matrix keeps its cell dialog, its grid keyboard navigation and the pencil's tab stop. Each column's resize handle is a tab stop before the grid, as in every table (a page of 20 matrix columns adds 21); the a5 runner's tab budget to reach the grid went from 20 to 40.
- **A mapping grid's columns of a row may name the type above the row.** `sourceColumns` accepts `ancestor:<type>`, as a matrix's `rowColumns` already do (the coverage read already returned it as the ancestor's name; the model check, shared with the matrix, already accepted it), and the model editor's mapping-grid **Columns of a row** offers those types under "From the parents". A system value's mapping grid can show its system. Search does not look at them.

### Changed (model editor: borrowed types and drag-to-reorder)

- **The model pane and a type's page tell a type an application holds from one it only borrows.** Why: an application lists a type either because it keeps the type's records or because one of its relation views (a relation matrix, mapping grid or relationships table) needs it, and the editor showed both alike, and a grouped type twice. The outline (`GET /model-drafts/{id}/outline`, additive) now says, per application, `ownTypes` and `ownTree` (a `table` view of the type, or a `tree` that includes it), `borrowed` (`[{objectType, home, uses}]`, with `borrowedTree`) and `unused`; a use is `{view, viewName, viewType, role, relationType, relationName}` with role rows, columns, cells, from, to, or link (a type on the containment path between a matrix's column and cell types). A type's `home` is the first application, in model order, that holds it; the type entry has `home`, `ownIn` and `borrowedIn`. The pane shows each type once per application: a type placed in a navigation group stands only in its group (a held type as a plain row with the types it contains beneath it, a borrowed type with a dashed icon, a kind chip and "view · relation · from home"; a group row says "group · N" for its entries), the other held types in their containment tree, the borrowed types in no group under "From other applications", and the types no view uses under "Listed, used by no view here" (with "can be unlisted" where the existing unlist rule allows it). A borrowed type opens on its home application, so its Preview and layout editor show where its records are edited. The type page says "Maintained in <home>" and adds an "Also in <application>" line per borrowing view.
- **Navigation groups and group entries are dragged into order, and Starts folded is a one-click cell.** `EditorTable` takes an optional `reorder` (rows show the grip and a drop line; a drop sends the position the Move up and Move down items send); it is on for an application's navigation groups and a group's entries. Move up and Move down stay in the menus. An application page splits its types as the pane does: "Object types" lists the types it holds, "From other applications" the borrowed ones (From, Used by, Relation, Group), and "Listed, used by no view here" the unused ones; a borrowed row opens on its home. A borrowed row in the pane has the full text as its tooltip. A group page's entries table says each entry's Kind (List, Borrowed list or Relation matrix) and what it opens on as "view kind · view name". The Starts column became Starts folded, the one-click yes/no cell (`ui/FlagCell`, the box alone under its header) that saves in one step.

### Changed (the Claude Code proposal provider is built in, `AI_PROVIDER=claude-code`)

- **`AI_PROVIDER=claude-code` is a provider of the engine, in the image.** Why: a deployed image set `AI_PROVIDER=devtools.claude_code_provider:provider` and refused to start (`No module named 'devtools'`), because `backend/devtools/` is not in the image (only the guide's reference instance mounted it). The provider moved to `engine/proposals/claude_code.py` and behaves as before: one headless `claude -p` call per request, no tools, MCP servers, project settings or saved session, in an empty temporary directory, `AI_MODEL` as `--model`, `AI_TIMEOUT_SECONDS` as the limit. It needs no `AI_API_KEY`; it signs in as Claude Code does (`CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` in the environment, or the host's sign-in). The `usage.jsonl` file is gone: `ProviderAnswer` has an optional `cost_usd` (the CLI's `total_cost_usd`), and `calls.ask` writes it to `ai_calls.cost_usd`, so the cost of a provider call shows in Calls; the other providers leave it empty. `backend/devtools/` and the reference instance's mount are removed; the reference `.env` and README use `claude-code`. Production normally keeps `claude` with `AI_API_KEY`. Docs: `.env.example`, `docs/OPERATIONS.md`, the guide's Set up AI, Developer instance and AI pages.

### Fixed (mail through Microsoft 365 arrived empty, 0.13 MS)

- **A message sent through Microsoft 365 arrives with its text and HTML.** Cause: the MIME handed to Graph's `sendMail` had bare LF line ends (the message's own policy); Exchange then finds no parts and delivers an empty message, while SMTP was unaffected because `smtplib` converts the line ends. `engine/mail/graph.py` now serialises with CRLF; J46.11 checks the MIME Graph receives. Seen on the first live Microsoft 365 setup (managed identity, 10 Nov 2026).

### Added (build reference on About and sign-in, 0.13 BR)

- **About and the sign-in screen show which commit and tag the engine was built from.** Why: nobody could tell which build an instance ran, only its version. `GET /api/v1/system` has `engine.build: {commit, tag}` (the first eight characters of the commit, and the release tag on it; each null when unknown), and the public `GET /oauth/sign-in/options` answers `build: {version, commit, tag}`, nothing more. An image gets them from build arguments (`REFIROO_BUILD_COMMIT`, `REFIROO_BUILD_TAG`, passed by `.github/workflows/images.yml`; the image has no `.git`); a checkout reads them once through `git` (`app/common/build_reference.py`). Settings › About, Engine has a **Build** row with the tag and commit linked to the repository (the source address with `/tree/...` removed). The sign-in screen (and the reset pages that share its frame) show one very small muted line under the card, "refiroo 0.16.0 · build v0.16.1-alpha.1 (baf823b6)", the tag and commit in the link colour, no links; hidden parts are left out when unknown. The OpenAPI baseline is re-baselined for `EngineInfo.build` and `BuildInfo`. Guide: `run/licence-and-source` describes the Build row and the sign-in line.

### Added (mail through Microsoft 365, 0.13 MS)

- **Mail can be sent through Microsoft 365 (Microsoft Graph) beside SMTP.** Why: Microsoft is retiring basic authentication for SMTP AUTH in Exchange Online, and an organisation on Microsoft 365 often cannot give refiroo a user name and password for it. Settings › Mail has a method choice at the top of the form: SMTP server (as before) or Microsoft 365, which has one **Sign in with** menu of four entries (client secret, certificate, managed identity in this tenant, managed identity hosted in another tenant) and takes the tenant ID, the application (client) ID, a client secret or a certificate (PEM key and certificate; sealed with `SECRETS_ENCRYPTION_KEY`, never answered; the page and `GET /mail-settings` show the certificate's thumbprint and expiry, `clientSecretSet`), the sending mailbox (`fromAddress`) and, for a national cloud, the token and Graph addresses (defaults `https://login.microsoftonline.com` and `https://graph.microsoft.com`). One method is active: saving one clears the other's saved fields, and a saved credential is kept only for the same tenant, application and token address (`422 MAIL_CREDENTIAL_REQUIRED`); a certificate that cannot be used is `422 MAIL_CERTIFICATE_INVALID`. The engine takes a token with the client-credentials grant (plain `httpx`, a signed RS256 assertion for a certificate, a cached token), sends the same MIME message as SMTP with `POST /users/<mailbox>/sendMail`, and maps failures to the kinds it knows: a refused token, missing `Mail.Send` consent or a mailbox the application may not use is `login` (shared by every waiting message, with a sentence that says what to change in Entra), Microsoft out of reach, throttled or failing is `connection` and waits at least `Retry-After`, a mailbox that does not exist is `sender` and waits to be tried again, as with SMTP. Bounces are not read: a message Graph accepted shows as sent and a bad address comes back to the sending mailbox. The MIME route of `sendMail` has no `saveToSentItems`, so system mail lands in that mailbox's Sent Items. **A managed identity is a third credential (MS-D5), where refiroo runs on Azure and no secret is stored:** `direct` (the host's own identity in the organisation's tenant: the engine takes a Graph token from the Azure host's token endpoint, `IDENTITY_ENDPOINT` with `IDENTITY_HEADER` or the VM metadata service, with no tenant token request; an optional user-assigned identity client ID; no tenant or application ID) or `federated` (refiroo hosted in another tenant: a user-assigned identity's token for `api://AzureADTokenExchange`, or its `USGov`/`China` form by the token address, is the `client_assertion` of the client-credentials grant at the customer's tenant). `PUT /mail-settings` takes `identityMode` and `identityClientId`; the response has `credential`, `identityMode` and `identityClientId`; saving a managed identity clears a saved secret or certificate. Where no Azure host answers, the test and queued mail fail as a shared `login` failure saying refiroo is not running with a managed identity. Migration `20261127_01`. Migration `20261126_01` (an existing row becomes `smtp`); `reseal_secrets` covers the new secrets. Docs: `docs/API.md`, `docs/OPERATIONS.md` (Entra setup), J46.11 in the journey catalogue, the guide's mail pages. Journey: `test_j46_mail_microsoft365` against a local stand-in for the token endpoint and Graph (`tests/graph_server.py`).

### Documentation (pictures of the Microsoft 365 form, 0.13 MS)

- **The mail pages show the form.** Three pictures from the reference instance (`admin-mail-microsoft365-menu`, `-secret`, `-entra`; recipe `guide/_waves/MS.screens.json`): the Sign in with menu with its four entries, the client secret entry filled with example values, and the managed identity entry with the Entra steps opened. Nothing was saved or sent. `docs/API.md` no longer says that a mailbox Microsoft 365 does not know fails at once; it waits and is tried again, as the code, `docs/OPERATIONS.md` and the journeys say. `m1-mail.mjs` section 7b runs a saved Microsoft 365 configuration (secret, certificate) in the browser on both models.

### Changed (an AI task is named by what it asks, 0.13 TN)

- **A task given in words is titled by a short title its own session writes, not by its request cut off.** Cause: the task page and the Jobs page named it by its words cut at 80 characters (mid-word, typos included), and the draft was named the same way. Now the session's `proposal.json` carries an optional `title` (a few words, for example "Move types under the person group"; prompt `agent/20`, no second model call), the engine stores it on the task (`ai_tasks.title`, migration `20261125_01`) and the API returns it as `title` (null until written). The task page heading, the Jobs page group name and the confirm bar use it; the full request stays shown uncut ("You said: …"). The assistant's draft is named `Assistant: <title>`, once. Until a title arrives, and for a task that ends before its first answer, the words are cut at a word boundary, never mid-word (`cutAtWord` in `aiTaskText.ts`, `cut_at_word` in `engine/tasks/store.py`, and the same cut in the Jobs page origin name). J50.72.

### Documentation (six assistant pictures retaken, 0.13 DOC10)

- **The six pictures of the assistant journeys show the current pages.** `use-assistant-proposal`, `model-assistant-workbook-proposal`, `use-assistant-loaded`, `model-assistant-workbook-loaded`, `use-assistant-reload` and `use-assistant-words` were taken before the checked-items load and showed the saved-profile load, "Accept the model" and proposal-file wording. They are retaken from one workbook task (checked, then accepted with **Accept and load to change set**, "What the load does", 172 records new, 322 relationships new) and one words-only task ("No change to the model", **Accept**), with their recipes in `guide/_waves/C10.screens.json`.

### Documentation (the relationships table, grid and cell dialog looked at on a phone, 0.13 RV)

- **Inspected once at 390 x 844 (touch) and 1280 px, light and dark; nothing needed changing.** The page does not scroll sideways at either width, the grid and the matrix cell dialog's table scroll inside their own scrollers, and the filters, Display, the selection bar, the bulk change dialog, the `+ Link` cells and the group headings work. The result is recorded under RV in the 0.13 plan.
- **`test:browser:rv`**, a browser acceptance runner for the relationships panel, the relationships table, the grid and the matrix cell dialog: values edited and bulk changed with each write read back through the API, live and in a change set, a refused batch naming the failing item, Layout… in the model editor, keyboard, 390 x 844 touch and a dark pass, with axe.

### Fixed (the guide home's tab title, the AI task fixture's keys, 0.13 FX)

- **The guide home's browser tab reads "refiroo documentation" once, not "refiroo documentation | refiroo documentation".** Cause: Starlight joins the page title and the site title, and the home page's `title` equals the site's. Now the home page's front matter sets its `<title>` tag itself (`head` in `guide/src/content/docs/index.md`); its visible heading is unchanged.
- **`test_model_independence` passes again.** Cause: `frontend/src/features/ai-tasks/designFixture.ts`, a fixture outside the test's reach by name, held the starter model's keys `domain` and `codelist` as literals. The fixture now uses neutral keys (`topic`, `category`), and the tests that assert them follow (`DesignView.test.tsx`, `DesignCheckView.test.tsx`).

### Fixed (the assistant's note shows a table as a table, 0.13 FX)

- **A markdown table in the assistant's note ("| Result | Count |", "|---|---|") is a table, not plain text.** Cause: `AssistantText` (`frontend/src/ui/AssistantText.tsx`), the one component that shows the assistant's words in the task notes, the proposal and the design view, read paragraphs, lists, bold and code only, so a table's lines ran together as text. It now reads a table (header line, rule line, rows) and shows it with the app's ruled table (`SettingsTable`; at phone width each row stacks, so the page does not scroll sideways). Cells are text, never HTML.
- **On a phone, the assistant's task page no longer runs its text and cards past the right edge.** Cause: `.task-check` (`frontend/src/styles/settings.css`) is a grid whose one column took its widest child's width, so the notes, sections and cards were wider than the window and clipped. The column is now `minmax(0, 1fr)`, so each child fits and its own table scrolls inside it. Seen with the note of the task whose table was fixed above, at 390 px.
- **The two proposal pictures of the assistant journeys are retaken from a new checked task** (`use-assistant-proposal`, `model-assistant-workbook-proposal`; the first task was already accepted), and the alt text and captions of `use-assistant-proposal` on `use/loading-with-the-assistant` and `journeys/work-with-an-assistant` describe what it shows now (0.13 DOC10).

### Fixed (a taken release version has a way forward, 0.13 FX)

- **Apply, Install and Load no longer end in "already installed with different content" with nothing to do.** Cause: the editor proposed the base release's next version without knowing which versions were installed (the assistant's drafts take them), and after the failed try the draft kept the taken version, so every retry hit the same `RELEASE_IDENTITY_CONFLICT`. Now the draft outline carries `suggestedReleaseVersion` (a free version, or the draft's own when free), the 409 carries `details.releaseKey`, `releaseVersion` and `freeVersion`, and each dialog (and the model workbench) offers **Use <version>**, which sets the release and goes on. `next_free_version` in `engine/model/releases.py` is the one rule, shared with the assistant's install.

### Fixed (a file already in the workspace is a checked load, 0.13 AB)

- **A workbook whose every record is stored already ends `checked`, and accepting it ends `loaded` with nothing new.** Cause: the assistant's prompt (`agent/18`) let the session decide "already there", send no items dry run and write no proposal, so the task failed, and an accepted items load whose change set held nothing failed with "nothing to load". `agent/19` says the items dry run and the proposal are always sent (the draft is the current model, each item names an existing record by ID); the accept ends `loaded` with zero counts and the matched records as `unchanged`, no release when the model does not change, and the empty change set stays on the task to discard. A session that ends with no proposal still fails.

### Fixed (the change set band stays compact, 0.13 FX)

- **On a change set page the pinned band holds one compact strip, and the rest scrolls with the page.** Cause: the change set bar in the band (`contextActions`) reached `BelowContextBand` outside `ContextBandSlotContext`, whose provider wrapped only the page content, so its notices (model mismatch, sent back, warning) rendered in place inside the sticky band instead of in the slot below it; with a long submit comment the band covered about half the window. `AppShell` now provides the slot to the band as well. The band keeps the name (one line, ellipsis, full name in its title), the "Waiting for approval" pill and the buttons; the version, source, model and creator line, "Submitted by", the comment (two lines with Show more / Show less where it is longer) and "Withdraw the request to edit it." sit below it with the notices. Frontend only.

### Fixed (a moved collection opens in its new application, 0.13 MG)

- **An old address of a collection a model migration moved to another application opens it there, instead of the "not in this workspace's model" page.** Cause: `missingElement` looked only at the application named in the path, so a view, kind of record or navigation group that now lives in another application of the same model was reported as missing. `relocatedPath` (`routing/routes.ts`) now finds the one other application that holds the key and rewrites only the `/apps/<key>` segment, keeping the rest of the path and the whole query; the router replaces the history entry (Back does not loop), and Home's remembered "continue where you left off" address is moved the same way. A key held by none or by several applications still shows the page as before. Frontend only.

### Fixed (a type's preview follows its application, 0.13 DF5)

- **A type listed in several applications opens its preview, record page and table views in the application whose row was selected.** Cause: the editor's selection kept only the type, so the preview took the first application that listed it (a country listed in System codes, Reference lists and Translations always showed System codes and "The draft declares no table view for Countries"). The type selection and the editor address now carry `application`; tree rows and collection rows pass their own, and only the selected row is highlighted. A link naming no application, or one that does not hold the type, falls back to the first application with a detail page or table view for the type, else the first that lists it. Frontend only.
- **A selection that names no application opens the one that holds the workspace's records of the type, and the preview reads records for that application only.** Cause of the follow-up report: a country's records all belong to Reference lists, but the preview took System codes (the first with a detail page), tried to show a Reference lists record in its page ("This object belongs to another application") and a layout edit went to a page no record uses. Resolution order: the application named, else the one that owns the workspace's records, else the first with a table view or detail page, else the first that lists the type (`applicationForType`). The records query carries `applicationKey`; when the application chosen has none in the workspace, the empty record is shown with a line naming the application that holds them and a link to switch. A type listed in several applications shows the application in the band, as a choice among them.

### Added (attributes of the relationship in views, 0.13 RV)

- **A matrix cell shows and changes the relationship's own values.** Each cell record carries `relationAttributes`; the cell dialog shows them under "Attributes of the relationship", a link or a create-in-cell sends the values entered, and an edit claims the relationship's version, with the conflict notice of the Edit values dialog. One shared `RelationAttributes` serves all three.
- **A matrix cell's relationship values are edited in place**, as a record's fields are: each value shows with the Edit pencil, opens a small form with Cancel and Save, and saves against the relationship's version; there is no separate "Edit relationship values" step. The relationships table's cells save through the same code.
- **A matrix cell opens as a table.** A row per record: its name and the view's cell fields, then the relationship's values under "Attributes of the relationship", then Open and Unlink (asked in the row); every value edits where it stands with the cells of the other tables (`RelationValueCell`, `EditableField`), a save re-reads the cell and keeps the dialog open, and a filter box narrows the records. The separate Edit step is gone; Create and Link are as before. The dialog widens with the columns (`Modal` `width`) and the table scrolls inside it, name and actions fixed.
- **The Relationships panel shows them as columns** after the related record's, listed in Display under the same heading; no sorting by them.
- **A new view type `relationTable`** (schema 0.10, "Relationships table"): one binding's relationships as rows with both records' columns and the attributes as columns; filters, sorting, group headings with counts and cursor paging, live, in a change set and in a publication; cells edit where they stand, ticked rows are set in one request. `GET /workspaces/{key}/relations` takes `fromObjectId`, `toObjectId`, `sort`, `filter.<ref>.eq` and `seek`, its rows carry `relationVersion` and its page `groupCounts`. The editor's **Add a view…** offers it as a kind; the example model has one over the system value mappings.
- **`POST /relations/batch`** sets attribute values on many relationships as one write, all or none, refusing with `RELATION_BATCH_REFUSED` and each failing item named.
- **A relationships grid (0.13 RG):** a relationships table with `layout: "grid"` shows each record once with a column group per related record and the relationship's values under it; the viewer picks the related records and the values shown (in the address), filters, links a pair with one click and sets one value on ticked rows or every matching row, counted first (`GET /workspaces/{key}/relation-grid`, `POST /relations/grid-change`).
- **A relationships grid filters with the collection's own filter bar** over the filter fields of its end types' main views (every operator, search, related filters) and the relationship's values, for the rows and for the column records, shown as columns or not; rows are selected and changed as a collection's are, and a saved cell reads only its own row again.

- **The guide's reference model carries relationship values** (release 1.8.1): stop to operator holds Local name, Primary contact and Inspected on, system code to municipality holds Confirmed and Note; two relationships tables over the first (rows, grid), a related-block field per value in the Stops API, and `samples/data/reference/relation-values.json`. `load.py` moves an existing workspace to the release.

### Fixed (a refused grid change names its relationships, 0.13 FX)

- **The relationships grid's Change relationship values dialog says which relationship each refusal belongs to.** Found by `test:browser:rv`: a value below an attribute's minimum on two pairs listed the engine's message twice with nothing to tell the pairs apart. Cause: the dialog listed `refused[].message` only, and the engine's refused items for an existing relationship carried its ID but not its ends. The engine now adds `fromObjectId` and `toObjectId` to such items (`decide_relation_values`, so `POST /relations/batch` and `POST /relations/grid-change` both), and the dialog writes each refusal, in the preview and after a refused Apply, as "Stop A → Operator B: message" with the names the grid shows, once per relationship and reason; the title counts those lines.

### Fixed (Layout… of a relationships table, 0.13 RV)

- **"Layout…" opens on the view's current layout.** Cause: the draft outline (`GET /model-drafts/{id}/outline`) carried a view's `config` only for tree and mapping-grid views; it now carries a relationships table's too, so a grid view opens on "Grid".
- **A relationship attribute holding JSON can be a column of a new relationships table.** Cause: the Add a view dialog put every selected attribute into `sortFields` (and a filterable one into `filterFields`), and the model refuses a JSON field as either, so the draft became invalid. A JSON attribute is now left out of both.
- **A relationships grid can filter by a Yes or no relationship value.** Cause: the filter built every comparison (`<`, `<=`, `>`, `>=`) before choosing one, and SQLAlchemy refuses those on a Yes or no value, so the read answered 500; only the asked comparison is built now (`reads/relation_grid.py`).

### Fixed (AI task progress line, 0.13 AW)

- **An AI task's "Working on it" line no longer shows the session's shell command.** Cause: `tasks/agent.py` defined `_plain` twice, and the later one (quote comparison, which only lowercases and strips punctuation) replaced the one that puts a call in words, so the raw command reached the page. The progress helper is now `_call_in_words`; the line reads "Reading stored … records", "Writing …" or "Working".

### Fixed (a tall Display popover looks cut off, 0.13 FX)

- **The Display popover of a relationship or collection panel on a record page no longer looks cut off, and no popover opens with no height on a scrolled page.** Cause: the application frame was a positioned, page-sized box that scrolls with the window, and React Aria measured a popover's room from it, so a popover placed below its button on a scrolled page got a height of zero (the Display popover then flipped above with only the room there, under a scrollbar macOS hides). The frame is no longer positioned (`.app-shell`), so room is measured from the window; this covers `ControlPopover` and `InfoHint`. A popover now stays below the sticky top bar and data band (its placement boundary starts under them, and follows the window while it is open). When it cannot show all its content it scrolls the page, if that can give it the whole room below its button, else the whole room above it under the band, and places it again; only in a window too short for either does it scroll inside, with an always-visible scrollbar.

### Fixed (the assistant re-checked an outdated copy of its draft, 0.13 FX)

- **An AI task no longer fails over a draft its session has already corrected.** Cause: database sessions keep loaded rows after a commit (`expire_on_commit=False`), so on every landing round `_proposal_landed` read the draft the first round had loaded, not the one the session had corrected through the API since, and the compatibility check refused the same thing again until the rounds ran out. A task that proposed `rootCreatable: false` on 25 list types and then set it back failed with the first round's `PARENT_REQUIRED`. The draft is now read from the database on each round (`populate_existing`), as is the draft version a turn starts from, and a locked read of a task (`load_task(..., for_update=True)`) sees the committed row.

### Added (attributes of the relationship in consumer API related fields, 0.13 RA)

- **A related block can publish a value stored on the relationship itself.** In `object.related.<name>.fields`, the source `relation:<attribute-type-key>` reads that attribute's value on the relationship each item was reached through (`null` when it has none), in objects, lists, XREF and resolve answers and in publication and `asOf` reads. The attribute must be in `attributeTypeKeys` of a binding of the block's relation, in its direction, from an exposed type; otherwise the draft compile, install and validation refuse it at the field (`INVALID_REFERENCE`), as they refuse the source anywhere but a related block's fields and the `matchOn` that read them. The field has the attribute's value type in the schema and the OpenAPI document; the values are read in the related items' statement, not per item. An event watching the block reports an update of the relationship's values.
- **They match too.** An `onRelated` filter's `matchOn` (with `keepOnlyMatching`, `scoreOnlyMatching`, `crosswalk`) and an XREF `alsoMatchThrough` rule's `firstOf` may name `relation:<attribute>`: the value is compared with the relationship's attribute, so an item matches through that relationship only. An XREF rule reads a text attribute.
- **The editor offers them.** The field picker of a related block, and its `matchOn` pickers, have a group **Attributes of the relationship**, listing the attributes of the relation's bindings; `GET /model-drafts/{id}/outline` lists `attributeTypeKeys` on each relation.

### Changed (changes that need a migration are made in the editor, 0.13 MG)

- **The editor applies a change to a released element that stored data holds**, where it refused it. A type moved to another application or under another parent, a split, a merge, a conversion to a list type, a tighter rule, a removal and a key change are applied like any other step (undo, redo and the dry run behave as usual) and marked **Needs a migration** in the history, with the records, values and relationships that hold the element (`migration` on the history entries of `GET /model-drafts/{id}/operations`). The menu reads "Needs a migration when installed" and Move to… says what becomes of the records. **`OPERATION_REQUIRES_MIGRATION` is no longer raised.** A released key can change; the install dialog says that integrations naming it must change, and names the consumer APIs of the base release that name the old key.
- **The draft states its migration**: `GET /model-drafts/{id}/migration` (`workspaceKey`, `againstReleaseId`, `toReleaseId`) derives, each time and from the steps that stand now, which type, attribute and relation type becomes which, which application a moved type goes to, whether its records leave their parents, the split's and the conversion's new records, each key change with the consumer APIs naming the old key, and with a workspace the preview's own landing check. The install and apply dialogs state it and start the preview with its mappings (**Install … and preview the migration…**); the migration page opens filled in (**What the draft proposes**), each row marked Proposed and changeable in place.
- **The workspace migration carries more**: `toApplicationKey` on a type mapping (a type listed in several applications moves too), `relationTypeMappings`, `splits` and `listConversions`, and `draftId`. A record whose type stands at the top after a move becomes a top-level record (its parent and the containment relationship go); a split and a list conversion create records, values and relationships, shown as the new **Created** outcome (`counts.created`, `?status=created`); all as set statements in PostgreSQL. A tighter rule still lists the records that break it as refused, and a removal is still a loss to accept. Activation still refuses a release whose migration has not run.
- **A migration never loses records of a type the target still has, and the assistant offers none that loses data (user's product rule, 2026-11-09).** Records of a type the target lists go to their own application, the mapping's `toApplicationKey`, the one application that lists the type or the one that lists it newly; when that is not unique they are refused (`APPLICATION_TARGET_AMBIGUOUS`, naming the candidates) instead of lost. A workspace migration of 20 types moved between applications while a third application listed every type previewed 459 losses with no mapping; it now moves 179 records and loses none. `GET /model-drafts/{id}/migration` with a `workspaceKey` starts from the release that workspace runs, so after an install the Apply and Install dialogs still state the move. The assistant task runs the landing check on exactly the migration it would hand over, whatever kind of change caused a loss: a loss of a record, value or relationship goes back to the session as a finding, and at the handover no migration is returned and the task says per type what would be lost and that no data was changed. The one exception is what the person's words explicitly ask to remove: the session lists it in the proposal's `removals` (kind, key, the quoted words), the guard allows a loss only when it falls within those removals (records of a removed type or application, values of a removed field, relationships of a removed relation type or of removed records), and the task page and notes state the deletion in plain words with the engine's counts before the person accepts ("As you asked, the Drug list is deleted, deleting 16 records."). Agent prompt `agent/16`. The migration page words `APPLICATION_TARGET_AMBIGUOUS`.
- **Found by the before-and-after on a real model:** a type listed in several applications that was moved out of one would have lost its records; the draft's migration now names the application it gained.
- **A task that moves types to another application hands the migration the move.** The task's migration was built from the assistant's `moves` alone, so types that keep their key and change application were handed over with no mapping and the preview listed every record and relationship of them as lost. It now starts from the engine's own migration of the draft against the workspace's release (application moves with `toApplicationKey`, relation type mappings, splits and list conversions) joined with the assistant's moves, one mapping per type. The landing check, the proposal's "What happens to the records" ("20 types move to Reference lists, 179 records") and the task's `result.migration` (now with `relationTypeMappings`, `splits` and `listConversions`) use that set; the engine's note that a step replaced the whole model is shown as a task note.
- **The assistant's counts say what they count.** A summary counts the records of the types or lists the change touches, named, and states the rest of the workspace apart; it no longer gives the workspace's total as if every record were part of the change (a move of 179 records read as "all 4657 records keep their IDs").

### Added (relation matrices in navigation groups, a collection's opening view, a group panel in the editor, 0.13 NG)

- **A relation matrix can stand in a navigation group as an entry of its own.** A group's `collections` may hold `{ "view": "<relation matrix view key>" }` beside collection keys, in one shared order; the sidebar and the group page show the matrix named after its view, with a matrix glyph in its row type's hue, opening the matrix directly. The row type's entry stays and its view switch is unchanged; a matrix in no group stays inside its row type's entry. `navigation.opens` maps a collection to the view its entry opens on, in place of the application's `defaultView` for that collection. Schema 0.10, optional: a model without either keeps its content hash. Validation refuses a view entry that is no relation matrix of the application, a matrix in two groups, and an `opens` key or view that is no collection or view of it, each at its pointer. Presentation only: the change is compatible.
- **Operations.** `placeCollection` takes `view` in place of `collection` to place, move (at a `position` of the group's one order) or take out a matrix; the new `setCollectionOpening` sets or clears a collection's opening view. Several entries added to a group in one request are one step and one undo. Removing a matrix view takes its entry and its opening with it, and a view given a new key keeps both; `GET …/outline` lists each group's `entries`, `navigation.opens` and each view's `collection`.
- **The editor opens a group.** Choosing a group in the model tree shows its panel: its entries with their kind, what each collection opens on (changed in place) and state, a menu to move an entry up or down, to another group or out of its group, and **Add to group…**, a dialog with a search that adds several collections and matrices at once and says where each stands now. The application panel's group table lists matrices among a group's entries and links the group's name to its panel; "In no group" offers **Add to a group…** with those collections chosen; a relation matrix's menu in the Views table gains **Move to group…**. The group page's search messages say "collection or relation matrix", and **Remove group** says that a group's relation matrices go back inside their row type's entry.

### Changed (the assistant loads a file as one checked batch, 0.13 AB)

- **A draft's dry run takes items.** `POST /model-drafts/{id}/dry-run` accepts `workspaceKey` and `items` (the batch items, each with an optional `ref` naming its cells, such as `Person!Q31:S31`) in place of `sourceFileId`; exactly one of the two. The worker previews every item against the draft's model in a rolled-back transaction and stores the items with the completed job. `GET …/dry-run` answers `items`: per type the records new, matched, changed and refused, the relationships, up to three examples with their refs, the rows read, the parts of the file by sheet and columns, the refused items with their refs, and the finding, read before the rollback, of a name that appears more than once in one type among the records the load touches, with the parents. Held to the background limits and to `ATOMIC_JOB_MAX_ITEMS` (`413 BATCH_TOO_LARGE`).
- **Accepting runs the previewed items, with no assistant turn.** The engine installs the draft as one release (the install of `POST …/installation`, now one function), makes the change set on it (on the current release when the model does not change) and runs the stored items as one atomic batch; the task ends `loaded` with the batch's counts, or `failed` naming the refused records and their cells with nothing written, the change set discarded and the release it installed deleted again (kept, with a note, when the engine refuses to delete it). A draft edited after the check has every item checked again first. Model-only tasks and moves end as before.
- **The assistant works as in an ordinary session** (`agent/15`): it reads the workbook and the workspace's records itself, changes the draft, writes a script that turns the file into items (new records with IDs it generates, existing ones named by ID), sends one items dry run and fixes its items until nothing is refused and the findings are explained. It writes no load profile and asks only what the file and the words leave open, in the person's terms.
- **The task page shows What the load does** in place of "Where each sheet goes" for these tasks: the figures, a table per type whose rows open to example records, the engine's findings and a folded "Where each part of the file goes"; **Accept and load to change set** says the engine loads exactly those records, the task bar says the same, and the loaded page says an items load only installed its release (publishing moves the workspace) and that new words are a correction checked and accepted again. Tasks recorded with a profile keep "Where each sheet goes". A load made from items saves no import profile; saved layouts load as before.

### Added (related jobs grouped on the Jobs page, 0.13 JG)

- **A job says where it comes from.** `origin` on every job: the assistant task it belongs to (its own job and every job its session queued) or else the model draft it works on, with the name the task's or draft's page shows; `null` for neither. `GET /jobs?grouped=true` answers one row per origin and one per job without one, newest activity first, with job counts per state; `GET /jobs?origin=aiTask:{id}` (or `modelDraft:{id}`) lists one group's jobs. Without them `GET /jobs` is as before. The OpenAPI lock is re-baselined.
- **Settings › Jobs groups related jobs.** A group row shows its kind, name, job count, state pills and latest activity; a **Grouped / All jobs** switch (remembered in the browser) shows the flat list. A group opens in the same view under the shared trail bar, with a summary, state chips that filter, and **Open the task** or **Open the draft** where the person may open it; a job opened from a group keeps the trail; Esc goes up; the group and the filter are in the address (`/settings/jobs/groups/{aiTask|modelDraft}/{id}?state=failed`).
- **Migration `20261124_01`** adds `jobs.task_ref` and `jobs.draft_ref` (generated from `parameters`, with an index on the task) so the grouping reads no JSON per job: on the dev data the grouped read fell from 300 ms to 3 ms.

### Changed (the assistant loads a laid-out workbook and asks only what a person decides, 0.13 AQ)

- **The session limit is a handled ending.** A turn over `AI_AGENT_TIMEOUT_SECONDS` (default 1800, in the settings template and `OPERATIONS.md`) is stopped as a person's Stop is: the session ends, the jobs it started are cancelled, a partial load is undone and the task goes back to its last point with its draft kept. The note says the session took longer than the limit; the job ends `cancelled`, never `JOB_FAILED`, and the log has one WARNING line, no traceback.
- **The draft operations are typed in the OpenAPI.** `POST /model-drafts/{id}/operations` describes `operations` as a list of one schema per public kind (`<Kind>Operation`, discriminated by `kind`), generated from the kinds registry (`@kind(name, params=…)`, the kind's docstring as description). The server's checking is unchanged; a kind added without its parameters fails the contract check.
- **A whole profile in one operation.** `setProfile` takes `sources` and `valueMaps` as `GET /model-drafts/{id}/profile` answers them in `definition`, replaces the draft's profile in one undoable step and queues the dry run. A source's `id` sent back is ignored.
- **A column is named by its letter too.** A column binding takes `letter` in place of `column`, so a column whose header cell is empty can be loaded; the import, a draft's dry run and the draft's column operations (`mapColumn`, `setColumnReading`, `splitColumn`, `ignoreColumn`, `addValuesToList`, `unmapColumn`, `setValueMap`) accept it. The draft also accepts the reader's names for a repeated header (`Checklist #2`).
- **The assistant asks only what a person decides** (`agent/11`): keep-as-is points (two names for one thing, no key column, a repetition kept flat) are one line of the summary, not questions; what the load cannot read is bound by letter; a tested profile is set with one `setProfile`.
- **Answers that keep the defaults cost nothing.** `POST /ai/tasks/{id}/answers` with only the assumed options records them and queues no turn; the task stays `checked`.
- **A waiting task says it waits.** An assistant task carries `ahead`, the assistant jobs before its queued job; the page and the journey bar say "Waiting for the assistant: 2 tasks ahead" instead of "Reading the workbook".
- **Undoing a value map restores that map only.** `setValueMap` records `valueMaps/<name>`, so undoing an earlier one no longer removes the later ones.
- **A request that changes only the model no longer fails** (`agent/12`): when the words ask nothing of the stored records, the session installs one release and makes no change set, and the task ends `loaded` with a migration of no type mappings that the person previews and confirms (nothing moves); an empty change set the session made is discarded. Found in task 99 (relation matrix views).
- **The assistant's questions are no longer cut off** (`agent/13`): a question reached the page as its first 500 characters, so a long reason hid the ask; the text is now kept whole, and the session is asked to put the question first, in at most three short sentences.
- **Answering with the assumed options no longer looks broken:** the draft is already built on them, so the engine starts no new design round; the Questions card now says so and shows "Answer and design again" only once a choice differs from the assumed one.
- **An assistant turn no longer fails on its own scratch files** (`agent/14`): the session's scratch folder is now inside its task folder, and it is told to keep every file there and to retry a refused command instead of ending the turn, a rule every later turn repeats with the paths; a refusal had ended task 95's load turns with nothing done.
- **A change set that adds an application can be browsed in it:** inside a change set (or a publication) the app reads addresses under that change set's own model, not the workspace's active one, so switching to an application only the change set's release has no longer says it "is not in this workspace's model".
- **The migration started from a change set's banner leads back:** the migration page opened from the "Move … and publish" banner shows "‹ Back to the change set “…”" while it runs, waits for confirmation, fails or is cancelled, and once done, with the change set published with the move, offers "Open <application> in <workspace>"; a plain move of the change set offers "Open the change set to publish it". The way back is in the address (`journey=change-set:…`), so a reload or the browser Back keeps it.
- **One key is one record across the sheets of a load** (task 95): two sheets keyed alike for one type (a code list and a person sheet naming the same countries) loaded each key twice, as two half-records; the rows of every sheet with one key are now one record holding all their values and relationships, in the preview and dry run too. Two sheets that fill one field of a key differently refuse both rows, naming each other with their sheet and row (`details.refs`), where the later sheet's value used to win.

### Changed (a draft's dry run reads its own profile, 0.13 AT)

- **A draft's dry run reads the draft's own profile.** `profile` in `POST /model-drafts/{id}/dry-run` is optional: without it the file is read with the profile the draft holds. The profile `GET /model-drafts/{id}/profile` answers is accepted unchanged: its read-only `key`, `unmapped`, `ignoredSheets` and each source's `id` are ignored, where they were refused with `422`.

### Added (findings of the depth waves, 0.13 DF)

- **An earlier contract version of a consumer API is served beside the new one.** A definition may keep frozen copies of itself at older contract versions (`earlierVersions`, each with the day it was superseded and an optional `sunset` day). Every route and the OpenAPI document of a kept version answer from the current data through that version's definition, with `Deprecation` (RFC 9745) and, when a day is set, `Sunset` (RFC 8594) headers; the index lists one entry per version, `CONTRACT_VERSION_NOT_FOUND` names the versions served. A kept version is validated like the current one (a type or attribute the model no longer has refuses the release naming the version) and must read as it did in the active release. A webhook accepted under it keeps receiving that version's shape instead of being suspended, and `POST /consumer-subscriptions` takes `contractVersion` to subscribe to a kept version; the version stops when the administrator removes it, the sunset day being announced, not enforced. In the model editor, raising a contract version keeps the previous one by default; the consumer API's Settings list the earlier versions with their sunset day and **Stop serving**. New operation kinds `raiseConsumerApiVersion`, `removeConsumerApiVersion` and `setConsumerApiSunset`. `COMPATIBILITY.md` says the notice period of a consumer API's earlier version is its administrator's.
- **The Webhooks dialog creates a subscription to a workspace's own events.** **Source** chooses **Consumer API** or **Workspace events**; the latter offers the workspace and its three events (`change-set.submitted`, `change-set.approved`, `change-set.sent-back`) and no filters or content choice, as the engine accepts them.
- **Rotate secret is offered for a deactivated client.** The dialog says the new secret takes effect when the client is restored; the engine already allowed it.
- **The kept earlier version is what was served.** Raising a contract version freezes the definition as the draft's base release served it, not the draft's edited one (an API the base release lacks keeps nothing), so activation no longer refuses the kept version for the edits that made the raise necessary. A subscription to a version not served is refused with `details.servedContractVersions`. **New webhook** is offered when no consumer API declares events (a workspace's own events can always be subscribed to), and a tree view needs a top type before **Add a view** applies.

### Added (images built in CI and CI as a quick gate, 0.13 CL)

- **`.github/workflows/images.yml` builds the engine and web images once** for `linux/amd64` and `linux/arm64` on native runners, starts them with `compose.yml` (`.github/images/compose.smoke.yml`) and checks `/health` and the application, and only then writes the tags in `ghcr.io/refiroo/refiroo-engine` and `-web`: `v<X.Y.Z>` for a stable tag (built only from a commit with a green CI run, and only if the tag equals the version in `backend/pyproject.toml`), `main-<12-character commit>` and `main` for a successful CI run on `main`, and `test-<label>` for a manual run. Pre-release tags are not built.
- **`.github/workflows/images-cleanup.yml`** deletes untagged versions and `main-*` / `test-*` versions older than 30 days each week; stable tags and the moving `main` tag stay.
- **CI on GitHub is a quick gate**: the linter, the backend unit tests and the frontend tests and build, on Ubuntu 24.04. The full suite runs on a developer's machine before a release (on GitHub it took a whole runner hour per push and ran out of memory). The statement counts leave out the assistant's worker thread (0.16), and the batch and move budgets gain two statements: a client token's request reads the client's kind and its assistant task (0.16 ag1, ap9). The dry-run seconds budget is a release check (`budget`).

### Documentation (automatic HTTPS needs port 443 alone, 0.13 CP)

- Port 443 alone is enough for automatic HTTPS (port 80 only redirects `http://` to `https://` and may stay closed); the API description covers every operation.

### Added (the model editor sets everything a model holds, 0.13 ED)

- **A type's Settings tab** sets the attribute that names its records, its effective period (a start and an end date attribute), the attributes of which a record needs at least one filled, and the relationships that place a record under a parent.
- **An attribute type's Settings** set a minimum and a maximum (for whole and decimal numbers), hide it from record screens and give it help text. A type's attribute table has **Hidden** and **Help text** columns for the same on that type alone.
- **A relation type's Settings** say whether it is oriented (deleting a record then removes the relationships it points to). The relations tables have a **Carries** column: the attributes a relationship holds.
- **An application's Settings** set its default view (its colour is drawn nowhere, so it has no control). A consumer API's Settings set its contract version, and a match through a related block can prefer types.
- **On a record page, Header and breadcrumbs…** chooses the title field, the line under it, whether the header names the type, and what the breadcrumbs show. **A table's Sort menu and page size…** and **a panel's Settings…** (the relationships a panel lists, their direction, the relationship column, the sort menu, parent and ancestors, a page size) complete the layout editor.
- **Add a view…** offers a table, a tree, a mapping grid and a relation matrix; a tree's or a mapping grid's **Change…** edits it afterwards.
- **Three deletions have screens.** An import profile and its uploaded file on the profile's page, and a mapping in the Copy and move list, each after a question in its own words; people who may not do it are not shown the button.
- **Server.** New operation kinds `setObjectTypeProperty`, `setAttributeTypeProperty`, `setRelationTypeProperty` and `setApplicationProperty`; `setAttributeBinding` takes `ui` and `setRelationRule` takes `attributeTypeKeys`. The draft's outline carries these settings. An application's `state` is read by nothing and has no control.

### Fixed (command-line tools without a terminal or with --help, 0.13 DOC11 clean-host rehearsal)

- **Command-line tools: `database_upgrade --help` and `generate_key --help` print help instead of doing the work; `create_admin` without a terminal says to use `--password-stdin` instead of failing with a traceback.**

### Fixed (found by the fresh-reader check, 0.13 DOC11)

- **A hierarchy view can take its first top-level record.** The tree only offered Add from an existing record's menu, so an empty workspace had no way to start. The header and the empty state now offer Add for each of the view's top-level types that may stand without a parent, when the view allows creating and the person may write the type.
- **A followed publication's notice opens something.** It leads to the workspace's Publications page; an approval's notice still leads nowhere, as its change set is gone.
- **A retired workspace says it is read-only.** The context band read "Edits apply immediately in this workspace."; it now says "Retired: read only."
- **A supplier profile is read and saved in the workspace of its comparison.** Accept and Ignore on Settings › Import profiles saved against the default workspace's model, so a profile of another workspace's model failed with "The profile was not saved" while its detail said Valid and its header said Needs a fix. The screen now reads the profile, and `PUT /import-profiles/{key}` carries `workspaceKey`, for the workspace of the profile's latest file. The Import dialog lists profiles the same way, valid or not under the release of the workspace the file loads into, so a profile of that workspace's model is no longer shown as no longer valid and can be chosen.
- **"Update them anyway" updates records changed since the export.** An import with `onExisting: "overwrite"` still held a row's exported version against the record, refusing it with `VERSION_CONFLICT` in the preview and the run. A file's version claims (a record's, a relationship's, a relationship list's) are now ignored under overwrite and the previous version is audited; a batch's own `expectedVersion` is still held.
- **Preview again after a delete takes the records' current versions.** A record refused because it changed after the preview was previewed again with the version it was selected with and refused again, offering "Delete 0 records". A refusal for a changed version now names the `currentVersion` (also for `DELETION_PREVIEW_CHANGED`), and Preview again of a bulk action sends it.
- **A released element's refusal says how to make the change.** The model editor said the change "needs a migration (planned for 1.0)", although migrations exist; it now says to make it in the JSON view, where installing the release shows the migration to review.
- **A draft conflict names a rename from its old name.** "Applied since" read "Renamed Reader refactor Admin to Reader refactor Admin"; it now reads "Renamed Reader refactor to Reader refactor Admin".

### Fixed (found by the fresh-reader check of the assistant journey, 0.13 DOC11)

- **A person's Stop in a container shows as their stop.** Ending the session needed `ps`, which the engine's image lacks, and signalled the session's `sudo` with a signal it cannot pass on; the Stop became an internal error and the session kept running. The session is now found by `/proc`, asked to end, and killed only if it does not.
- **A message that asks for a correlation ID shows it.** A task stopped by a failed job names the ID in its warning.
- **A failed assistant job reaches its task when it fails.** The task no longer waits for a page to read it, and the job's result no longer says "Every item applied" when it failed with no item.
- **A correction of a load that fails leaves no change set behind.** The empty replacement the session made is discarded with the failed turn, so no change set is left that no task links.
- **The checked relationship count is the loaded count.** The check of an assistant's items counts each new record's link to its parent, as the load does (164 became 354 in the reader's workbook), and says how many of them are parent links.
- **A records-only words task is named for what it is.** Its trail and journey bar read "Change records" once its proposal leaves the model as it is, not "Change this model".
- **"No change to the model" no longer claims a workbook fits.** For a task without a workbook it says so plainly, and for a draft that changes only views or layout it says no type, attribute or relationship changes and opens the draft.
- **The model summary and the task note use words.** A changed type reads "Changes the attribute that names its records" instead of its key, and the assistant's closing words no longer name its own proposal file or its keys and lists (draftId, moves, removals, movedTo); the instructions ask for plain words and the engine drops the sentences that still do.
- **Go on as it was works after a Stop in the first seconds.** A session stopped before it wrote its transcript had nothing to resume and the next turn failed with no reason; it now starts again with the person's words, and a turn that ends without an answer says so on the task.
- **A partial move is described as what accepting prepares.** The assistant's instructions now say a split of some records of a type is prepared on acceptance as a release beside the old types, a change set and a final release, never as manual work for the person. The note for the removed type says its records move to the new types instead of saying they are deleted, and a partial move whose final release the session did not name says so on the task.
- **A partial move's steps no longer depend on the session's last line.** The engine finds the final release from the releases the task installed (the newest whose types are the change set's release without the old types beside the new ones); the session's `THEN_RELEASE:` line is only a hint.
- **The top "Accept the model" button takes you to Accept.** It moves focus to the Accept button on the page; it focused "Open in the model editor", the first button beside it.
- **A words task has a neutral name until its proposal says what it changes.** It reads "Change with the assistant" before a proposal, then "Change records" or "Change this model".

### Fixed (findings of the documentation waves, 0.13 CP, D-*)

- **Settings › AI says what the Values level sends.** It read "up to N per column"; the code sends every value a feature asks for at Values, and the count only limits Samples.
- **Changing a tree keeps what the form does not show.** Change… on a tree rebuilt its action list from the availability field and one common child sort, dropping declared actions (Create, Rename, Move) and per-type or descending orders. It now sends only the properties that moved: the availability action is added or removed alone, and a new order keeps each type's direction.
- **Oriented says what it does.** The help text claimed deleting a record removes the relationships it points to; deletion cascades to the target records the record owns through required one-to-one or one-to-many relationships of an oriented type.
- **`EVENTS_EXPIRED` on resume tells the truth about the reset.** The message sent the caller to re-sync from the named publication, which may be older than the feed head the reset starts after, so following it literally skipped changes. It now names the head position and tells the receiver to reload from current data taken after the reset. The error code and its details are unchanged.

### Fixed (setting name on the Webhooks screen, password in a restore check refusal, 0.13 FX)

- **The Webhooks screen names the setting that is read.** With webhooks off it said they also need `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`, a setting startup refuses since `SECRETS_ENCRYPTION_KEY` replaced it; it now names `SECRETS_ENCRYPTION_KEY`.
- **A refused `--restored` URL no longer shows its password.** `python -m app.cli.restore_check` printed the value as given when it refused it. A URL that is not PostgreSQL is shown with its password hidden; a value that is not a URL at all is not repeated.

### Fixed (an assistant task makes its own model draft, 0.13 AD)

- **A task whose session opened the workspace's own draft no longer fails at once.** The session is told how to get a draft (`agent/10`): make its own with `POST /model-drafts`, never open the workspace's draft or use one it did not make, and keep its own on later turns. A proposal that still names a draft the task did not create goes back to the session, as a finding does, for up to two rounds; only then the task fails, saying the session must make its own draft, no longer "try again", which could not help. A person's draft is never touched.
- **A load that only adds relationships is a load.** After acceptance the task judged the change set by its records alone, so a session that only linked records ended `failed` with no note. The load's counts now include new, changed and removed relationships (`relationsCreated`, `relationsUpdated`, `relationsRemoved`) and removed records (`deleted`), and the task page names them. A task that fails after acceptance now always says why: no change set of its own named, another workspace, or nothing in it to load.
- **A failed load that left a change set behind keeps it reachable.** The task page no longer says "Nothing was installed or loaded" then: it says what the assistant loaded and into which change set before it stopped, with **Review the change set**, the words box and **Discard the task and its change set**. Trying again or telling the assistant discards that change set first, so there are never two. A failed load is also re-judged when the task is read, so a task the earlier counting bug had failed lands `loaded` by itself.

### Fixed (jobs, client webhooks, the assistant's note, 0.13 FX)

- **Jobs name the workspace by its label** in the list and on the job page, not by its key.
- **A client's page shows its webhooks only where the deployment manages webhook subscriptions**; with them off it no longer shows "Not Found".
- **Cancelling a job asks with its own words.** The confirmation reads **Discard the import** (nothing was written) or **Stop the job**, no longer repeating the button that opened it.
- **The assistant's closing note speaks in the person's terms.** The session is told to name no files, keys, ids, endpoints or commands (`agent/9`), and the engine's closing `CHANGE_SET:` and `THEN_RELEASE:` lines are left out of the note.

### Added (dark screenshots for the website, 0.13 DOC10)

- **`guide/tools/screens.mjs --scheme dark` takes a screen in dark.** It sets the browser's colour scheme and the application's own Appearance setting to dark and writes `<name>-dark.png` beside the light file. Without the flag nothing changes. Eight screens the refiroo website shows are captured in dark; the Stops list's Display panel (`list-display-panel`) now has a screen spec in `_waves/PILOT.screens.json`.

### Documentation (relation matrix columns, 0.13 FX)

- **The guide says how to show only the columns that concern you in a relation matrix.** *Fill in a relation matrix* has a new section, *Choose which columns to show*, and *Relation matrices* explains that the choice belongs to the page open: it is kept in the address for bookmarks and links, not saved for the view or for other people.

### Added (record pages and related columns in the model editor, 0.13 RL)

- **A type's page has one panel per relationship, in each direction.** The page a new type gets, **Declare its page**, a newly allowed relationship and the page shown where an application declares none follow one rule: Details and the hierarchy at the side; in the main region the contained types, then a panel for each relationship the type holds (containment aside), titled as the relationship reads from the type, with the name, the parent type the records sit under, up to four of their attributes and, for several types, their type. A newly allowed relationship also gets a `related:` column and filter on both types' tables, and removing it takes them away; pages written by hand are not rewritten. The frontend's copy is checked against the server's on the guide's example model.
- **Add panel… on a record page**, beside New field group: related records of one of the type's relationships (marked where already on the page), contained records, or a field group, with a region and a title. A new draft operation `addPanel` builds the panel on the server, undone by `removeViewItem`.
- **The Columns dialogs show fields of the related records.** In a table's Columns… each relationship unfolds into the fields of its records and where they sit (Has name translation › Language › Language code); a relations panel's Columns… adds where its records sit (`ancestor:<type>`) and their type when it lists several. Filters still offer the relationship alone.
- **The model editor's preview fills a column showing a field of related records.** The preview's client had sent only bare relation keys in `expand`, so such a column stayed empty until the draft was applied; it now keeps every entry the active model answers.
- **A relations panel that comes to list several record types drops its ancestor sort**, which needs one type: allowing a second type's relation no longer leaves the model invalid (0.13 RL).

### Added (a theme choice: Normal or Website purple, 0.13 TH)

- **Settings › Appearance has a Theme selector: Normal or Website purple.** Website purple is the refiroo website's look (periwinkle, mint, navy, cream, coral) as a second theme of the interface, in light and dark. It is independent of the light and dark choice, which stays as it was and now picks the light or dark of the chosen theme, and of the type colours (A and B apply inside both). The choice is saved in this browser (`rdm:scheme:v1`, JSON `"normal"` or `"purple"`, default Normal) and set as `data-scheme="purple"` on the page by the first-paint script, so there is no flash; the browser's address-bar colour follows. `tokens.css` gains the website's colours as a primitive ramp and two role blocks (light, and dark twice, identical), each setting every role Normal's dark block sets; `tokens.test.ts` checks that, that the two dark blocks match and the contrast of every pair in both, with and without palette A.
- **The guide and the API reference an instance serves follow it too.** Their header bar (`refiroo-header.css`, now with a copy kept equal under `backend/app/management/brand/`), Starlight's variables (`guide.css`) and Scalar (coloured by the same stylesheet) take the purple values, and all three follow a choice made in any of the three tabs through the storage event, as they follow the light and dark choice. The public site's guide build with a host look (`PUBLIC_GUIDE_THEME`) and its API page keep the site's look and ignore the choice.

### Fixed (the assistant in a container, 0.13 DOC11)

- **The assistant's session could not run shell commands when the engine runs in a container.** With `AI_AGENT_SANDBOX=container` Claude Code's sandbox is off, and its don't-ask mode then refused every compound or multi-line command. In a container the session now starts without `--restricted` and with `--permission-mode bypassPermissions` and `--setting-sources ""`; the `assistant` user stays the boundary. Outside a container nothing changes (`app.engine.tasks.agent._safeguards`).
- **Open assistant tasks survive a recreated engine container.** Compose now keeps the assistant's task folders and Claude Code's session logs in the named volumes `assistant` and `assistant-claude`; before, every upgrade (a new container) removed them and a retried task failed with "No such file or directory". Losing the volumes loses open tasks' folders and session logs, not records (`compose.yml`, `backend/Dockerfile`).
- **Compose sets `AI_AGENT_API_URL` to `http://127.0.0.1:8000`.** The session runs inside the engine's container, where `PUBLIC_URL` may not be reachable.
- **The session in a container can use `$REFIROO_TOKEN` in a command.** Claude Code's `blockReadsOutsideWorkingDirectories` refused any compound command that expanded a variable, so most sessions ended early on the Authorization header. In a container the setting is no longer passed (the `assistant` user is the boundary); on the host it stays.
- **"The model: what changes" reads the draft, not its steps.** A task proposal whose draft the assistant made with a single whole-model step said "No change to the model". The task's design now lists the changes between the draft's model and the model it was drafted on (new applications, types, attributes, relationships, changed and removed ones), whichever steps made the draft.
- **The assistant's summary and notes on a task page render as text.** `**bold**`, `` `code` `` and dash lists are shown as such instead of one raw block.
- **The web image builds again.** Two frontend tests read the example model from `guide/samples/model.json`, which the image's build did not copy, so `docker compose build web` failed in the type check (`frontend/Dockerfile`, `.dockerignore`).
- **A proposal lists a type as changed only when it changes, and says what changed.** The outline of a task proposal called a type "Changed type" whenever its attribute list differed in form (default values spelled out, another order, another order number), and never said what had changed. It now compares what the attributes mean (added, removed, required, read-only, screen hints) and reads "Changed type (adds Step-free access, Remark)" or "(changes how FSO number is filled in)". "The model: what changes" gains a row when an attribute becomes required or optional, and no row when a type's description is null on one side and missing on the other.
- **An instruction in words that needs no model change is a proposal, not a failure.** A task without a file whose model does not change (for example "set the Abbreviation of this stop") ended "The session ended without a proposal" because the session named no draft. Such a proposal now lands with `draftId` null and `design.modelUnchanged`: the task shows the summary, "No change to the model", the questions and Accept. Accepting installs and activates nothing; the session makes the change set on the workspace's current live release, unpublished, and the task loads as before. A workbook task still needs a draft, and a draft that is given keeps its checks (drafted by the task, held by no other). The prompt names the case and is `agent/8`.

### Fixed (mapping coverage: several targets on a many-allowed view, 0.13 FX)

- **A mapping row with several targets is "Mapped" where the relation lets a source hold many.** The coverage state called every row with two or more targets "ambiguous", ignoring cardinality. The engine now reads the binding's cardinality at the source end (`one-to-many` outgoing, `many-to-one` incoming and `many-to-many` hold many): there a row with one or more targets is `mapped`, `state=mapped` lists them and `state=ambiguous` returns no rows. Where a source holds at most one target (`one-to-one`, `many-to-one` outgoing, `one-to-many` incoming) the rule is unchanged. The grid hides the Ambiguous filter where it cannot occur and shows the target count on any row with several targets. API, application model and guide pages updated.

### Changed (the public guide build, 0.13 DOC12 with website W4)

- **The public site build takes its address, base path and version from settings.** `PUBLIC_GUIDE_SITE_URL` makes every page name its refiroo.org address as canonical and writes the sitemap; `PUBLIC_GUIDE_BASE` (default `/docs`, `/docs/0.13` for the version before the latest) sets where the build is served, and the static API reference follows it; `PUBLIC_GUIDE_VERSION` shows a version mark after Documentation | API reference and `PUBLIC_GUIDE_OLDER=1` adds "Guide for 0.13 · Latest version" to every page. In the public build the logo leads to the site's home (`/`) instead of the guide's, and under `prefers-reduced-motion: no-preference` pages fly between the site and the guide (`mascot`, `page`, and `terminal` on the API reference). An instance's guide is built and behaves as before. The website's `tools/engine.mjs <tag>` runs the build (`guide/src/styles/public-site.css`, `guide/src/components/Banner.astro`, `app.management.reference.static_site`).
- **A host can give the public guide its own header and look (`PUBLIC_GUIDE_THEME`, 0.13 DOC12 E5).** The setting names an absolute directory: its `Header.astro` replaces the guide's header, its `theme.css` loads after the guide's styles, and its `api/` folder (`head.html`, `header.html`, `theme/`) gives the static API reference page the same header instead of the application's, with the page's Content-Security-Policy naming the header's inline scripts by hash and the page's theme wiring following a header that toggles `data-theme` itself (`app.management.reference.static_site`, `ApiTheme`). Unset, an instance's guide and the API page are unchanged. refiroo.org uses it for its own header, colours and fonts on the guide and the API reference.

### Changed (documentation: automatic HTTPS needs both Compose files)

- **Every page that recreates containers now warns that automatic HTTPS needs `compose.acme.yml` on each command.** A highlighted caution on Install (after `COMPOSE_FILE` is set), Upgrades (before the steps, replacing the one sentence after them), Restore on a replacement host, Configure and Set up AI says to keep `COMPOSE_FILE=compose.yml:compose.acme.yml` set or add both `-f` files: a command without the overlay recreates web without Caddy in front and the site stops answering. Troubleshooting has a row for that symptom (port 80/443 already allocated or missing certificate files after an upgrade); README and `docs/OPERATIONS.md` say the same.

### Added (documentation: production deployment and AI)

- **"Deploy to production with Docker"** (`/docs/run/install-with-compose/`) takes an operator from an empty server to a running instance step by step: the source at a tag, a GitHub App with a short-lived token for a private repository, `.env` filled by commands, automatic HTTPS with Let's Encrypt (`COMPOSE_FILE` set once), the first administrator, backups and upgrades to the next tag.
- **The AI features are documented** for every reader: asking a list in words, proposed mapping targets, loading and changing with the assistant, changing a model from words, accounts of changes, Settings › AI, agent access, assistant tasks for integrators, and setting up AI with a Claude subscription or an API key. Automatic HTTPS is presented as a feature on About and Run.

- **Every picture the guide references exists.** The remaining screenshots were taken on the reference instance (the assistant chain, model moves, a stale migration, history with an assistant's preparation, mapping proposals, a failed provider test, webhooks, sign-in providers, second factors, groups, jobs and the import preview), and every caption was checked against its image. The Run pages describe the assistant's API address under Compose and its two volumes; the words-only pages describe a proposal with no model change. The two example workbooks are downloadable from the pages that use them (`/docs/downloads/`).
- **The fresh-reader check (DOC11), done rather than read:** a fresh session given only the built guide did the quick start, every journey but the assistant one and the production checklist's outside checks, in a browser and with real requests on the reference instance; the run pages' commands were run on a clean host, including an upgrade. What it got stuck on was fixed in the pages, and the product defects it found are listed under Fixed. The assistant journey is read once the assistant work (AT) is delivered.

### Added (branded mail)

- **The five messages the engine sends are branded HTML as well as plain text.** Activation, password reset, test message, inbox notice and digest are multipart: the plain text, unchanged, then an HTML part with the refiroo mascot and wordmark in a lavender band (a renamed product shows its name beside them, as the top bar does), a heading, a button, the raw link for a client that hides the button, and a footer saying why the person gets the message and where to change it (Settings › Notifications), with a link to refiroo.com ("Made with refiroo" before it for a renamed product). The HTML carries the same facts as the text and no more (D421, D432); every value is escaped. The images travel inside the message as `cid:` parts from `backend/app/engine/mail/brand/`, never loaded from the application's address. The sealed outbox text now holds the text and the HTML together (`outbox.pack`/`unpack`), so there is no migration; a message queued earlier is sent as plain text. The test message from the Mail page, sent without the outbox, carries the HTML too.

### Changed (the documentation's sidebar)

- **The documentation's sidebar starts folded.** Only About refiroo is open by default; every other section and its groups start closed. The section and group of the page being read open by themselves, and a reader's own folding is kept as before (`guide/astro.config.mjs`).
- **"refiroo" is marked as the product name in the documentation's text**, in the wordmark's navy (light periwinkle in dark mode), by the build itself (`guide/tools/rehype-brand.mjs`); code and names such as `refiroo-guide-ref` are left as they are.

### Fixed (CI on GitHub)

- **The frontend tests pass under Node 22**, the version CI, the images and the README name. Browser storage is cleared after each test (`src/test/setup.ts`): under Node 22 jsdom kept a saved preference, an open section or a hidden column, into the next test of a file, while Node 26 leaves `localStorage` undefined, so the leak did not show on the developer instance. The release detail test waits for the activation check's request instead of expecting it with the first text. `docs/testing/EXECUTION_GUIDE.md` lists the AG3 browser module.
- **The backend tests run in parallel in CI**, `-n auto` and then the `serial` tests, as the execution guide runs them; a single process took about an hour. The job stops at 40 minutes. A tag push no longer runs CI a second time for the same commit, and the frontend job installs Playwright's Chromium for the gate-helper test (`.github/workflows/ci.yml`).
- **One ruff for CI and the developer instance:** `ruff==0.16.5` in the dev dependencies (0.17 dropped DTZ001 and refused the `noqa` comments 0.16 needs); the import order and a nested `if` it reported are fixed.

### Changed (the starter model only)

- **`model/` holds only `rdm-starter.json`.** The consumer API document tests run over the starter model, with its `rdm` definition widened to every type where a test needs the whole model.

### Fixed (a released consumer API's key fact)

- **A released consumer API no longer says "Key fixed: released".** Its key can be changed, as D55 decided, and **Change key…** stays offered; the fact now reads **Released: a new key moves its address**, and its tooltip says consumers of the old key get 404 once the draft is active (the contract check warns `CONSUMER_API_REMOVED`). An unreleased one reads **Key editable**. Model elements keep **Key fixed: released**. The guide's Define a consumer API and Consumer APIs in the model pages say the same.

### Changed (one header, 0.13 HD)

- **One header for the app, the guide and the API reference.** The three bars share the height, surface, rule, mark and ink underline (`frontend/public/brand/refiroo-header.css`, served at `/brand/`); the logo leads to the app's home, Documentation | API reference come before the guide's search, and the API page drops Scalar's own dark-mode toggle. **"?"** in the app bar, left of the bell, opens the documentation in a new tab. One theme choice: the guide and the API page read and write `rdm:theme:v1` (System, Light, Dark) and, with the app, follow a change made in another open tab. A public site build sets `PUBLIC_GUIDE_SITE=1` and sends the logo to the site's home (first the guide's home; changed by the entry above). **The public site has the API reference too:** `npm run build:public` in `guide/` (with `GUIDE_OUT` to build elsewhere) builds the guide for the public site and writes a static `/docs/api/` beside it with the engine's own page (`render_page`, in its static form: no sign-in script, no test-request button, the Content-Security-Policy in a `<meta>` element), Scalar's bundled script, the management API's document (from the code, no database) and the `stops` consumer API of the guide's reference domain (`guide/samples/model.json`), titled as the example. The module is `app.management.reference.static_site`; an instance does not use it, since the engine serves `/docs/api` from its route before the guide's files.

### Changed (image layout)

- **The images keep everything under `/opt/refiroo/rdm-engine`**, laid out as the repository is (`backend/`, `guide/dist`, `model/`, `data/`, and in the web image `frontend/dist`, `frontend/certs`, `frontend/nginx`), and add nothing at `/`. An existing installation mounts the job-files volume at `/opt/refiroo/rdm-engine/data/job-files` and the certificate folder at `/opt/refiroo/rdm-engine/frontend/certs`; `compose.yml` does both. `AI_AGENT_FOLDERS` defaults to `/opt/refiroo/rdm-engine/data/assistant`.

### Added (the guide's foundation, 0.13 DOC1)

- **The guide at `/guide`.** A static site built with Starlight from the new `guide/` folder and served by the engine offline, from the version it runs; the web image's proxy forwards `/guide`, and `/docs` and Settings › About link to it. A checkout that has not built it starts as usual and `/guide` says how to build it. The engine image builds the guide in its own stage and carries only the built files.
- **Page kinds, templates and checks.** Every page is a tutorial, how-to, explanation or reference with front matter for its reader, covered items, required statements and examples; the build refuses a stub. `npm run check` (front matter, stubs, template headings, banned terms, the spelling "refiroo", examples) and `npm run check:links` run from `guide/`; `guide/AGENTS.md` holds the writing rules and the process for writing a page from its brief.
- **The `docs` test group.** `pytest -m docs` runs the guide's examples against the engine seeded with the starter model (IDs and times normalised; model examples through the engine's validation); a page prints the same file it was tested from. `python -m tests.affected` selects it when a file in `guide/examples/` changes.
- **First page: Three kinds of change.** `node e2e/accessibility-gate.mjs --only guide` runs the accessibility checks on the guide through the running engine, light and dark, at 1440px and 390px, and fails if the page asks for anything outside the engine.
- AGENTS.md: a change to user-visible behavior updates the guide pages that cover it, in the same change.

### Added (the guide's page inventory and the briefs of waves A and B, 0.13 DOC3 part 2)

- **Every page of the guide has an owner.** 143 stub briefs in `guide/_briefs/` (title, kind, reader, wave, the inventory items and required statements each owns); `npm run check:coverage` shows no unowned item. The generated reference pages own the rest of their kind (`kind:*`); 0.16's items are listed in `guide/_coverage/wave-g-items.txt` for wave G.
- **Full briefs and tested examples for waves A and B** (how refiroo works, run refiroo, administer access and security): 53 briefs, 72 new examples run by the `docs` group, and `npm run check:briefs`. Prompt files `guide/_waves/DOC4.md` and `DOC5.md`.
- **A stale coverage inventory fails the `docs` group**, and `GUIDE_RECORD=1` records an example's expected responses from what the engine answered; signed cursors are shown as `<cursor>`.

### Added (the guide's reference domain and coverage inventory, 0.13 DOC3 part 1)

- **The guide's running example is in `guide/samples/`.** The public transport stops of Graubünden from open data (opentransportdata.swiss and Wikidata, attribution in `SOURCES.md`) with one fictional ticketing system and one fictional workbook: the model, two dated data sets (docs, 598 records; reference, 3,528) and the scripts that fetch and load them. `python3 guide/samples/load.py --set docs|reference --base <instance> --env <env file>` loads either set through the public API.
- **A reference instance for the guide** (`guide/reference/reference.sh up`): the engine image on Compose project `refiroo-guide-ref`, ports 8480 and 8443, with the reference set loaded and generated secrets in a git-ignored `.env`.
- **The `docs` group seeds the docs set** instead of the starter model; the proof page's examples run on the reference domain.
- **The coverage inventory.** `npm run inventory` lists what the guide must account for (capabilities, journeys, settings, error codes, commands, roles, permissions, event types, model-language fields); `npm run check:coverage` compares it with the briefs and pages, and `-- --strict` is the release gate.

## [0.16.0] - 2026-11-02

The assistant and the agents: a person says a few words, uploads a workbook and gets the model and the import, with an
AI assistant that runs as a Claude Code session through the engine's own capabilities and is limited only by what they
can express. An AI proposal provider (Claude or an OpenAI-compatible one) with a send level and call records, targets
for unmapped values, the assistant's instruction-driven tasks that design, check and load, a change of a workspace's
model with its records moved, always a way out of a failed task, agent access (`/mcp` with read tools, changes prepared
and submitted for approval, and natural-language search), an account of a model change, an account of what changed in a
period, and notification digests with following a workspace. The contract change is additive. Upgrading from 0.12: the
migrations run with `python -m app.cli.database_upgrade` ([Upgrades](docs/OPERATIONS.md#upgrades)) or at startup; the AI and MCP settings are in [OPERATIONS](docs/OPERATIONS.md).

### Fixed (the 0.16 release review)

- An assistant's refresh token no longer opens the API console's management token or the engine's own pages (it is no browser session).
- A Claude Code session never writes live data: a batch or an import naming no change set is refused `403` for it, and the write unit refuses it again. An assistant task takes a draft or a change set on its word only when its own client made it, so discarding or expiring a task never deletes a person's draft; the grants a turn leaves behind are removed first and the turn's grants end even when it fails to start; the two roles the session's grants use are checked on every turn and a changed role refuses the turn (`AI_ASSISTANT_ROLE_CHANGED`).
- Correct, accept, retry, answers and run call the assistant's checks again, as creating a task does. The person's words are the last command argument after `--`, so none is read as an option. The engine's OpenAPI read and the session's `curl` verify TLS unless the API address is on this machine. A container's session runs as a separate user (`assistant`, through `sudo`) that cannot read the engine's environment or the job files (R-F45).
- A load of a design is refused `409 AI_TASK_CHECK_STALE` when the draft changed after its check. A turn's words and start stay until the turn is recorded; a load turn a stopped worker left is undone before it loads again; a session's jobs that outlive the session's time are cancelled and undone; the task row is not locked while the workbook is copied and the OpenAPI read; a stop that undid nothing no longer says it did.
- The agent access endpoint limits registrations per address, caps a registration at ten addresses of 2,000 characters, and re-checks a self-registered address against the listed hosts on every sign-in. Every call, a failed lookup included, is recorded, and tool and resource listings count against the rate limit. `create_change_set` finds the change set a retry already made.
- An account of what changed names a job's file and links the job only for a reader who may see the job; two activations of one release are two facts; a statement may cite only facts the provider was sent; a provider's error no longer carries its address.
- Migrations: a role of the instance's own called `agent` is kept under the next free `agent-N` key with `(custom)` in its name; only the engine's own shared assistant client is deactivated, not an integrator's of the same name.
- Imports: a row finding its record by a value another row writes, and the merge of repeated keys, run as one pass each. A person deleting a row the assistant marked in a change set is named in its origin.
- The assistant's task page: a stale check hides Load and says so; Accept follows Work in change sets unless the proposal moves whole types; installing a model needs the instance-level Model release; the offers need Bulk and import and job creation; one stream per task however many parts follow it; the Apply dialog never installs twice and lists every other workspace; the Follow button's name holds its visible word.
- The deployment's `compose.yml` reads its settings from `env_file: ${RDM_ENV_FILE:-.env}` again; a 0.16 AP1 change had broken the file name the deployment runner passes, and the runner stopped.
- The browser stand-ins for the assistant read the person's words after `--` as the prompt, as the real Claude Code does (checked once with the real one: a prompt beginning `--add-dir=/etc` was read as words).
- With agent access off, the protected-resource documents and `/oauth/register` answer `404` in the OAuth error shape (`error`, `error_description`) instead of a bare `detail`; J47's route tables now hold them and AP13's `/proposal` (R-F46, found by the J47 cases run on the release snapshot).

### Added (notification digests and following a workspace, AO3)

- **A digest instead of many mails (0.16 AO3).** On Settings › Notifications each kind of notice is mailed **at once** (what every kind stays until changed), **in the digest** or **not at all**, and the digest comes every morning or on Mondays at 07:00 in the time zone the browser reports; the page says when the next is. One message says in a sentence how many notices of each kind wait ("3 change sets wait for your approval; 1 job you started failed"), then lists up to 50 newest first with their kind, time and a link that opens the notice, and "and N more"; a job's line adds its kind and the rows applied and rejected while the job is kept. It names no record, change set, workspace, person or file (D432); there is no AI in it (AO-D32). Nothing new, or everything read before then, makes no mail; the sender's round makes the digest with the person's row locked and the next time moved in one commit, so two processes make one. `GET`/`PUT /me/notification-mail` take `kinds` as `now`, `digest` or `off` and a `digest` of `every` and `timeZone` (`422 UNKNOWN_TIME_ZONE`, `422 DIGEST_NOT_SET`) and answer `delivery` per kind and `digest.nextAt` (pre-1.0: `enabled` per kind is replaced by `delivery`). Migration `20261123_01`.
- **Follow a workspace (0.16 AO3, AO-D38).** A Follow / Following toggle on each workspace card on Home (`following` on `GET /me/workspaces`) and Workspaces I follow, with Stop following, on Settings › Notifications; `GET /me/followed-workspaces`, `PUT` and `DELETE /me/followed-workspaces/{workspaceKey}` (`404` for a workspace the person cannot browse). A change set published there, from an approved request or directly, puts a `change-set.published` notice ("A change set was published in a workspace you follow") in each follower's inbox who still holds Browse there, not the publisher's, written in the publication's transaction by one `INSERT … SELECT`. It is a kind like the others: at once, in the digest or no mail.
- **A digest's link opens the notice.** `/notifications?notice=<id>` opens the notice's subject as a click does (a followed publication's notice opens the publication, while it is the active one) and marks it read; `GET /me/notifications/{id}` reads one of the caller's notices.

### Added (always a way out, AP13)

- **A task is never left with only Back (0.16 AP13).** A turn that failed shows its reason on the page (the task's own notes) and takes the person's words: `POST /ai/tasks/{id}/model` now works in every state a task can go on in (a proposal, a failed or stopped task, a saved layout's load stage, a loaded change set not yet published), and `POST /ai/tasks/{id}/retry` takes optional `words`. The same session goes on, or starts again on the same task, file and words when it never ran. The page's words box is one component (`TellAssistant`) wherever it appears.
- **Stop ends the turn, not the task.** `POST /ai/tasks/{id}/cancel` now also works while a load runs. A stopped correction returns the task to its last proposal with a note (and a warning when the turn had already changed the draft); a stopped load discards the change set it was making, stops the jobs the session started and returns to the accepted proposal; a turn stopped before any proposal leaves a `stopped` task (a new state, migration `20261122_01`) that takes words or Discard. `POST /ai/tasks/{id}/discard` is the one way to end a task and now also ends a `failed`, `stopped` or loaded one (a loaded task's change set goes with it).
- **A load that is wrong takes words.** Words on a loaded task discard its change set (the page says first that any edits made in it go) and the same session loads again with them. The session's folder, transcript and client now stay until the change set is published or discarded, the migration confirmed, or the task discarded or expired (revises AP-D37's timing); the next read of the task ends the session, records a publication (`result.published`, `result.publicationId`) and ends a task whose change set was discarded elsewhere.
- **A published task points onward** with Change this model… and Ask about these records…, the same offers as the workspace menu (one hook, `useAssistantOffers`, for both). An offer, and the Accept and Load buttons, appear only for a person who holds every group the steps need, Work in change sets included; `POST /ai/tasks/{id}/accept` refuses without it (`403 FORBIDDEN`) unless the proposal only moves whole types, and a person who lost it is told who can load, with the task's link to copy.
- **The smaller states.** The check before a saved layout's load has Back to the proposal (`POST /ai/tasks/{id}/proposal`) and the words box; a saved layout that no longer fits offers Read it with the assistant; a migration the engine refused is shown on the task with the words box; a task that expired or never existed says so and leads to the workspaces. `canTell` on a task says whether the assistant can be told something now.
- **A refused step of a reshape is shown on the task.** The next step that activates a release is checked with the release page's own check, and the engine's reasons appear above the words box. A loaded task recorded before AP13, whose folder went at its load, ends its session at its next read (`canTell` false) and offers Discard and the ways onward. The journey bar no longer offers Accept or Load to a person without Work in change sets.
- **A column no source reads is said before the proposal is accepted (found on the real walk-through).** The proposal's checks name the filled cells of the tables a design reads that none of its sources covers (`cellsLeftOut`, e.g. a column under an empty header): the walk-through's workbook lost the Spanish names of two lists' entries without a word. `design.checks[].kind` gains `cellsLeftOut`.
- A task's notes show the newest three and fold the earlier ones, and a task that goes on from a failure or a stop clears the reasons it stood on.

### Added (a job's page says what it did)

- **A move's and a migration's job page (0.16).** Settings › Jobs › one job shows a move's sentence and four counts, its record and relationship types (made, refused, not moved), and its items filtered by outcome and reason, refused first; names link to the records in the source workspace and a refusal by a model rule links to the model. A migration shows its counts and items by outcome. A job with nothing to list (an assistant task, a model draft's inference or check, a mapping proposal, an import profile's check) says what it belongs to and links to it only where the caller can open it; a mapping proposal job shows its tally. The move editor's report draws its rows with the same table (columns Item, What, Why, Fix); a move or migration job is titled "Copy into X", "Move into X" or "Migration" instead of "Batch". No API or database change: `GET /jobs/{id}` already carried the `move` and `migration` summaries.

### Added (change the model from the workspace, and move the records with it, AP12)

- **"Change this model…" on a workspace's ⋯ menu (0.16 AP12).** Where the assistant is on and the person holds Use AI proposals, Model authoring and Model release in the workspace, the menu opens the same dialog as Load a workbook with the workspace fixed, the words first and a workbook optional. The task page's title and crumb no longer say "Load a workbook" for a task with no file.
- **Two ways to move records between types.** A whole type that becomes another (a rename, a merge, into another application) goes by one migration: the proposal's `moves` are checked against the draft with the migration's own plan, shown as a table of each type, what it becomes and the records it holds, and the task ends with `result.migration` instead of a change set; **Preview the migration** opens the migration page with those choices and **Back to the proposal** returns. Part of a type goes by the 0.8 restructuring in a change set on a release holding both shapes, and the task ends with `result.changeSetId` and `result.thenReleaseId`; the task page shows the three steps (activate both shapes, publish, activate the final release) one at a time. Records keep their IDs, values, relationships and history either way.
- Prompt `agent/5` tells a session that a record changes type and keeps its ID through a restructuring or a proposal's `moves`, and the endings to use. `design.moves` and `result.migration` and `result.thenReleaseId` are new in the task; `result.changeSetId` may be absent. A release named by `result.migration` or `thenReleaseId` is not retired with the task. No migration of the database.
- **A merge the consumers would notice no longer ends in a refused preview (0.16 AP12, fixed after the real try).** The proposal is checked against the consumer contract as the migration preview and an activation check it: a draft that breaks a consumer API without raising its `contractVersion` goes back to the session (twice at most) and fails the task naming the API if it still does; the final release of a part-of-a-type reshaping and the installed release are re-checked likewise. The proposal says, for each consumer API whose version it raises, its name, the old and new version and what its consumers stop reading (`design.consumerChanges`, from the engine's diff). Prompt `agent/6`.
- **A merge the records would be refused for no longer ends in a refused preview (0.16 AP12, fixed after the second real try).** The proposal's moves are checked against the workspace's live records by the migration preview's own check (every record, set work in PostgreSQL, nothing written): a draft that leaves the moved records no place under their parents goes back to the session with the engine's code, message, count per type and example names (twice at most), and fails the task with that reason if it is still refused; the installed release is re-checked on accept. The proposal shows what each moved type would lose (`design.moves[].lost`). Prompt `agent/7`.
- **A reshaping that keeps the old type no longer shows a step with nothing to do (0.16 AP12, fixed after the third real try).** When the session's final release is the change set's own release (a split that leaves the old type beside the new), the task page shows "Two steps are yours" and no "Remove the emptied types" step; after publishing it says the workspace runs the new model, whenever the page is opened: the result carries `changeSetReleaseId` next to `thenReleaseId`, and the page compares the two.

### Fixed (a removal in the model editor leaves nothing dangling, and every broken page is named)

- **Removing an application, a type or a relation binding takes the panels and views that depended on it.** A relations panel on another application's page that listed a relation its page's type no longer has loses that relation (and the columns only the dropped types gave it), and goes when none is left; a mapping grid or relation matrix over a gone binding goes, with the navigation entry it leaves empty. The relation types and attribute types a removal leaves without a binding go too, released ones included, unless data holds them; one still bound stays even with no data (D31, the same rule for every removal, merge and parent change). One undo restores all of it; adding a relation is now undone by restoring what it changed.
- **The compiler reports every broken view and page problem at once** (a view, a detail page header, each panel) instead of the first; other rules still stop at the first.
- **A panel issue leads somewhere.** `diagnostics[].element` of the draft's outline names `applicationKey`, `detail` and `panel`; the issue links to the page's type and offers Remove from page, which works while the draft is invalid (Edit layout stays closed). The message is plain: "The Stock panel on the Bin page lists a relation Bin no longer has (…). Remove the panel or restore the relation."
- **A step that leaves the draft with more errors says so** in a popup with the count and Show issues, whatever caused it (a step, undo, redo, a JSON edit, an applied proposal); opening an invalid draft does not. The Apply and Install dialogs' "Not valid" notice links to the Issues list.

### Added (what changed in a period, AO2)

- **"What changed" above a workspace's Activity and on a record's History (0.16 AO2).** Where a provider is set and the person may browse and holds Use AI proposals, Explain this period puts the changes of a period (7 days on a workspace, 30 on a record, or dates) into a few plain statements, each followed by numbers that lead to the facts it rests on. The engine counts the facts in the database over every change to live data: records per type and action, fields, relationships, sources (a job, a publication with who prepared and published it, or direct), people, change sets, withdrawals and model activations. Show them narrows the Activity, or the record's timeline, to the changes a fact counted; a fact also opens its job or change set. Names go to the provider only at send level `values`.
- `POST /workspaces/{key}/history/account` and `POST /objects/{type}/{id}/history/account`, the purpose `historyAccount` (offered at every send level) and `HISTORY_PERIOD_INVALID`. `GET /changes` gains `objectTypeKey`, `relationTypeKey`, `causeId`, `action`, `attributeKey` and `live`, and a record's history gains `live`. The shared parts of the account moved to `summaries.py` and `ui/AiAccount`; the model change's account behaves as before.
- **`history_facts`, an assistant's tool (0.16 AO2, AO-D28).** With Browse only, an assistant asks for the engine's facts of a workspace, or of one record (`objectType` and `id`), over `[since, until)` and an optional `timeZone`, and words them itself. It runs the account's own scope, period and facts, with no provider call, no `ai_summaries` row and no call record, and is refused as the route is: a workspace it cannot read, a missing record, `HISTORY_PERIOD_INVALID`. The agent ceiling is unchanged.

### Added (an account of a model change, AO1)

- **"What this change does" in the activation dialog and in Apply (0.16 AO1).** Where a provider is set and the person may activate releases and holds Use AI proposals in the workspace, pressing Explain this change puts the change into a few plain statements, each followed by numbers that lead to the facts it rests on. The engine writes the facts (each difference between the models, each rule the workspace's data would break with its count, what the consumer APIs would notice, whether activation is refused, the workspace's records per touched type, counted over the whole set); the provider only words them, is sent at most 40 of a kind with each kind's true total and no record, and is told never to judge. A statement with no source is dropped and counted; when the provider fails the facts stand alone with Try again. The same facts asked within the hour are answered without a second call. Nothing is sent until the person asks.
- `POST /model-releases/{id}/impact-summary` and `POST /model-drafts/{id}/impact-summary` (the second where model drafts are), the purpose `impactSummary` (offered at every send level), the table `ai_summaries` (migration `20261121_01`, an hour's cache) and `IMPACT_SUMMARY_DRAFT_INVALID`. Use AI proposals now also covers summaries.

### Changed (a hint beside the relationship panel's heading)

- Why a record is not offered a relationship ("Only … can have this relationship.") is no longer text under the panel's toolbar: a small blue circled "i" beside the panel's heading shows it on hover, on keyboard focus and on a tap, one reason per line. The hint is a shared `InfoHint`; it appears only when the reason applies to that record.

### Changed (the model's language in the API, AP11)

- The API's OpenAPI document now describes the model: the `model` field of model requests and responses names `EngineModel` and its definitions. Validation is unchanged, so a wrong model still gets the compiler's diagnostics.
- An assistant session's log is kept beside its folder rather than inside it, and goes with the folder.

### Changed (one path for the assistant, AP10)

- A session builds everything the words ask for, as they place it and also with no data in the file; a question no longer replaces building.
- Switching workspace from a page the other workspace's model lacks now writes the start page it opens to the address, so a reload no longer says the page is not in the model.
- A session no longer stops with an internal error when its stream carries a system event whose message is text, as a refused permission does.
- An assistant check counts a row skipped only when a value on it is lost: an empty cell in a list's column no longer reads as a skipped row, and `unchanged` counts records, not links.

- **`AI_AGENT_COMMAND` alone turns the assistant on.** `POST /ai/tasks` is `409 AI_NOT_CONFIGURED` without it
  and no longer needs `AI_PROVIDER`, which serves mapping targets and later features only. `GET /ai/status`
  answers `assistant`; Settings › AI says what each setting gives and opens if either is set.
- **The rules-only task path is removed:** `POST /ai/tasks/{id}/plan`, `plan` on a task, `table` on
  `GET /ai/tasks/{id}/changes`, the relationship rules (`design.links`, `check.links`, `result.linksJobId`),
  `AI_MAX_STEPS` and the provider purpose `workbookLoad`, with their Reading and Check pages. A saved layout
  that still fits takes the engine's path with no AI.
- **A load leaves a saved profile.** The engine saves it from the change set's imports (`result.profileKey`),
  checked against the change set's release, or says why it did not (`result.profileNotSaved`): a source with
  no key, a change made only through batches, a profile already saved.
- **A proposal warns of new records beside held ones** (`design.checks` kind `besideHeld`).
- **A check tells skipped rows and an old check apart:** `check.summary.skipped` no longer counts as refused, and
  `check.draftChanged` says the draft moved after that dry run.
- **A saved layout fits a workbook with sheets its profile left out**, if the earlier file had them too; its
  summary gives the profile's own figures.
- **A session is refused a draft another task holds** (`409 AI_TASK_DRAFT_HELD`), and unused releases a task
  installed are retired when it loads or is discarded.

### Added (a key of several columns, AP10)

- **`SourceKey.attributeTypeKeys`** in an import profile: two or more attributes, each bound by a column, whose
  values together find one record, live and in a change set. A combination two records hold refuses the row
  (`KEY_AMBIGUOUS`); an empty cell is a row without a key (`MISSING_RECORD_KEY`, or `rowsWithoutKey`); an
  unbound attribute is `KEY_NOT_BOUND`. The assistant gives each source such a key. Batch `upsert` keys are
  unchanged.

### Added (who did the assistant's changes, AP9)

- **Provenance on a session's changes:** a record or relationship the assistant proposed carries `origin` (who asked,
  who edited it afterwards, the task) in the change set and, once published, in history, removals included.
  `ProposalOrigin` gains `editedBy`, `editedByName`, `proposedByName` and `taskId`.
- **One client per task:** `ai_tasks.client_id`, client kind `session`, left out of `GET /clients` unless
  `kind=session`; `409 CLIENT_HAS_NO_SECRETS`.
- **The call record holds a session's runs:** purpose `assistantSession`, `costUsd`, `taskId`, failure kinds `timeout`,
  `cancelled` and `interrupted`; Settings › AI shows them with their cost.
- **Retention** removes a task's folder and Claude Code's transcript with the task.

### Added (changing a workspace's model)

- **Edit model from the workspace:** a ⋯ menu beside the workspace selector, and a button on the workspace's page
  in Settings › Workspaces, open the model editor on that workspace's draft. **Apply to this workspace** says what
  changes and what happens to the records, installs, then activates or migrates there alone, and returns to the
  workspace. `POST /workspaces/{key}/model/draft`; a draft's `workspaceKey`. Model release in a draft's workspace
  now allows installing that draft.

### Changed (Import and Export)

- **Import and Export moved** from the collection's header into the workspace's ⋯ menu. Export still exports what
  the page shows.

### Fixed (the assistant's pages)

- **Load a workbook is offered only where a session is set up** (`ai.assistant` on `GET /system`, `AI_AGENT_COMMAND`),
  and says what the session is given. With a provider alone, Import is the ordinary dialog.
- **The proposal's correction box** is three lines, not 440px. **The loaded page** no longer says a session's changes
  note the assistant, which they do not yet.

### Added (asking a list in words)

- **Ask a table list in words (0.16 AG4).** Where a provider is set and the person holds Use AI proposals, a Search | Ask switch sits at a table list's search box. Pressing Enter on a question sends it (nothing is sent as you type; Cancel stops it); the list shows the filters it became as ordinary pills, with "Your question became these filters. Change or remove any of them." A part the list cannot express (an order, who changed a record, a record that is not found or is named by several) is named and nothing is applied: the proposed filters are shown as dashed pills with Use these filters. A failure is one sentence and the words stay. The provider is sent the question, today's date and the list's fields, every relationship the type has (declared by the view or not), and, at send level `samples` or `values`, the record names of a relationship's types when they hold at most 50 records, so it can choose records by meaning ("above 100 km" from "120 km" as one `eq` filter each); at `structure` no record is sent. A filter on a relationship the view does not declare is drawn as an ordinary pill and kept in the page address. `POST /workspaces/{key}/query-translations` answers directly; new codes `QUERY_TRANSLATION_FAILED`, `QUERY_TRANSLATION_VIEW_UNSUPPORTED` and `VIEW_NOT_FOUND`; no new setting.
- **List filters: under an ancestor, and the stamps.** `filter.related:<key>.under=<record ID>` and `.notUnder=<record ID>` keep the records with some, or none, of their related records below a record at any depth (live, in a change set, in a publication; the query and an export say the same with `ancestor:<type>` inside a related hop). The filter bar's relationship editor offers "has none under" and "has any under". `createdAt` and `updatedAt` filter every live list without being declared, and a field with two conditions (a date range) shows a pill for each.

### Added (agent access)

- **An assistant can prepare a change (0.16 AG3).** With Work in change sets, an assistant creates a change set, adds and changes records and relationships, sets a field's value, reads the validation and submits it for approval, in change sets its own person or client created and never a colleague's. It cannot remove or clear anything, withdraw, discard, batch, restructure, approve or publish; change reaches live data only when a person approves it. A refused call tells the assistant the engine's code and details. Its rows say "Prepared by an assistant" with the name it gave itself (`origin` of kind `agent`), and `channel` `mcp` is on `GET /changes` and a record's history for what was done through an assistant. `changeSetId` joins `find_records`, `read_record` and `describe_type`. No new setting.
- **An assistant can read (0.16 AG2).** A signed-in assistant or agent client can look up a value through a tool generated from each consumer API, list a mapping view's unmapped values, find and read records with their relationships and history, read a workspace's changes, and read the model as tools and as resources. New setting: `MCP_ANSWER_BYTES`.
- **An assistant can reach refiroo (0.16 AG1).** With `MCP_ENABLED`, an assistant that speaks MCP connects at `/mcp`. A person adds the address and signs in on refiroo's own page, which says who asks and where it returns; a system uses an agent client. It works within what its person or client may do, cut down to reading and preparing changes, and can never approve or publish. Two tools so far: who it acts as, and the workspaces it may read.
- **Settings › Security › Agent access** shows how to connect, the agent clients, the assistants people sign in with and each call, with argument names and never their values. Blocking an assistant or deactivating a client stops it on its next call. People see their assistant among their sessions.
- API: `/agent-access` and its lists, `kind` on clients, `application` on sessions, `mcp` on `GET /system`, `/.well-known/oauth-protected-resource`, `POST /oauth/register`. Settings: `MCP_ENABLED`, `MCP_RATE_PER_MINUTE`, `MCP_OPEN_REGISTRATION`, `MCP_REDIRECT_HOSTS`, `MCP_CALLS_DAYS`.

### Fixed (the AI import)

- **The same words give the same kind of model:** a session separates what a workbook repeats into types of its own and
  raises it as a question if it keeps it flat; what the workspace holds decides whether it adds to the model or may start
  anew. The proposal shows attributes and records per type from the engine's figures, counts relationships apart from
  records, and warns when a model leaves out types holding records.
- **A session's own jobs run:** an assistant's session held the only job worker while it worked, so a
  job it queued, such as profiling its workbook, waited until the session ended and then failed because
  the session's grants had ended too. Sessions now run on an assistant worker of their own (reported as
  `assistantWorker` among a process's threads), and their grants stay until the jobs they queued are done.

### Fixed (opening a record from another application)

- **A record opens where it stands:** opening a record from an application that lists its type but does
  not hold it, such as from a matrix row, now goes to the record's own application. It said "This object
  belongs to another application" before.
- **The session's checklist shows what happened:** a step was ticked as soon as a command mentioned its
  address, so "Model changed" and "Every row checked" appeared before either happened, and a refused load
  counted as loaded. Steps now come from what the engine recorded: a check counts until the model changes
  again, a running one shows as in progress, and a turn lists only what it can reach, the model and its
  check first and the release and the load after acceptance.

### Fixed (relation matrix cells)

- **A matrix cell shows the view's cell fields:** a cell now reads the first of "Fields in a cell" with a
  text or number value, and the record's name only when none has one. It always showed the name before,
  so records named by a code showed the code.

### Added (model editor, relation matrices)

- **Add a relation matrix in the editor:** an application's panel has a Views section listing its views.
  "Relation matrix" there opens a dialog offering only rows, cells, columns and actions that can work,
  with a preview of the shape chosen. The types the matrix needs are listed in the application in the
  same step; their records stay where they stand. A matrix can be changed, renamed and removed, and a
  removal takes along the types only it needed.
- **List a type in another application:** `listObjectType` and `unlistObjectType`, and "List an existing
  type" in the editor. A released listing is not taken away without a migration. `removeView` takes
  `unlist`; the draft's outline gives each application's `views` and `unlistable`.

### Changed (model editor, released elements)

- **A released element nothing uses can be changed:** a removal or other draft-only change applies when
  it would affect 0 records, values and relationships in the workspaces running the model and their
  change sets; above 0 it is refused with its impact, and activating the release checks the data again.
  A released key stays fixed whatever the data, and the refusal now says so.

### Changed (model editor, choosing a relation)

- **Types and relation types sharing a name can be told apart:** in the model editor's pickers, a type
  whose name another type shares shows the applications listing it, and its key where those match too,
  with a note that the two hold separate records. A relation type shows the types it stands between;
  those already reaching the chosen type come first, and a note says how it reads in reverse, which
  pairs use it with their rules, and what choosing a new one leaves out. The draft's outline gives a
  relation's `uniquePer` where it has one.

### Added (0.16 AP6, the assistant designs and loads)

- **The assistant is a Claude Code session:** with `AI_AGENT_COMMAND` set, the person's words, the
  workbook, the model and the OpenAPI document go to one session working through the API. It stops at a
  model draft with every row checked; the person opens it in the model editor, answers or says what to
  change, and the same session goes on. Accepting installs one release, unactivated, and loads a change
  set; activation stays with publishing. The page shows what the session has reached while it works, and
  has Discard and Close. The turn loop, its answer format and `unpivots` are gone. A saved layout that
  still fits needs no AI; `key.storedUnique` keys a source by an attribute whose stored values are unique.
- **Guards on the assistant's session, for sessions refiroo starts only:** the operating system's sandbox holds it to its folder and this engine, it has only file and shell tools and none of the server's secrets, and its client cannot publish, activate or reach another workspace. A stopped session can be tried again. The engine image holds Claude Code (`AI_AGENT_SANDBOX=container`).
- **Imports reach every column of a repeated heading:** where a header repeats a name, the first column has the name and each later one the name with its place, `Currency #2`.
- **Words alone start a session:** a task without a file no longer stops with an internal error.
- **An empty change set is no load:** the task fails with what the session said, and can be tried again.
- **An import's request sent as a file part** is checked against the workspace it names, not the default one.
- **One session per task:** a session left running by a worker that stopped is ended before its job goes on, so two no longer work in one folder.
- **Conflicting values are kept:** the session is told that a workbook's conflicting names or values are intended: it keeps them as they are and may raise them as a question.
- **Switching workspace:** a page the other workspace's model lacks no longer shows "not in this
  workspace's model"; its start opens. An address asking for that page still says so.
- **The assistant designs the load:** with AI proposals offered, a task's assistant decides how the
  workbook lives in the workspace — an update, additions, a new relation, something new but related,
  something totally new — and changes the model where the data needs it (attributes, types,
  applications, relations) in a model draft of the task's own (`draftId`). It reads cells, values,
  stored records and model-aware queries; writes data sheets of its own for rows the workbook's shape
  cannot load; and asks questions with an assumed option (`POST /ai/tasks/{id}/answers`). Every row of
  the working copy is checked in a dry run against the draft, and refused rows go back to it within
  `AI_MAX_STEPS` calls. `POST /ai/tasks/{id}/run` installs and activates the model change first (needs
  Model release), then imports into one change set and saves the profile (`result.releaseId`).
- **Words alone:** `POST /ai/tasks` without a file takes an instruction; relationships where a
  condition holds (`design.links`) are counted in the database and written as one background batch
  into the change set (`result.linksJobId`).
- `GET /ai/tasks/{id}/changes?source=` lists a design sheet's changed records; the design check shows
  them behind a button per sheet. The check counts rows skipped for an empty key (`skipped`,
  refused as `ROWS_SKIPPED` when most of a source's rows are).
- `CARDINALITY_VIOLATION` names the relation and the end that already holds one (message and
  `details`).
- Import profiles: a related record's `parent` read from a `column` may name a `valueMap`
  (`parent.valueMap`), so a language word in a translations sheet finds the language record. The
  assistant's working copy keeps the formulas' last values.
- Imports: a `record: "existing"` source finds a record by the value another source of the file
  writes into its key attribute, whatever that source is keyed by. The assistant is given every
  model-draft operation kind (such as `setAttributeTypeFeatures` to make a stored attribute a key).
- Loading the same file again with "save the import" no longer fails with `IMPORT_PROFILE_EXISTS`:
  a key holding a profile of the same model gets its next version. A profile that cannot be saved
  is a warning note on the task; the load, already committed, stands.
- A record edited in a change set (an import's update) no longer re-checks the relationships it
  already holds against their candidate criteria: as live, an existing relationship is kept
  whatever the criteria say now (D175); the dry run and the load now agree.
- A design whose dry run cannot run (the file does not fit the profile, such as a header on row 2
  under a row of group headings) no longer fails the task with "The reading failed": the problems
  go back to the assistant to fix. Each round's refused rows by code go with the design so far.
- Imports: rows repeating a key no longer conflict where one leaves a cell empty that another fills
  (the record takes the filled values); rows of two sheets keyed alike by an attribute are one new
  record instead of two that break the unique rule.
- The assistant's loaded page lists only the sheets and columns the design leaves out (no longer
  the rules' first reading as "something new, not loaded"); the shown model is read again once a
  load activated a model change; the release it installs is numbered after the newest one.
- **The assistant proposes the model first (AP6r):** a task stops at a proposal — the model in
  plain sentences per type, the engine's design checks of any workbook (stored records to reuse,
  columns that group the rows, translations left out, relationships one end cannot show) and the
  questions — before anything loads. The steward corrects it in words (`POST /ai/tasks/{id}/model`)
  or accepts it (`POST /ai/tasks/{id}/accept`); the load stage then maps the sheets and checks every
  row. The assistant may use every model-draft operation, the page kinds included.
- The assistant describes how a wide sheet (one group of columns per brand, list or period) becomes
  rows (`unpivots`) and the engine writes them into the working copy.
- The assistant's design lists each column no source of its sheet loads with the reason it gave
  (`design.leftOut`; the loaded page shows it), and is told to reuse the records the workspace
  holds, to put rows under the column that groups them, and to load every translated column
  (`workbook-design/5`).
- **The import's journey bar:** below the top bar, an assistant's load shows its steps (file and
  words, the design, the model change, questions, the check, the load, review and publish), what
  to do now and the next action, on the task's page, in the model editor opened from it and on its
  change set (`?journey=ai-task:<id>`). Close in the editor returns to the task; Stop, Start again
  and Open the change set are on the bar.

### Removed (0.16 AP6, the reading turns)

- The assistant's read, match and fix turns of AP6a and the task phases `asking`, `matching` and
  `fixing`: with the assistant offered a task is designed; without it, read by the rules and planned
  by the person as before.

### Added (0.16 AP6a, loading a workbook with the assistant)

- **Import with the assistant:** with AI proposals offered, Import opens the assistant first ("Import
  without the assistant…" opens the manual import). `POST /ai/tasks` takes a workbook and a workspace;
  a job (kind `aiTask`) reads it: a stored import profile that fits the file is followed, other tables
  are read by the rules (an update of a type when most of a column's values are its records' keys or
  names), note and title rows are set apart, and the assistant checks the reading and matches values by
  meaning. The task page shows what needs the person (new keys, names that differ, missing records), the
  rest grouped by the model; `POST /ai/tasks/{id}/plan` checks every row in a dry run, the assistant
  proposes value maps for refused values, and `POST /ai/tasks/{id}/run` loads into a change set,
  optionally saving the import profile. Visible to its requester and the workspace's administrators;
  kept `AI_TASK_RETENTION_DAYS`; at most `AI_MAX_STEPS` provider calls a job.
- A list of records the workspace does not hold yet is read as new records of its type, keyed by
  the column the assistant names (prompt `workbook-read/2`). An answer that only repeats an operation
  the engine refused ends the assistant's turns. The task keeps only the assistant's last note, and
  refusals name the sheet and the column's header.

### Removed (0.16 AP6a, the AI naming helper)

- The AI naming helper of New from a workbook and Propose again is removed ("Also ask the AI assistant
  for clearer names", the inference's `assistant` option and read fields, `phase` and `assistantOutcome`,
  the purpose `modelNames` and the proposal pattern `assistant`): the inference runs on its rules; the
  workbook assistant replaces it.

### Changed (0.16 AP1, the naming helper sees the whole file)

- The inference's AI assistant no longer sends each sheet's first 50 rows. It sends each table's
  profile, computed in the database over every row: per column the counts, value type, candidate key,
  delimiters, placeholders, overlaps with other columns and, from `samples` up, the most frequent
  values with counts (at most `AI_SAMPLE_VALUES` at `samples`); `structure` sends no value. A request
  over half of `AI_CONTEXT_TOKENS` drops the values of the columns with the most distinct values
  first. Prompt version `model-names/2`.

### Added (0.16 AP2, AI targets for unmapped values)

- **Propose targets in a mapping grid:** `POST /workspaces/{key}/mapping-proposals` (a job of kind
  `aiProposal`) asks the provider for a target for each unmapped source of a view, among the targets the
  grid would offer (all up to 100, else each source's 20 closest), and writes them into a new or open
  change set; never into live data. The job counts proposed, unmatched, changed, refused and not-answered
  sources. Needs Use AI proposals and send level `values`.
- **Provenance on change-set changes:** `origin` on `change_set_relations` and `change_set_objects`
  (migration `20261118_01`), on coverage target summaries, copied into the published relation's audit
  event and answered by record history. Coverage takes `proposed=true` in a change set; the grid's
  **Proposed** filter and the "Proposed by the AI" mark with its reason.
- **`sendLevel` on a feature's request**, a lower level than `AI_SEND_LEVEL` for that request (AP-D3).
- **`AI_CONTEXT_TOKENS`**, a small model's context window: mapping-target calls are sized to half of it.
  A source with no candidate is not sent; fields repeating the name or holding a generated identifier are
  left out of what is sent. `GET /jobs` filters by `kind=aiProposal`.

### Added (0.16 AP1, the AI proposal provider)

- **An AI provider for proposals**, set in the environment: `AI_PROVIDER` (`claude`, `openai-compatible` or a
  factory), `AI_MODEL`, `AI_API_KEY`, `AI_BASE_URL`, and how much may leave the instance, `AI_SEND_LEVEL`
  (`structure`, `samples`, `values`, default `values`) with `AI_SAMPLE_VALUES`; `AI_MIN_CONFIDENCE`,
  `AI_LOG_CONTENT`, `AI_LOG_CONTENT_DAYS`, `AI_TIMEOUT_SECONDS`. A setting that cannot work refuses the start.
  Without a provider nothing is sent anywhere.
- **Settings › Administration › AI** and `GET /ai/status`, `GET /ai/calls`, `POST /ai/test` (Operations): the
  provider, the send level, the features offered, a test request and every call with who asked, the sizes, the
  tokens and the outcome (table `ai_calls`, migration `20261117_01`). `GET /system` answers `ai`.
- **The action group Use AI proposals** (`ai-proposals`), held by the Data steward, Data owner, Model
  administrator, Workspace administrator and Integration administrator roles.
- **The inference's assistant runs on the provider:** `POST /model-drafts/{id}/inference` takes `assistant`
  (a checkbox in the dialog); its clearer names are proposals of pattern `assistant` carrying
  `evidence.origin` (`kind: ai`, model, confidence, reason), copied as `origin.proposedBy` into the step that
  applies one, and shown in the editor's "Proposed because".

### Changed (0.16 AP1)

- **`INFERENCE_ASSISTANT` and `INFERENCE_ASSISTANT_ROWS` are retired**; the start is refused while either is set,
  naming `AI_PROVIDER` or `AI_SAMPLE_VALUES`. `httpx` is now a runtime dependency (both adapters use it).

- **Every setting in both settings files:** `python -m app.cli.settings_template` writes every engine setting
  from the settings catalogue, commented out at its default with its description. `scripts/dev.sh settings` uses
  it for a new `.dev/settings.env` and, run again, adds what an existing file misses and comments out a retired
  setting; the engine part of `.env.example` is generated from it and a unit test keeps it so. `compose.yml`
  passes all of `.env` to the engine (`env_file`) instead of a hand-kept list, which had left out every setting
  but four capability groups.

- **`AI_REASONING_EFFORT`** (`openai-compatible`): sends `reasoning_effort`, so a local thinking model answers
  without reasoning for minutes. The adapter also shows the answer's shape in the instructions as an example to
  fill in, so a model on an endpoint that does not enforce the schema (Ollama's MLX builds) answers in shape.

### Fixed (0.16 AP2)

- **Mapping sources ignored the binding's criteria:** a mapping grid applied `candidates` only to targets, so
  coverage, its counts and state filters, the Proposed filter and the AI proposal job's unmapped sources
  included records that can never be mapped there. Sources are now the source-type records meeting the
  criteria at the source end, plus any that already holds a relationship of the binding (kept, D175).

### Fixed (0.16 AP1)

- **A burst of requests froze the engine:** a page asking for many lists at once (a sidebar of 101 types) left
  the requests holding database connections without a worker thread to finish on, while the rest held every
  thread waiting for a connection; everything waited for `DATABASE_POOL_TIMEOUT` and answered 503. At most as many
  requests as the pool has connections are now inside the application; the rest wait for their turn without a
  thread (503 `poolExhausted` only after `DATABASE_POOL_TIMEOUT`).
- **Handled errors were also logged as unhandled:** the catch-all handler was registered where Starlette raises the
  exception again after the answer, so every 503 or 500 also printed an "Exception in ASGI application"
  traceback. The last-line handler now answers and raises nothing further; J12.11 fails on any escaping error.
- **A slow AI provider no longer breaks the inference:** the inference held its database transaction open while
  waiting for the answer, so a model taking longer than `DATABASE_IDLE_TRANSACTION_TIMEOUT` (a local model can) had
  its connection ended. It now ends the transaction first and marks the job's phase `assistant`.
- **The editor waits for the proposals, visibly:** while the inference runs it says what it is doing ("Asking the AI
  assistant (model) for clearer names…"), pauses editing so a change cannot discard the proposals, and offers Stop;
  afterwards it says what the AI did, including "found the names good as they are". The inference read answers
  `phase` and `assistantOutcome`; `GET /system`'s `ai` names the `model`.
- **A draft profile key taken by another model's profile** was refused only at installation or loading, and the
  editor had no way to change the key. It is now an error in Issues at the profile's key, with a free key
  (`freeKey` on the draft's profile and in the refusal's details) offered as "Use '…'" there and in the Load and
  Install dialogs; the source pane shows and edits the profile's key and name.
- `tests/test_startup.py` pinned the schema head at `20261114_01`, two migrations behind 0.12.0;
  `POST /me/notifications/removal` was missing from the API journey inventory.

## [0.12.0] - 2026-10-28

Security, authentication and authorization: every caller signs in, every operation is authorized against a role, and
every change records who made it; change-set publication approvals and an inbox; mail; licensing and the
compatibility commitment ([COMPATIBILITY](docs/COMPATIBILITY.md)). Upgrading from 0.11: create the first administrator
with `python -m app.cli.create_admin` ([OPERATIONS](docs/OPERATIONS.md)); the schema-language window is 0.10 only,
and a workspace on an older release is brought up to date from its own screen or with
`python -m app.cli.model_release_raise`.

### Added (0.12 NT1, notifications: a short list and a history page)

- **The bell lists only unread notices**, at most 20 with how many more, and a notice opened from it leaves the
  list; "See all notifications" opens the new **Notifications** page (`/notifications`, also in the account menu with
  the unread count): search, Kind, Workspace, Show (all, unread, read) and Sort, rows loaded as the list scrolls,
  notices selected as records are (Cmd/Ctrl-click, Shift for a range, Select all) and marked read or unread or
  deleted from one steady bar, and Delete all read…. Settings › Notifications is renamed **Notification email**.
- **A notice opens in its own workspace's application** from the bell, also on Home and the Notifications page.
- `GET /me/notifications` gains `q`, `kind`, `workspace` and `sort`; `POST /me/notifications/read` gains `subjectId`
  and `read: false`; new `POST /me/notifications/removal` (`{ids}` or `{read: true}`). Additive.
- **The engine closes what is done:** a job's "waiting for your confirmation" notice is read once the job is
  confirmed or cancelled, and opening a job's page or dialog, a migration, a move or a change set's review marks the
  person's notices about it read, including one that arrives while it is shown.
- The 90-day delete runs in the job worker's hourly sweep instead of inside every insert (migration
  `20261116_01`).

### Fixed (0.12 NT1)

- **A second click on the bell, the account button or any other popover button closed and reopened it.** Focus
  leaving the popover closed it and the same press opened it again; that press now only closes it.

### Added (0.12 MR1, retiring and deleting model releases)

- **A model release can be retired** (`PATCH /api/v1/model-releases/{releaseId}`, Settings › Model › the release
  › Retire…): it is no longer offered or accepted where a release is chosen (`409 MODEL_RELEASE_RETIRED` for a new
  workspace, an activation, a migration or a change set elsewhere), and the workspaces and change sets on it keep
  working. It can be brought back; installing its exact model again also does. The default workspace's release is
  not retired (`409 MODEL_RELEASE_IS_DEFAULT`).
- **A release nothing refers to can be deleted** (`DELETE /api/v1/model-releases/{releaseId}`, Delete… on its
  page). Every release says `deletable` and, if not, `deleteBlockedBy` (`running`, `history`, `importProfile`,
  `mapping`); a refusal is `409 MODEL_RELEASE_IN_USE`. `python -m app.cli.model_release_prune` deletes the retired
  ones at once (`--unused` also the active ones, `--dry-run` lists).
- **Model pickers offer only what can be chosen.** `GET /model-releases` gains `status` and `usable=true` (active,
  of a schema this version reads); every picker uses it. The new-workspace picker lists each model's newest
  release, older ones behind "Show older versions"; a change set's pickers list every usable version, and its
  workspace's own release even when retired. Settings › Model lists fully retired models last, under Retired.
- Release answers gain `status`, `statusVersion`, `retiredAt`, `deletable` and `deleteBlockedBy` (additive). The
  database gains `model_releases.status`, `status_version` and `retired_at` (migration `20261115_01`).

### Fixed (0.12 R, the release review)

- **Reloading and moving on at once no longer signs you out.** A reload renews the session; when the browser navigated before it kept the new refresh cookie, the next page presented a used token and the session ended as reuse. A used refresh token presented again within 30 seconds of its use, while the token that use issued is unused, now renews from that token; an older token, a later one, or a successor already used still ends the session.
- **A DELETE could change live data under a change-set permission.** The record, relationship and
  attribute-value deletes took `changeSetId` from the body for the permission check but from the query for
  the write, so a Contributor could delete live. The check now reads it where the write does, and the write
  unit itself refuses a live write by a caller allowed only change-set work (and the reverse), `403 FORBIDDEN`.
- **A record-type narrowing was skipped** for attribute writes in a change set that already held the record.
- **A migration that publishes a change set** now needs what publishing it directly needs: Publish in the
  workspace and the workspace's approval policy (`409 APPROVAL_REQUIRED`); an open request is closed as a direct
  publication closes it. Confirming such a migration is no longer allowed to someone with only Work in change
  sets.
- **A submitted change set can no longer change underneath its request.** Moving it to another release freezes
  or withdraws the request (`409 CHANGE_SET_SUBMITTED`, or `withdrawSubmission=true`), and an approval is bound
  to the version that was submitted (`409 VERSION_CONFLICT`).
- **Withdrawing a request** follows one rule: its submitter or an approver. `DELETE …/submission` is declared by
  its own action, `change-sets.withdraw` (Work in change sets or Approve publications).
- **Adding a passkey asks for your password or a code first**, as removing one does
  (`POST /oauth/passkeys/registration/options` takes `{"proof"}`; `422 PROOF_REQUIRED`, `422 CODE_INCORRECT`,
  `429 SIGN_IN_SLOWED`). A malformed passkey answer is refused instead of answering `500`.
- **More guessing is slowed:** a wrong current password on `POST /me/password`, wrong client secrets on
  `/oauth/token` (per client and address; an unknown client costs the same), and open provider sign-ins are capped
  at 2,000 per provider.
- **An engine that started with nothing to serve** (every workspace on a schema outside the window) starts its
  background work as soon as a release is raised, without a restart.
- **A one-time link is never mailed twice** when a mail server is slow; a provider sign-in with unchanged groups
  no longer empties every process's permission cache.
- **The application:** actions stay hidden until your permissions are known; the draft's consumer API documents
  download with your sign-in; a server error while renewing the session no longer signs you out; live updates back
  off when the engine is unreachable; a change set's page follows its request after it is sent back; reload after
  a version conflict on the approval policy; no `Error:` prefix on the crash screen.
- **The development proxy** answers `502 ENGINE_UNREACHABLE` with the reason (nothing at the engine's address,
  or another program holds its port) instead of printing a TLS stack trace.

### Changed (0.12 R, Settings)

- **Settings › Account › What you can do** is a table of your workspaces: your roles, and what you may read,
  propose, change live, publish and approve. A limited permission is a count ("2 applications, 1 record type")
  that opens what it covers, application by application, with the role it comes from. Each role appears once per
  workspace; roles across the instance are listed under it. The Account and Notifications pages are wider.
- **People, groups and clients** scroll page by page; the Groups page names each group's source on the group.

### Added (0.12 UW1, a workspace that cannot be served)

- **A workspace says why it cannot be opened.** `GET /api/v1/workspaces` and `GET /api/v1/workspaces/{key}`
  carry `availability`: `available`, or `unavailable` with the reason (the schema left the window, is a later
  engine's, or the release is invalid), the release, its schema, the schemas this version reads and whether it
  can be raised.
- **`POST /api/v1/model-releases/{releaseId}/raising`** brings a release of a schema that left the window up to
  the schema this version reads, in place, for someone who may install models. `{confirm: false}` shows the
  schemas, the consumer API definitions rewritten and the workspaces that return, and changes nothing;
  `{confirm: true, expectedModelHash}` rewrites the release, records it in the audit trail, and every process
  serves the workspaces again from its next request. Refusals: `RELEASE_NOT_RAISABLE`, `RELEASE_RAISE_REFUSED`,
  `MODEL_HASH_CHANGED`. The code is shared with `python -m app.cli.model_release_raise`, which behaves as
  before. A maintenance step before 1.0, outside the compatibility commitment.
- **The interface shows it in three places with one component.** A workspace that cannot be served opens a screen
  saying why in plain words, with "Bring it up to date" (for a schema that left the window: "Review the change…"
  for someone who holds Model release at the instance, one sentence for everyone else, nothing while the
  permissions load) beside "Or continue elsewhere" (the workspaces that open and All workspaces). The review
  dialog previews, then "Raise and reopen" confirms against the preview's hash (a changed release is read
  again); afterwards "{workspace} is back." offers "Choose another model…" and "Open {workspace}". Settings ›
  Workspaces marks the workspace "Cannot be opened" in its list and shows the same notice at the top of its
  Overview.

### Changed (0.12, the Workspaces list)

- **Settings › Workspaces lists each workspace's model and release in aligned columns**, labelled once per
  group; the second line is the workspace's key. At a phone's width they stack under the name.
- **Settings › Model lists each model the same way:** its key on the second line, then Releases, Latest, Draft (the
  model's newest open draft) and Schema (the newest release's schema language) as aligned columns; a draft not yet
  installed shows "—" for the release columns. Every group has the same columns and the status column fits its pill,
  so they line up from group to group. An opened draft or release no longer repeats the page's title as its heading.

### Added (0.12 L2, the compatibility commitment)

- **[docs/COMPATIBILITY.md](docs/COMPATIBILITY.md)** (D436–D440): from 0.12.0 the management API `/api/v1`, each
  consumer API contract version, webhooks and events with the `RDM-*` headers, sign-in and tokens, the setting
  names and the documented commands change only by addition; a breaking change comes beside the old version and
  the old one is kept at least 12 months and two minor releases. Clients ignore unknown fields and values; four
  extensions are reserved (a retired record's survivor, a value's source, computed values, new value types). Before
  1.0 the schema language is the exception: each release reads the version it writes.
- **Consumer API documents describe answers as open objects** (no `additionalProperties: false`), so a client
  that validates against them accepts a field added later; requests stay closed.

### Removed (0.12 L2a, the schema-language window cleaned)

- **The window is schema 0.10 only (D439, D441).** Before 1.0 the window holds the one version a release
  writes; 0.5 to 0.9 left it. `GET /system` answers `schemaLanguages: ["0.10"]`, every refusal names
  `supportedSchemaVersions: ["0.10"]`, and `setRelease` accepts only `0.10`. Gone with them: the
  per-version feature checks, the reader of 0.8-shaped consumer API definitions, and the offline schema 0.4
  upgrade command (`python -m app.cli.model_schema_upgrade`).
- **The example model is released as `0.10.0`** in schema 0.10 (`model/rdm-starter.json`); the 0.8 copy
  of the example model is removed. A stored release of an
  older schema is raised with `python -m app.cli.model_release_raise` or from the interface (UW1).

### Changed (0.12 L2a follow-up, a bootstrap release conflict no longer stops the start)

- **Startup serves when the bootstrap model's release is stored with other content.** It logs one error (no
  traceback) and continues: for a stored release of a schema outside the window the error gives the exact
  command, otherwise it asks to raise `release.version` in the model file. Workspaces on a release outside the
  window answer `503 MODEL_REGISTRY_UNAVAILABLE`; the others are served.
- **`python -m app.cli.model_release_raise [--dry-run]`** raises stored releases of a schema older than the
  window to `0.10` in place (schema 0.8 and earlier also get `consumerApis` in the present syntax), under the
  installation lock and in one transaction. A release whose raised model is invalid, or whose hash another
  release has, is skipped and reported (exit status 1). It replaces the "start a new database" advice for
  releases of a schema that left the window.

### Added (0.12 L1, licensing and policies)

- **The licence and the source are offered by a running instance (D219, AGPL section 13).** `GET /system`
  answers `engine.license` (`AGPL-3.0-or-later`) and `engine.sourceCode`; the OpenAPI document has
  `info.license`; Settings › About shows both and the account menu ends with "Source code · licence". The new
  setting `SOURCE_CODE_URL` defaults to the project's tag of the version
  (`https://github.com/refiroo/refiroo/tree/v<version>`); an operator running a modified version sets their own.
- **Policies:** README licence section, `CONTRIBUTING.md` (no outside code until a contributor agreement
  exists), `SECURITY.md`, `TRADEMARKS.md`, `COMMERCIAL.md`, and `THIRD_PARTY_NOTICES.md`, generated by
  `scripts/third_party_notices.py` (it refuses a licence outside its allow-list). The project is named
  refiroo and its repository is `refiroo/refiroo`.

### Added (0.12 M2 follow-up, notification types)

- **Choose which notices are mailed (J46.10, D434, D435).** A new Settings › Notifications page holds the e-mail
  switch (moved from Account) and one setting for each kind of notice (a change set waiting for your approval, yours
  approved, yours sent back, a job of yours finished, failed or waiting for confirmation). Everything is on until
  switched off; a kind switched off stops the e-mail only, the inbox, notices and workspace events are unchanged.
  `GET`/`PUT /me/notification-mail` answer `kinds: [{kind, label, enabled}]` and `PUT` takes `{enabled?, kinds?}` (at
  least one; an unknown kind is `422 UNKNOWN_NOTICE_KIND`). The mail's last line now points to Settings › Notifications.
  Migration `20261113_01` (`users.notice_mail_kinds_off`); the one list of kinds is `engine/notifications/kinds.py`.

### Changed (0.12 A3a, the workspace page in tabs)

- **A workspace's page has tabs.** Settings › Workspaces › a workspace: the actions sit under the header, then
  Overview (the facts and the workspace's applications as clickable cards), Access, Approval and Activity, each shown
  only to someone who may use it (Activity needs Browse; it lists the workspace's changes, newest first, by day, from
  `GET /changes`). The tab is in the address: `/settings/workspaces/{key}/{tab}`. Visited tabs stay loaded, so
  switching keeps the page where it is; a workspace opens at once on Back (its last known state, read again
  meanwhile); reading a workspace no longer counts its records to say whether it can be deleted.
- **Workspaces and Model open on a list.** Settings › Workspaces lists the workspaces (active first, the default on
  top, then retired; search by label and key) and Settings › Model lists the models; opening one shows its page under a
  bar "← All workspaces" / "← All models" with a trail. The switcher boxes and their dialogs are gone.
- **The access list groups a principal's grants.** `GET /workspaces/{workspaceKey}/access` is ordered by principal
  (people, groups, clients; then name and id), then by grant, so one principal's grants are adjacent.

### Changed (0.12 A3c, Settings › Model in tabs)

- **The model page has tabs:** Overview, Releases, Drafts and Structure; the "Deployment capabilities" panel is gone (the
  Deployment page has it). A release or draft opens as before, under a bar "← Back to Releases" and a trail that returns
  to the tab it was opened from. The new Structure tab is a read-only list of a release's applications, object types,
  attributes and relations, with a release picker.

### Changed (0.12 A3b, Access and Activity of a workspace)

- **A consumer API is granted to a client only:** a person or a group is refused `422 CONSUMER_API_CLIENTS_ONLY`; people read through the management API. Migration `20261114_01` removes such grants made earlier.
- **Access is one line per person, group or client**, with its roles as coloured chips, a trash on hover (asking
  first), a + to add a role, search and Role/Kind filters; at 390px each is a card. The people's and clients'
  own pages keep their tables.
- **Switching workspace is smoother:** the previous workspace stays on screen, dimmed, until the next one is read (a
  row prefetches on hover); the dialog shows its last lists at once and refreshes them in place; a short tab no longer
  sends the page back to the top; dialogs fade in.
- **Activity has coloured marks:** the record type's tile, a Created/Changed/Removed pill, and one expandable line for
  the records of one change set by one person on one day.

### Added (0.12 A3, approvals in the interface)

- **Submit, decide and set the policy in the interface (J42).** The change-set bar offers "Submit for publication"
  where direct publishing is not allowed, shows "Waiting for approval" with the request and "Withdraw request"; the
  review has a Decision card ("Approve and publish", "Send back" with a required comment, the decisions so far);
  Settings › Workspaces has an Approval section for the policy; Home lists "Waiting for your approval".
- `GET|PUT …/approval-policy` also return `approverCount`, how many can approve in the workspace.

### Added (0.12 M2, inbox notices by mail)

- **E-mail for inbox notices (J46.10, D432, D433).** A person with an address switches on "Email me when something
  arrives in my inbox" on Settings › Account (`GET`/`PUT /me/notification-mail`; off by default; the switch is not
  shown where mail is not set up, the person has no address or the caller is a client). The mail sender then mails one
  plain-text message per notice that is unread, made after switching on and under 24 hours old. A message names the
  kind of event and links to the application; it holds no record, change-set, workspace or person content. Enabling is
  refused `409 MAIL_NOT_SET_UP`, `409 NO_EMAIL` and `403 NOT_A_PERSON`; switching off always works. Migration
  `20261112_01` (`users.notice_mail_since`, `notifications.mailed_at`).

### Added (0.12 A2, the inbox and workspace events)

- **An inbox for people and clients (J42.5).** `GET /me/notifications` (`unread`, cursor-paged, with `unreadCount`),
  `POST /me/notifications/read` (`ids` or `all`) and a live stream, `GET /me/notifications/events` (`unread` and
  `notification` server-sent events, woken by PostgreSQL `NOTIFY` on the job stream's listener). A submitted request
  reaches every active person or client holding Approve publications in the workspace except the submitter; an approval
  or send-back reaches the submitter; a background batch, import, export, migration or move a person started reaches
  them when it completes, fails or waits for confirmation (a trigger on `jobs`, so every path is covered). Ending a
  request marks its "waiting" notices read. Notices older than 90 days are deleted. Migration `20261111_01`.
- **Workspace events for webhooks (D428–D431).** A subscription with `source: "workspace"` delivers
  `change-set.submitted`, `change-set.approved` and `change-set.sent-back` with the same signing, retry, log, resend,
  rotation and formats as record events (CloudEvents type `rdm.change-set.approved`). Events name the people (kind, id,
  name; no e-mail) and are numbered per workspace without gaps. Subscriptions read `source`; `consumerApi` is `null`
  for this source.
- **The interface:** a bell with the unread count in the top bar opens the inbox panel; Webhooks lists a workspace-events
  subscription as "Workspace events".

### Added (0.12 A1, a publication request and its approval)

- **Submit, approve or send back (J42).** `POST /change-sets/{id}/submission` submits a validated change set for
  publication (`DELETE` withdraws it); `POST /change-sets/{id}/decisions` approves it, which publishes it in the same
  transaction bound to the reviewed version and the active publication, or sends it back with a required comment;
  `GET /workspaces/{key}/publication-requests` lists the requests with their decisions, cursor-paged. A change set's
  read gains `submission`. Each submission and each decision is a row of its own (`change_set_submissions`,
  `change_set_decisions`, migration `20261110_01`); audit events `change-set.submitted`, `.withdrawn`, `.approved` and
  `.sent-back` name the actor.
- **Approve publications (D424).** A new action group, held by the Data owner role, not narrowable.
- **A workspace's approval policy (D425).** `GET|PUT /workspaces/{key}/approval-policy`: `requireApproval` makes a
  direct publication need an approval (a holder of Publish and Approve publishes in one step and the approval is
  recorded; anyone else gets `409 APPROVAL_REQUIRED`), `secondPerson` keeps the submitter from deciding their own
  request (`403 FORBIDDEN`, `details.reason: "ownApproval"`). A change is a security event (`approval-policy`).
- **A submitted change set is frozen (D426).** Any write to it is refused `409 CHANGE_SET_SUBMITTED` unless the request
  carries `withdrawSubmission=true`, which withdraws the submission in the same transaction. The inbox and webhook
  events are A2, the interface A3.

### Fixed (0.12 E1, security review)

- **A profile's check is made in a workspace (F5, low).** `GET` and `POST /import-profiles/{key}/check`, and the
  check's `new-values`, `drift`, `missing-records` and `rows` reads, took no workspace: they picked the profile's
  newest file or check across workspaces, so a caller holding Bulk in one workspace could check, or read the check
  of, another workspace's file. They now take a required `workspaceKey` and need Bulk there (declared as "the query's
  workspace"; Bulk at the instance serves any); they read only the profile's current file and latest check in that
  workspace, "no file" or "no check" when it has none, and `422` without the parameter. The action's groups are
  unchanged; the OpenAPI lock is re-baselined for these six routes only. Settings › Import profiles reads the check in
  the workspace of the profile's latest file.

- **A profile's file is uploaded and current per workspace (C2, medium).** A Data steward holding Bulk in one workspace
  could upload a file for an import profile naming another workspace, and the upload superseded (and the retention
  sweep aged) the file that workspace's owner had made. `POST /source-files` for a profile now needs Bulk and import
  in the request's `workspaceKey` before anything is stored (`403 FORBIDDEN` naming the action, `bulk` and the
  workspace), and a profile's files are superseded and expired per profile and workspace. A model draft's files keep the documented rule (Bulk at any scope). The action's groups and the OpenAPI
  document are unchanged.

- **A deletion honours a grant narrowed to record types (C1, high).** `DELETE /objects/{type}/{id}` (with a cascade
  too), a `delete` item in a batch or import, the rows an import deletes for being missing from a file, and a delete
  in a change set skipped the narrowing check: a Data steward narrowed to one type could delete records of another.
  The one deletion path (`records/deletion.py`) now checks the distinct record types of everything it removes, cascade
  victims included, and the ends of the relationships it removes, before anything is written; a refusal is `403
  FORBIDDEN` with `details.recordTypes` as for every narrowed write, ahead of the impact or the preview, and a batch
  item is refused on its own (an atomic batch applies nothing). Journey cases in J40 for a live, cascading, batch and
  import, and change set delete; the narrowing table of J47 maps the delete route to them.
- **Unauthenticated and unauthorized calls are refused before an unknown parameter (F1, low).** On a route that needs a
  token the order is now `401`, `403`, then `422 UNKNOWN_PARAMETER`; the open routes still refuse it first.
- **A request body that is not UTF-8 is `422`, not `500` (F3).** The rejected bytes are left out of the error's
  `details`.
- **A NUL character in a name, a key or an address is `422 REQUEST_VALIDATION_ERROR`, not `503 DATABASE_UNAVAILABLE`
  (F4).** The driver refuses such a text before the database sees it; that is no database condition and no longer counts
  as an outage in the process report. A database that cannot be reached still answers `503`.
- **Behind a load balancer (`WEB_TLS=proxy`) a caller cannot choose the address the engine sees (C3, medium).**
  `web` believes `X-Forwarded-For` only from the addresses in the new `WEB_TRUSTED_PROXIES` (default empty: nobody),
  and sends the engine the one address it settled on. List the balancer's range, or every caller counts as the
  balancer. `compose.acme.yml` lists the private ranges for Caddy. A malformed entry stops `web` with a message.
  The deployment runner proves a forged address is ignored, and honoured from a listed balancer.
- **The application page cannot be framed (C5).** `Content-Security-Policy: frame-ancestors 'none'` and
  `X-Frame-Options: DENY` on every response of `web`.
- **A secret is not carried to another server or provider (C6).** Saving mail with a new host or port, or a sign-in
  provider with a new issuer, needs the password or client secret in the same request (`422 MAIL_PASSWORD_REQUIRED`;
  new `422 SIGN_IN_PROVIDER_SECRET_REQUIRED`). The issuer of a provider anyone has signed in with cannot change
  (`409 SIGN_IN_PROVIDER_IN_USE`: add a new provider).
- **Changing `SECRETS_ENCRYPTION_KEY` says what it voids (C7).** Recovery codes are keyed with the key itself;
  `reseal_secrets` (and `--check`) now print how many people hold unused ones, who must make new ones.
- **The API reference page has a content security policy (C10).** Only the engine's scripts and the page's own two
  run, nothing is evaluated, requests go only to the engine, the page cannot be framed.
- **Documentation corrected (C4, C9).** The refresh cookie's path is `/oauth`; each consumer API's OpenAPI document
  needs no token; the sign-in slowing is stated as the code does it (5 free failures per username, 20 per address, 3
  and 20 for reset asks), and that anyone knowing a username can keep it slowed.

### Added (0.12 E1, the security sweep)

- **The security model is checked against its catalogue.** Journey J47: every operation of the OpenAPI document that
  declares an action is called as a caller holding each of the nine predefined roles, as one holding nothing and with
  no token, and must be allowed or refused as `catalogue.py` says (`403 FORBIDDEN` naming the action, `401` without a
  token); the probes cannot change data. Composed cases: a Reader on every write path with the state read before and
  after, a table naming the narrowing test of every route a grant can narrow, expired, altered, `alg: none` and HS256
  tokens that run nothing, a rotated client secret, and the reset-by-mail ask (a provider-only person, slowing per
  address, no password, code or record in any message). A unit probe shows authorization runs before body
  validation for one operation of each scope kind. No feature changed.
- **The sweep reaches what the first pass left out.** J47.6 calls every consumer route each API's own OpenAPI document
  declares, and the index, as a client granted that API, one granted another, one granted it in another workspace, one
  holding only Reader (with a `consumer` and a `management` token), one holding nothing and with no token, and reads the
  answers against API.md and J41 (`403` naming the API and workspace, `401 audience`, the index filtered, the documents
  open). J47.7 classifies every route outside the OpenAPI document (open by design, needs a session, needs the
  operations role) and sends each nothing, a well-formed body with no credentials, a foreign origin and junk (not JSON,
  wrong types, 70,000-character values, a cut-off deep document, forms, meaningless cookies, redirect and traversal
  tries): never `5xx`, never a traceback, no person, session, grant, link, code or message changed. J47.8 makes a
  person (a real sign-in) holding each of five roles and requires every answer to equal a client's with the same role.
  J47.9: a reset by mail keeps the second factor; the new password alone gets the code step and no session. Two defects
  found are recorded as strict expected failures (F3: a body that is not UTF-8 is `500`; F4: a NUL byte in an address is
  `503 DATABASE_UNAVAILABLE`), fixed below; the sweep itself changed no engine code.

### Added (0.12 E1 prep, a real sign-in provider try)

- **A runner that signs in against a real provider.** `npm run test:browser:real-provider` (heavy, Docker, run before E1
  and at R) starts a pinned Keycloak with the realm in `backend/tests/keycloak/refiroo-realm.json` and walks ten sign-in
  cases on two models: register, first sign-in, groups, a wrong password, groups changed at the provider, signing out of
  the provider, local sign-in off and a rotated key.

### Fixed (0.12 E1 prep, provider sign-in callback)

- **Signing in through a real provider works.** Providers such as Keycloak return the browser with parameters of their
  own (`session_state`, `iss`); the callback refused them as unknown (`422 UNKNOWN_PARAMETER`) and no session started.
  `GET /oauth/providers/{key}/callback` now ignores extra parameters, and an `iss` it is given (RFC 9207) must equal
  the provider's configured issuer, else the sign-in is refused like any other unconfirmed answer (a `sign-in` `failed`
  event with reason `issuer`). Other routes still refuse unknown parameters.

### Added (0.12 M1)

- **A waiting message can be stopped.** Settings › Mail › Messages shows Stop sending on a message still being
  retried; after a confirmation it fails at once ("Stopped by an administrator") and is not tried again.
  `POST /mail-outbox/{id}/stop`; `409 MESSAGE_NOT_WAITING`, `409 MESSAGE_BEING_SENT`. The list also loads and
  empties as the Jobs and deliveries lists do.

### Fixed (0.12 M1, I6)

- **Every message names the product the same way.** A reset asked for on the sign-in screen said "RDM Engine"
  (the model's product name) while one mailed from People said "refiroo" (a constant), and the test message
  used the constant. `templates.product` is now the one place: the model's own name, or refiroo where the
  model keeps a default name; callers no longer pass a name. The list of default names moved to
  `common/brand.py`, used by the sign-in pages too.

### Added (0.12 I6)

- **A forgotten password is asked for on the sign-in screen.** Where mail is set up and local sign-in is
  on, the screen links to `/reset-password`: the person types a username or e-mail address and is told
  the same whoever they name. A link to the application's reset page is mailed only to an active person
  with a local password and an address; asking is slowed per name and per address (3 free asks, then
  doubling to 15 minutes) whatever the name matches. The link names the person, works once, is replaced
  by a newer one, and sets a password under the engine's rules; the person's sessions end. New JSON
  routes beside I5's (`POST /oauth/sign-in/reset-request`, `GET`/`POST /oauth/sign-in/reset`), not in the
  OpenAPI document; `options` gains `reset`.
- Links an administrator makes and links in mail now open the application's reset page (the Mail page's
  application address, else the first `CORS_ORIGINS` entry); with neither known they open the engine's
  `/oauth/password`, which still works for links made before.

### Added (0.12 SP3)

- **A new person's link is mailed.** `POST /users/{id}/password-reset` takes `send: true`: with mail set
  up and an address on the person, the one-time link is queued as a message in the transaction that
  makes it (a welcome for a person with no password, a new-password message for one with a password) and
  the answer names `sentTo`, still holding the link once. `409 MAIL_NOT_SET_UP` and `409 NO_EMAIL` are
  answered before the earlier link is replaced. The password-link dialog on People
  (one button, as before) offers "Mail it to <address>" beside "I have copied it" when mail is set up and
  the person has an address (a newer link is made and mailed, and shown in place of the first); otherwise it shows the link to
  pass on as before.

### Added (0.12 M1)

- **The engine can send mail.** Settings › Integration › Mail (`GET`/`PUT`/`DELETE /mail-settings`)
  holds the organisation's SMTP server: host, port, TLS, STARTTLS or none, an optional login whose
  password is sealed with `SECRETS_ENCRYPTION_KEY` and never answered, the from address and the
  address links point to. A login is refused over an unencrypted connection, and the server's
  certificate is verified. `POST /mail-settings/test` sends a test message at once and, when it cannot,
  answers `422 MAIL_SEND_FAILED` naming what failed (`connection`, `tls`, `login`, `recipient`,
  `sender`, `rejected`). Every change to the settings is a security event (`mail-settings`).
- **Mail is sent in the background.** Messages wait in an outbox (`mail_outbox`, migration
  `20261109_01`) and a thread in each process sends them, trying again after 30 seconds and then twice as
  long up to an hour, failing an address the server refuses for good at once and anything else after 24
  hours. `GET /mail-outbox` lists them with the reason of a failure; a message's text, which holds a
  one-time link, is sealed while it waits and erased when it is finished. `mailSender` is among a
  process's threads. Plain-text templates exist for the activation link, the reset link and the test.
  Nothing queues a link yet: SP3, I6 and M2 do. `reseal_secrets` covers the password and queued text.

### Added (0.12 I5)

- **The application signs people in on a screen of its own.** The sign-in screen is part of the
  application, so it follows the saved light or dark theme, carries the refiroo mark and a line about
  what refiroo is for, and covers every way in: a passkey, a password, a sign-in provider's button,
  the authenticator app's code or a recovery code, the set-up when a second factor is required (with
  the recovery codes shown once), and the administrators' link when local sign-in is off. It asks the
  engine through new JSON routes, `GET /oauth/sign-in/options`, `POST /oauth/sign-in/password` and
  `POST /oauth/sign-in/second-factor`; the passkey ceremonies are the existing ones. The token flow is
  unchanged (code flow with PKCE, `/oauth/token`, the refresh cookie).
- **Every sign-in rule is in one place.** The checks of an authorization request, of a password and
  of a second step moved out of the routes into `engine/identity/browser_sign_in.py`; the engine's own
  HTML pages (`/oauth/authorize`, kept for outside web clients, now with the welcome words too) and the
  new JSON routes only read their input and present the outcome. A post from one of the application's
  own origins (`CORS_ORIGINS`) is accepted by both kinds of route and the passkey ceremonies; one from
  another site is refused. A failed provider sign-in's **Try again** returns to the application.

### Added (0.12 C1)

- **The API reference's "try it" console is signed in.** `/docs` asks the engine, with the session's
  cookie, for the token of the person signed in at the browser (`POST /oauth/console-token`, answered
  `{access_token, expires_in}`, `401 not_signed_in` without a session, `403` from another site) and
  gives it to the console for the management API and the consumer APIs, so a request is answered or
  refused as the application would answer it. The cookie is read without renewing it, so the
  application's own tabs keep their session; the console renews its token in the token's last minute.
  A client's token pasted over it is sent as it is. The page itself stays open and holds no token.

### Added (0.12 K1)

- **A webhook's signing key can be rotated.** `POST /api/v1/consumer-subscriptions/{id}/rotate-secret`
  `{expectedVersion, overlapHours}` (24 by default, 0 to 168) answers a new key once, as the create
  does. For the overlap every delivery is signed with both keys, `RDM-Signature:
  sha256=<new>,sha256=<previous>`, and a receiver accepts it when either verifies; afterwards only the
  new key signs, and with 0 the old key stops with the next delivery, a retry of a waiting batch
  included. A subscription names `previousSigningKeyExpiresAt` while an overlap runs. **Receivers must
  accept a comma-separated list.** Settings › Integration › Webhooks has **Rotate key…**, with the
  overlap choices of a client's secret (one shared dialog now), and shows the new key once.
- **`python -m app.cli.reseal_secrets`** re-seals every sealed secret (token signing keys, webhook keys,
  a provider's client secret, authenticator secrets and the provider ID tokens kept with a session)
  under a new `SECRETS_ENCRYPTION_KEY`, all or none; `--check` proves every one opens. Migration
  `20261108_01`.

### Changed (grant dialog)

- **Grants are made in bulk, from a grid.** The grant dialog (a client's, person's or group's page,
  and a workspace's Access) now takes several things at once. Consumer APIs are ticked in a grid of
  APIs by workspaces (a row or column heading ticks the line, Shift extends a range; a workspace
  whose model does not declare an API has no tick for it); roles are ticked as cards, in several
  workspaces or the whole instance. What the holder already has is shown ticked and locked and is
  not sent again; a sentence says how many grants will be made. Each tick is one `POST
  /api/v1/grants`, so a refusal leaves the others made and its tick in place with the reason.
  Narrowing is offered when one role is granted in one workspace. A client's page opens on
  Consumer APIs.

### Fixed (development)

- **The API reference can call the engine in development.** `scripts/dev.sh engine` allows the
  engine's own addresses (`localhost:8000`, `127.0.0.1:8000`; with `--network` also its https address)
  in `CORS_ORIGINS`, so Scalar's `Try it` and token request are not refused as `400 Disallowed CORS
  origin`. A `CORS_ORIGINS` already in the environment is kept.

### Fixed (0.12 D412)

- **The API reference shows the consumer APIs.** A consumer API's `openapi.json` needs no token, like
  the management API's, so `/docs` and the link on Settings › API reference load it instead of
  answering `401`. The consumer index and the data routes still need a token.

### Changed (branding)

- **The application is named refiroo.** The interface shows the refiroo mark in the top bar, the
  loading and empty screens, Home and Settings › About, with the title and favicon in the browser;
  the sign-in pages and the API reference at `/docs` (and the OpenAPI title) carry the same name and
  mark, served from `/brand/<file>`. The logos are in `logos/`, renamed by what they are; the
  interface and the engine keep resized copies. Naming rules and files: `docs/BRANDING.md`.

### Fixed (0.12 I4 review)

- **Removing a passkey asks for the password again** (or a code from the app or a recovery code):
  `DELETE /me/passkeys/{id}` takes `proof`, so a stolen session cannot strip a person's passkeys.
- **Recovery codes are stored keyed** (HMAC-SHA-256 under `SECRETS_ENCRYPTION_KEY`), not as plain
  SHA-256 of 60-bit codes. Recovery codes made before this stop working: make new ones.
- **A second factor and passkeys need a password:** `409 PASSWORD_REQUIRED` for a person who signs
  in with a provider (a passkey would have been a way in past the provider).
- **Linking** locks both people in one order (no deadlock between opposite links) and refuses a
  deactivated person as the target (`409 LINK_TARGET_DEACTIVATED`).
- **Open passkey sign-ins are capped** (2000 waiting at once, then `429` with `Retry-After`), so the
  open options endpoint cannot fill the database.

### Added (0.12 DP3, the deployment guide and its check)

- OPERATIONS § **Deploying**: the topology, the steps in the order an operator needs them (address,
  `.env`, HTTPS in three ways, start, first administrator, provider, mail), what is public and what is
  kept inside, upgrading and backups; "From a phone on the same network" for development.
- `WEB_CERTS_DIR` names the folder of the certificate and key (default `./certs`).
- `npm run test:deployment` builds the images and starts the installation from empty at the computer's
  network address, signs in from a desktop and a phone-sized browser, restarts, checks that `web`
  refuses to start without a certificate and that `WEB_TLS=proxy` serves plain HTTP, then removes
  everything it made.

### Added (0.12 DP4, automatic HTTPS for a public installation)

- `compose.acme.yml` and `caddy/Caddyfile`: Caddy in front of `web` obtains and renews a Let's Encrypt
  or ZeroSSL certificate for `PUBLIC_URL` with no certificate files; `web` runs as `WEB_TLS=proxy`
  and is no longer published. Started with `docker compose -f compose.yml -f compose.acme.yml up -d`.

### Added (0.12 DP2, images and a reference installation)

- `compose.yml` is the reference installation (database, engine, web), read from an `.env` filled from
  `.env.example`: `PUBLIC_URL`, the database password, `SECRETS_ENCRYPTION_KEY` and
  `RDM_CURSOR_SIGNING_KEY` are required and never in an image. It replaces `docker-compose.yml`, which
  no longer started the engine.
- The **web image** (`frontend/Dockerfile`): the application built once, served by unprivileged nginx
  with the engine's paths forwarded, HTTPS from the organisation's certificate files and plain HTTP
  redirected to `PUBLIC_URL` (or `WEB_TLS=proxy` behind a load balancer), HSTS, `/metrics` kept inside.
- The **engine image** runs as an unprivileged user behind the proxy (`--proxy-headers`), with a health
  check and export files in a volume. A `.dockerignore` sends only what the images copy.

### Changed (0.12 DP1, one address for the application and the engine)

- The application calls the engine on the address the page was opened at (D404); `VITE_API_URL`
  still names an engine on another address. The Vite dev server forwards `/api`, `/oauth`,
  `/.well-known`, `/docs`, `/openapi.json` and `/health` to the engine (`ENGINE_URL`), so a phone on
  the network needs only the frontend's address. `PUBLIC_URL` is that address: `scripts/dev.sh engine`
  sets it, and trusts the forwarded caller address from this computer.
- Browser runner `test:browser:one-address`: signing in, a reload and signing out through the page's
  address with no request to the engine's own port, on two models and at 390px.

### Added (0.12 DP1a, a developer instance on the network)

- `scripts/dev.sh` runs a developer instance in two terminals: `settings` (the database and a secrets
  key in a git-ignored `.dev/settings.env`), `admin` (the first administrator), `engine`, `frontend`;
  with `--network` both over https on this computer's network address, after `cert` finds the
  address and makes an mkcert certificate, so a phone or another computer on the network signs in.
- README's setup uses it, and OPERATIONS § A developer instance explains each step and the settings.

### Changed (0.12 SP1b, a group's members)

- **Add members** on a group's page adds several people at once: searched and ticked (people already
  in the group or deactivated shown but not tickable), or pasted as a list of usernames and e-mail
  addresses that is checked first, each line saying whom it names or that nobody has it; the people
  to add gather as chips and are added together (D401).
- Members are ticked and **removed together**; the last Security administrator is still kept (D402).
- `POST /groups/{id}/members/batch` (with `dryRun`) and `POST /groups/{id}/members/removal`.

### Changed (0.12 RA1, a person's recent activity)

- **Recent activity** on a person's or client's page reads like a record's history: a heading for
  each day, one line each, filtered by kind (**Signing in**, **Roles and groups**, **Account**), the
  10 newest first, **Load more** adds 20, **Show fewer** returns to 10. The kinds use the API's
  existing `aggregateType` filter.

### Changed (0.12 RH1, a record's history)

- A record's **History** lists its changes under a heading for each day, one line each (what, who,
  when); a line opens to show each value with the one before (D389, D16 revised for history only),
  or says the one before was not recorded after a publish or a type change (D390).
- Filters by kind (values, relationships, moves) and by who made the changes; the 10 newest first,
  **Load older history** adds 20, **Show fewer** returns to 10 (D391, D393). A relationship's line
  names the record at its other end (D392).
- `GET /objects/{type}/{id}/history` takes `kind` and `actorId` and answers `kind`, `values` and
  `related` on each entry. The change feed and consumer events still name changes only.

### Added (0.12 I4c, passkeys)

- **Passkeys** (D389–D394): Settings › Account › **Passkeys** adds one on the engine's own page,
  where the browser asks for a fingerprint, face, device PIN or security key; it signs the person in
  alone from the sign-in page's **Sign in with a passkey**, or after a password as the second step,
  and meets the requirement for a second factor. Rename and remove them; an administrator removes
  one from a person's page. A passkey belongs to the host of `PUBLIC_URL`: changing it invalidates
  them.
- The sign-in page runs one script of the engine's own, `/oauth/passkey.js`, only where a passkey is
  offered, and none elsewhere (`script-src 'self'`; D275 revised, D390).
- `GET|PATCH|DELETE /me/passkeys`, `GET|DELETE /users/{id}/passkeys`, `passkeys` on a person and on
  `/me/second-factor`. Migration `20261107_01`; one new dependency, `webauthn`.

### Fixed (0.12 I4c)

- A sign-in provider's key cannot be `password` or `passkey`, nor `local`: a session's
  `signedInWith` is one of those or a provider's key.

### Added (0.12 I4b, a second factor for local accounts)

- **An authenticator app** (D383–D388, D225 revised): Settings › Account › **Second factor** sets one
  up with a QR code the engine draws, the key and a code, and shows ten recovery codes, once. After
  the password the sign-in page asks for the app's code, or a recovery code; each works once, and a
  wrong one is slowed like a wrong password. **New recovery codes…** and **Remove…** ask for a code.
- **Require a second factor with a password** (Settings › Security › Sign-in › Local accounts): a
  person without an app sets one up on the sign-in page, and sees the recovery codes, before their
  session starts; nobody removes their own factor meanwhile. Provider sign-ins are never asked.
- A Security administrator removes a person's second factor from their page (a security event).
- `GET|POST /me/second-factor`, `POST /me/second-factor/confirmation`, `POST
  /me/second-factor/recovery-codes`, `DELETE /me/second-factor`, `DELETE /users/{id}/second-factor`,
  `secondFactor` on a person, `secondFactorRequired` on local sign-in. Migration `20261106_01`; one new
  dependency, `segno` (the QR code).

### Fixed (0.12 I4b)

- The browser runner's provider helper passed its secret as a separate argument, which failed when the
  random secret began with `-`.

### Added (0.12 I4a, a provider identity linked, signing out of the provider)

- **Link to an existing person…** on the person a provider sign-in made (D377, D378): their
  identity and provider groups move onto the person who already had the account, with their roles
  and history; the new person is deactivated. Refused for a person with a password, roles of their
  own or local groups. **Unlink…** undoes it. `POST /users/{id}/identities`,
  `DELETE /users/{id}/identities/{provider}`.
- **Sign people out of *name* too** (D379, D380): a provider's setting, off by default, with the
  second address to register (`signedOutUri`). The app signs out by opening `GET /oauth/sign-out`;
  the browser goes through the provider's sign-out with the ID token the session kept, sealed, and
  back to the sign-in page. Migration `20261105_01`.
- **Keeps local sign-in** is a switch on a person's page (D381); while local sign-in is off, the last
  person who keeps it can neither lose it nor be deactivated (`409 LAST_LOCAL_ADMINISTRATOR`).

### Added (0.12 I3, a sign-in provider)

- **Sign in with the organisation's provider** (D361–D370): an OpenID Connect provider (Entra ID,
  Google, Keycloak and others) added on **Settings › Security › Sign-in** with its issuer, client ID,
  secret and groups claim, checked when saved, with the address to register shown to copy; the
  sign-in page offers **Continue with *name***. A person signing in through it the first time is
  created from the provider's name and e-mail and found by the provider's subject afterwards, never
  by e-mail; sessions record the provider.
- **Provider groups**: the provider's groups become groups listed under it, their members set at
  each sign-in ("Members seen"), renamed and granted like any group, and made ahead of anyone's
  sign-in with **New group › From a sign-in provider**.
- **Local sign-in can be turned off** once a provider has signed someone in; the administrators
  made on the server with `create_admin` keep a password as the way back, through a link on the
  sign-in page. A person's page says how they sign in; Account names the provider.
- API: `GET|POST /sign-in-providers`, `GET|PATCH|DELETE /sign-in-providers/{key}`,
  `GET|PATCH /sign-in-providers/local`; a group's `source` and `POST /groups` with one; a member's
  `seenAt`; a person's `identities` and `localKept`; `signInProvider` on `/me`; the security events'
  `sign-in-provider` aggregate. Migration `20261104_01_sign_in_providers`; people made before 0.12 Z4
  keep local sign-in.

### Fixed (0.12 I3)

- A group's page kept its old name after Rename until it was opened again.
- Two fields side by side in a dialog no longer push one input down when only the other has help
  text.

### Changed (0.12 HM1a, Home)

- A workspace card's tile (its initials) opens the workspace, as its name does.
- **Continue where you left off** stands on a shade of its own, in light and dark.

### Changed (0.12 LS1, a collection's rows scroll on their own)

- A collection's table page fits the window (D371): only its rows scroll; the top bar, the band,
  the header and the toolbar stay, and the table's footer and the rail end on the window's bottom
  line, also with few records and on a phone.
- The wheel over a list that fills its page is the browser's alone (D372); a list nested in a page
  that scrolls (a record's panels, dialogs) keeps carrying the wheel on at its ends, finding the
  scroller around it once per gesture.
- A record list's rows keep to one line once its columns are laid out (D375); a cut value is shown
  whole on hover, focus or a long press.

### Fixed (0.12 LS1)

- Scrolling a collection lagged even with a few hundred records. Rows passing under the pointer
  measured their cells and drew the whole table again, twice, for every cut-off value; every page
  arriving in the background and every draw of the page drew every row again; the wheel waited
  for a script that read the layout at each step; and every scroll frame laid the table out again.
  Now a row on the page is drawn once (D373), and the layout is read only when the list or its size
  changes (D374).

### Added (0.12 SP2, clients and their access)

- **Settings › Security › Clients** (D348–D357): the systems that call the API, each with its
  consumer APIs and roles and when it last obtained a token; a new client's ID and secret shown
  once; a client's page with who created it, Rename, Deactivate and Restore, **Rotate secret**
  keeping the current secret working for 1 hour, 24 hours or 7 days, or stopping it at once,
  secrets told apart by their last four characters and the previous one ended early, its access,
  the webhooks it created, its recent activity and its changes.
- The grant dialog grants **a consumer API** as well as a role, from a client, a person, a group or
  a workspace's Access; its button reads **Grant**.
- **Settings › Security › Signing keys**: the token signing keys and their state; start a new key,
  or retire the current one at once after a leak.
- A webhook's page names who created it.
- `roles`, `consumerApis` and `createdBy` on every read of a client, `hint` (the last four
  characters) on each of its secrets (migration `20261103_01`), and
  `GET /api/v1/workspaces/{workspaceKey}/grant-options`.

### Fixed (0.12 SP2)

- A person holding only Security administrator could not narrow a grant: the grant dialog read the
  workspace's model, which needs Browse; it now reads `grant-options`.
- A segmented choice in the grant dialog was drawn taller than its options (the dialog's label rule
  reached its labels).

### Added (0.12 TV1, a record's parent in its list)

- A table view's **Columns…** and **Filters…** in the model editor's layout editor offer the
  record's relationships, the ones to its parent first (D358–D360): a list of records under a parent
  can show which parent each belongs to and be filtered by it. The engine has listed and filtered
  by relationships since 0.9; only the model file could choose them until now.

### Added (0.12 Z6, one person's changes across workspaces)

- **Changes** (D340–D347): everything a person or client changed, across the workspaces the reader
  may browse, newest first and grouped by day: records and relationships, live or in a change set,
  change sets, publications and model drafts and releases, each naming its workspace, change set and
  what it changed with its type from that workspace's own model, narrowed by workspace, kind and
  period; each title opens what it changed while it exists. A name in a record's history opens it,
  as does "See changes" on a person's page; Home shows **Your recent changes**, the five latest.
- `GET /api/v1/changes` (`actorId`, `workspaceKey`, `kind`, `since`, `until`, paged), filtered to
  what the caller may see; a Security administrator without data roles reads an empty list.
- Every audit entry that belongs to a workspace now names it, also a change set's work, and a change
  set's records and relationships name what they changed; the upgrade places existing entries from
  their change sets (migration `20261102_01`).

### Added (0.12 HM1, a home page after sign-in)

- **Home** (D331–D339): signing in, the bare address and the product name open a home page: a
  greeting with the person's roles and what is open; Continue where you left off, back to the last
  list, record or review opened in this browser; the workspaces they may browse as cards, the
  default first, each with its model, their role, its applications and buttons counting their open
  change sets and, for a publisher, every open change set; their open change sets across workspaces,
  each opening its review. A workspace's name opens the workspace. An address naming a workspace,
  application or record opens it as before.
- `GET /api/v1/me/workspaces` and `GET /api/v1/me/change-sets` (D332, D333); `product` on
  `GET /api/v1/system` (D338).

### Fixed (0.12 HM1)

- A person with no workspace saw the model release's name in the top bar; it is the instance's
  product name, as everyone else sees.
- A browser runner's seed built on an older schema seed was reused after the schema seed was rebuilt,
  so its backend refused the harness client (`401 invalid_client`); such a seed is rebuilt now.

### Added (0.12 Z5, the interface follows permissions)

- **The interface offers only what a person may do** (D321–D330): a Reader sees no way to change
  anything and the data-context band says they can read; a Contributor proposes a change from a
  record into a change set of their own (named the first time, continued afterwards, counted in the
  band) and is not offered Publish; a narrowed writer edits only the permitted record types, named in
  the band; imports, bulk changes, moves, publishing, withdrawals, migrations and Settings' pages
  appear only to whoever holds their groups, and a flow appears only when every step can finish.
- **The first workspace** is the default one the person may read, otherwise the first they may
  read; with none, a page says so with their roles and leads to Settings (People for a Security
  administrator). The workspace selector lists only workspaces the person may read.
- `GET /api/v1/me/action-groups`, `holding=` on `GET /api/v1/workspaces` and `createdBy=` on a
  workspace's change sets (D325, D327, D328).

### Fixed (0.12 Z5)

- The `change-sets` and `test:browser` (navigation) browser runners start again: they ran their own
  servers without the secrets key and token every engine needs since I1, and now use the shared
  harness. `test:browser:wp12` accepts the activation's sentence naming who made it (0.12 Z4).

### Added (0.12 Z4, audit identity)

- **Every change names who made it** (D313): `actor` beside `cause` on a record's history, a feed
  entry and a release's activation: the person or client by their current name, `{"kind":
  "engine"}` for the engine's own changes, `null` for changes from before 0.12 ("Before sign-in").
  A job's changes name its requester, a publish's the publisher. Consumer events name no one (D314).
- `createdBy` on a change set, `publishedBy` and `withdrawnBy` on a publication, `requestedBy` on a
  job (D315).
- **Security events** (D317, D318): `GET /api/v1/security-events` (`principalId=`,
  `aggregateType=`) lists changes to people, groups, roles, grants, clients and signing keys, and
  sign-ins, succeeded or failed, with who made them and never a secret.
- In the interface: "by *name*" in a record's history and the model editor's history, "Created by"
  on a change set, "Published by" and "Withdrawn by" on a publication, "Requested by" on a job and
  in the Jobs list, and a person's **Recent activity** in Settings › Security › People (D319, D320).

### Changed (0.12 Z4)

- `author` on a model draft's and a model mapping's operations is now `{kind, id, name}` (or
  `null`) instead of a string, which was never filled.
- A subscription's `owner` uses the shared `PrincipalResponse` schema (same fields).

### Added (0.12 Z3, consumer APIs per client)

- **Consumer API grants** (D306): `POST /api/v1/grants` with `consumerApi` instead of `role` lets a
  client, person or group read that consumer API in one workspace; a grant reads `role: null` and
  `consumerApi` (`stale: true` once the model drops the API); `GET /api/v1/grants` takes
  `consumerApi=`. A workspace's Access and the Account page show it as "Consumer API: *name*".
- Each consumer API's OpenAPI document declares the OAuth 2.0 client credentials scheme with the
  token URL and scope `consumer`, and `401` and `403` on every operation (D311).
- A subscription reads `owner`, the person or client that created it, and the list takes `ownerId=`
  (D310).

### Changed (0.12 Z3)

- **The consumer data routes need a grant of the API in the workspace read** (D307): `403 FORBIDDEN`
  with `details: {consumerApi, workspaceKey}`, checked after the workspace and before the definition,
  so an unknown API key now answers `403` to a caller without a grant (D309). No role opens them.
  After upgrading, consumer clients read nothing until granted.
- The consumer index lists only the APIs granted to a `consumer` token; with a `management` token
  the index and the OpenAPI documents need Browse in the workspace (D308).

### Added (0.12 SP1, the Security pages)

- Settings › Security › **People**, **Groups** and **Roles**, shown to people holding Security
  administration (D303): people listed with the roles they hold, searched, active or deactivated; a
  person's page to edit them, make a one-time password link shown once (D304), sign them out
  everywhere, deactivate or restore them, and see their roles, directly or through a group, and
  their groups; groups with their roles and members; the matrix of roles by action group, a custom
  role made empty or copied and edited in place (D305 at phone width).
- A workspace's **Access** on its page in Settings › Workspaces: every grant that applies there,
  made in it or for the whole instance (D301). One grant dialog for Access, a person and a group,
  with the narrowing to applications and record types and a sentence of what the grant allows.
- `GET /api/v1/users` and `GET /api/v1/users/{id}` answer the person's `roles` and where (D298);
  `GET /api/v1/users/{id}/grants` lists a person's grants including their groups' (D299); `q` and
  `memberId` on `GET /api/v1/groups`, `q` on `GET /api/v1/clients` (D300).

### Changed (0.12 SP1)

- `POST /api/v1/grants` refuses a workspace grant of a role whose action groups are all held only
  at the instance, such as Security administrator, with `422 GRANT_SCOPE_INVALID` (D302): such a
  grant was stored and allowed nothing.
- Webhooks' "keep the signing key" dialog is the shared "shown once" dialog the password link uses.

### Fixed (0.12 SP1, after delivery)

- New person said only "Request validation failed" for a username with a space: it now says a
  username has no spaces as it is typed, and the engine's refusal of a field is shown under that
  field (New person, Edit) or by the field's name (groups, roles).

### Added (0.12 Z2, record types at the write unit, jobs as their requester)

- A grant narrowed to applications and record types now limits every write its holder makes in the
  workspace (D289–D291): a record may be written when its application or its type is named, grants
  holding the group there add up, and a relationship may be written when either end may. Live
  writes, change sets, restructurings (both the old and the new type), batches, imports, publishing
  a change set and moves into a workspace are checked at the write unit; a refusal is `403
  FORBIDDEN` with `details.recordTypes`. A batch, an import or a move refuses only the items of
  other types; a single write and a publication are refused whole (D293).
- Jobs run with their requester's permissions (D236, D294): checked at confirmation and before
  every worker step; a requester deactivated or without the job's group fails it with `403
  FORBIDDEN` and `details.requestedBy`. The requester reads, follows, cancels and confirms their own
  job and sees it in `GET /api/v1/jobs`.
- An import profile's source files are read, changed and listed for their uploader and for holders
  of Bulk and import in their workspace, `403` for anyone else (D295).
- A grant naming what the workspace's model no longer has reads `stale: true` with
  `scope.missingApplications` and `scope.missingRecordTypes`, and `/me/permissions` marks the group
  `stale`; such names allow nothing (D296). Migration `20261030_01` (`jobs.requested_by_*`,
  `source_files.uploaded_by_*`).

### Changed (0.12 Z2)

- Publish and Copy and move are narrowable action groups (D290).
- `POST /api/v1/moves` with `mode: move` also needs Work in change sets in the source, which it
  writes a change set of; `mode: copy` needs Browse there as before (D297).
- A write the engine cannot attribute to a request or a job is refused with `500 WRITER_UNKNOWN`
  (D292).

### Fixed (0.12 Z2, found in Z1)

- An import naming a stored source file, sent as a URL-encoded form without a file part, failed
  with an internal error: the route check read its body as JSON after the form was read.

### Added (0.12 Z1, roles, groups and grants at the route)

- Authorization (ADR-044): every management operation declares its action, published in the
  OpenAPI document (`x-action`, `x-action-groups`, `x-action-scope`), and a request its caller's
  roles do not allow answers `403 FORBIDDEN` naming the action, the action groups that would allow
  it and the workspace. Record writes check Edit live, or Work in change sets with `changeSetId`.
- Roles made of 13 action groups: nine predefined, read-only roles (Reader, Contributor, Data
  steward, Data owner, Model, Workspace and Integration administrator, Operator, Security
  administrator) and custom roles (`/api/v1/roles`, `GET /api/v1/action-groups`); local groups of
  people (`/api/v1/groups`); grants of a role to a person, client or group at the instance or in a
  workspace, optionally narrowing writes to applications and record types of its model
  (`/api/v1/grants`); who can do what in a workspace (`GET /api/v1/workspaces/{key}/access`); the
  caller's own (`GET /api/v1/me/permissions`, `GET /api/v1/me/grants`). Removing the last active
  Security administrator is refused. Migration `20261029_01`.
- Settings › Account lists the person's roles, where each applies, what it narrows and the group it
  comes through; the account menu names the roles held in the workspace open, and its Account and
  All settings are buttons like Sign out.
- `create_client --role <key>` grants roles to a new client at the instance.

### Changed (0.12 Z1)

- **A principal may do only what its roles allow.** `create_admin` gives the first administrator
  Security administrator, Data owner, Model, Workspace and Integration administrator and Operator at
  the instance; the upgrade gives the same to every person and client that existed before it; new
  people and clients hold nothing until granted. `/metrics` and `/api/v1/system/*` but `GET /system`
  need the Operator role.
- The workspace list, the workspace models, the jobs and the consumer subscriptions list only what
  the caller holds a role for; a named workspace the caller holds nothing in answers `403`.
- Permissions follow a generation number PostgreSQL raises on every change to roles, groups,
  memberships, grants or a principal's `active`, so a change applies on the next request in every
  process.

### Added (0.12 I2, signing in from the browser)

- The engine's sign-in page (`/oauth/authorize`): the browser signs a person in with the
  authorization code flow and PKCE and returns to the page asked for; the access token stays in
  memory and the session in an `HttpOnly`, `SameSite=Strict` cookie that renews it unseen, each
  refresh token used once (a reused one ends the session). Sessions end after `SESSION_IDLE_HOURS`
  (12) idle or `SESSION_DAYS` (14). `POST /oauth/revoke` signs out. Failed sign-ins are slowed per
  account and address, never locked. Migration `20261028_01`.
- The account menu names the person and offers Account, All settings, the theme and Sign out;
  **Settings › Account** shows the person, changes the password and lists where they are signed in,
  with sign out per browser or everywhere (`/api/v1/me/sessions`, `/api/v1/me/password`).
- `POST /api/v1/users/{id}/password-reset`: a one-time link (valid `PASSWORD_RESET_HOURS`, 24) to the
  engine's page that sets the person's password; `DELETE /api/v1/users/{id}/sessions` signs a person
  out everywhere. Deactivating a person ends their sessions.
- `PASSWORD_MIN_LENGTH` (15): a development machine may lower it for a short password (D276).
- Settings › Account reworked: a profile card, the password changed in place, sessions with device
  icons and relative times, and what you can do in each workspace (everything, until roles).

### Changed (0.12 I2)

- `GET /api/v1/me` adds `signedInWith` and `sessionId`. The metadata lists the authorization and
  revocation endpoints and the `authorization_code` and `refresh_token` grants.
- The browser reads a job's progress and downloads exports and consumer OpenAPI documents with
  `fetch` and the access token; the consumer `openapi.json` link on Settings › API reference, refused
  since I1, works again. The browser runners sign in as a test person through the real form.

### Added (0.12 I1, the engine issues tokens; every route authenticated)

- The engine is its own OAuth 2.0 authorization server: `GET /.well-known/oauth-authorization-server`,
  `GET /oauth/jwks` and `POST /oauth/token` with the client credentials grant (`scope` `management`
  or `consumer`), errors in the RFC's shape. Access tokens are ES256 JWTs lasting an hour
  (`ACCESS_TOKEN_MINUTES`); their signing keys live in the database, sealed, replaced after
  `TOKEN_SIGNING_KEY_DAYS` (30) when the next token is issued, and rotated on request, at once after a
  leak (`/api/v1/token-signing-keys`).
- People (`/api/v1/users`: create, change, deactivate, never delete) and OAuth clients
  (`/api/v1/clients`, the secret shown once, a second secret with an overlap); `GET /api/v1/me`.
- `python -m app.cli.create_admin` (the first administrator, with the password rules: 15–128
  characters, not the username, not one of the most common) and `python -m app.cli.create_client`
  (a client's credentials, shown once). Migration `20261027_01`.
- `GET /api/v1/system/configuration`: the database revision and the settings, moved out of
  `GET /api/v1/system`, which keeps what the deployment runs. Settings › Deployment shows the
  migration revision; About no longer does.

### Changed (0.12 I1, breaking)

- **Every route needs an access token** except `/health`, `/health/live`, `/openapi.json`, `/docs`
  and the OAuth endpoints: `401 AUTHENTICATION_REQUIRED` without one, `401 TOKEN_INVALID` with the
  reason otherwise. This includes `/metrics` and the consumer API (a `consumer` token; its index and
  OpenAPI documents take a `management` token too, D266). Until roles
  (Z1) every active client or person may use every route. The browser shows the refusals until
  signing in arrives (I2).
- `SECRETS_ENCRYPTION_KEY` is required on every installation and seals token and webhook signing
  keys; it replaces `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`, which startup refuses by name. `PUBLIC_URL`
  names the engine's address, the token issuer. Upgrading: OPERATIONS § Authentication.

### Added (0.12 P0, design only)

- The security design: the engine as its own OAuth 2.0 authorization server (ADR-043), roles made
  of journey-named action groups granted to people, groups and clients per workspace (ADR-044), and
  change-set publication approvals with an inbox (ADR-045); every management operation mapped to its
  action group in API.md § Security; journeys J39–J43; the Security pages (U8) from approved
  mock-ups. Decisions D243–D257. No code changes yet.

## [0.11.0] - 2026-10-22

Base 0.11 is released: each workspace runs a model of its own and moves to another release on its
own (Track M, Track V), data moves between workspaces whose models differ (Track X), and the engine
is hardened for production (several processes and nodes, PostgreSQL at volume, operability, backup
rehearsal, touch drag), accepted by R: a full review of every change since 0.10.0 with an independent
reviewer (12 findings, 10 fixed, R-F7 and R-F11 kept by decision), the full backend suite, the 56
browser runners, J36–J38 by keyboard alone on two models, the accessibility and visual gates with
Settings › Operations, an upgrade from 0.10.0 and the budgets. No schema language is released; the
window stays 0.5–0.10. Licensing, the contribution and security policies and the compatibility
commitment moved to 0.12, the first public release.

Nine migrations since 0.10.0 (`20261018_01` … `20261026_01`; eight since 0.11.0-alpha.1); a database
of 0.10.0 or 0.11.0-alpha.1 upgrades on start.

### Changed (0.11, the first public release moved to 0.12)

- Licensing, contribution and security policies (L1) and the compatibility commitment with the
  supported schema versions and their dates (L2) moved to 0.12, which becomes the first public
  release; the project's name is not chosen yet. 0.11.0 is released as an ordinary release.

### Fixed (found in 0.11 R's review)

- A workspace migration's type mapping naming an attribute's source was ignored when the target type
  also had an attribute of the source's name listed first: that attribute kept the values and the
  named one lost its own (R-F1). Two attributes trading values (`a` from `b`, `b` from `a`) failed
  the preview as an internal error (R-F2).
- A released type moved to another application in the editor (`setContainment` with
  `application`) lost every record of it in the migration its activation needs, unless an API
  client mapped the type onto itself, which the migration page cannot: its records now go to the
  one application listing it (R-F3).
- The relation matrix's and the relationship form's save did not send
  `X-Expected-Model-Release-Id` (R-F4).
- A migration, or a change set's move, confirmed or queued before its workspace was retired still
  ran: it is now refused `409 WORKSPACE_RETIRED` at confirmation and as it runs (R-F5). Activation
  holds the workspace row for key share, so a retirement during its check is seen (R-F12).
- A workspace migration held the unique values' table lock, which every value write of every
  workspace waits for, from its first step to its commit (66–111 s at 100,000 records): it now takes
  it just before the switch (R-F6).
- A change set's move did not hold its workspace's assignment, so an activation committing meanwhile
  left the change set pinned to the release the workspace had just left (R-F8).
- A move's load committed its first step (the target's change set opened) without checking that the
  job was still its worker's; a worker frozen past its lease could leave a second change set (R-F9).
- The FastAPI lower bound is 0.141, the version the engine is tested on: the read guard uses
  `Depends(scope=...)`, which older versions lack (R-F10).

### Fixed (found in 0.11 R's browser runners)

- At 390px a notice with actions (a change set on another release offering to move it or its
  workspace) kept its actions beside its text: the text was a word wide and the page scrolled
  sideways by up to 339 px. A notice's actions now go below its text when they do not fit, and a
  long action wraps its label (`wp13c`, `sc15`).
- A list drawn by row number as tall as its rows, such as the type change dialog's records, could
  stay empty: with no row drawn it had no height, and with no height the virtual range drew no row.
  It now draws the rows it holds whenever that range comes out empty (`c5`).
- After applying a restructuring, focus was meant to move to Done a frame later; on a page busy
  redrawing what the apply changed, Done was not there yet and focus was lost. It moves once Done is
  drawn (`c5`).

### Changed (0.11 R)

- A migration preview holds the live rows it converts while it runs; a write to one of them waits
  for it, which ARCHITECTURE and API.md now say (R-F7, decided by the user). A preview over private
  copies is in TODO.

### Added (0.11 U1, touch drag in the record tree)

- On a touch screen a record in a tree view or the sidebar is dragged by holding it still for half a
  second (D210): moving first scrolls, a short tap opens the record. Once lifted, the finger drags
  instead of scrolling, the list scrolls at its top and bottom edge (56 px for a finger, D211), and
  the preview sits above the finger, inside the screen (D212). Let go where it was lifted, nothing
  opens; in the sidebar the node menu (Move to…) opens, also on iPhones, which had no way to open it
  (D213). Never in a publication or a read-only tree (D214).
- `test:browser:touch-u1`: Chromium with Pixel 7 emulation and real touch input, WebKit with iPhone 15
  emulation (D215).

### Fixed (found in 0.11 U1)

- The drag's edge scroll at desktop widths started its top band under the sticky top bar, so a drag
  upwards could not scroll the page; the band now starts below the bar (`scroll-padding-top`).
- `OperationsPage.tsx` failed lint (`preserve-manual-memoization`).

### Changed (0.11 Q3, attribute sorts over very large parents)

- A change set's list sorted by an attribute reads in value order, as live and publication lists do:
  the base's records it keeps and its own, each through its value index, merged by their first rows
  (`pagination.merged`, D205). At full volume the 20,000-child parent's first page takes 14.5 ms
  (167.9 before).
- A total under an attribute sort counts the records without reading their values, in every context
  (live 94 → 11 ms at full volume).
- Records sorted by an attribute that share a value come by record ID live too, as in change sets
  and publications (D206). A live cursor or anchor of such a list issued before this release is
  refused once as `INVALID_CURSOR`, and the browser restarts the list.
- Migration `20261026_01`: `ix_snapshot_attribute_values_change_set_key_boolean`, so a change set's
  sort by a boolean reads in value order (D207).
- Not changed: a position deep under an attribute sort still grows with the records listed (124 ms
  in a change set at row 15,000 of 20,000, over the budget; stored sort keys in TODO); ancestor sorts,
  measured within the budget (D208).

### Fixed (found in 0.11 Q3)

- `test_build07_wp11` expected the 12-character correlation ID O1 replaced with the request's
  `X-Request-Id`.

### Added (0.11 O2, backup rehearsal and the Operations page)

- `python -m app.cli.restore_check --restored <URL> [--backup <name>]` checks a backup restored into
  a separate database: it prepares the copy as startup would, loads each workspace's release on its
  own, counts each workspace's records, relationships, open change sets and publications beside the
  live records, and records the result, passed or failed with its code, in the instance (table
  `backup_rehearsals`, migration `20261025_01`; J12.16, J12.17, D198–D200). A copy that is the
  instance's own database is refused before anything changes.
- `GET /api/v1/system/backup-rehearsals`, paged newest first, and `GET /api/v1/system/summary`, the
  instance figures of `/metrics` as JSON (D201).
- Settings › Administration › **Operations**: the instance's figures, each workspace served or not
  and by which process, every process with its threads, connections and requests, the last backup
  rehearsal with each workspace of the copy, the earlier ones, how to rehearse and the probe
  addresses; refreshed every 15 seconds while visible (U7, D202, D204).
- `scripts/postgres.sh rehearse [<dump>]` restores a development dump into a scratch database,
  checks it and drops it; `scripts/postgres.sh backup` leaves out the processes' rows (D203).
- OPERATIONS § Backup and restore: taking a backup, rehearsing it, recovering, and what a restore
  is; the rehearsal on the development database recorded.

### Changed (0.11 O2)

- A startup refusal carries a code (`DATABASE_COLLATION`, `DATABASE_EXTENSIONS`,
  `DATABASE_REVISION_UNKNOWN`, `DATABASE_MIGRATION_FAILED`, `DATABASE_UNREACHABLE`), which a failed
  rehearsal records; the messages are unchanged.

### Added (0.11 O1, metrics, logs, health and readiness)

- `GET /health/live`, the liveness probe: `200` whenever the process answers, never asking the
  database, so a database outage restarts no process. `/health` stays the readiness probe (D191).
- Each process reports itself through the database every `PROCESS_HEARTBEAT_SECONDS` (15; table
  `engine_processes`, migration `20261024_01`). `GET /api/v1/system/readiness` names each active
  workspace served or unavailable, with the live processes that cannot serve its release and why
  (`unsupportedSchema`, `invalid`, `notLoaded`); `GET /api/v1/system/processes` lists every process
  live or silent, ready or not, with its threads, pool and counters (J12.13, D192).
- `GET /metrics` in the Prometheus text format, the whole instance in one scrape: requests by route
  template and status, durations, connections in use and missing by reason, failing threads,
  readiness, each labelled by process; jobs, webhook subscriptions, processes and unavailable
  workspaces counted when scraped (J12.14, D193, D194).
- `LOG_FORMAT` (`text`, or `json` lines) and `LOG_LEVEL`; one access line per request from the
  engine instead of uvicorn's; every request carries `X-Request-Id`, the client's when well formed,
  which `INTERNAL_ERROR`'s `correlationId` now is (J12.15, D195, D196).

### Fixed (0.11 O1)

- Processes starting together could collide building the relation matrix states (a unique
  violation logged at ERROR; the API served and derived the cells from records). The build now runs
  under the startup lock, after the bootstrap install. The JSON and text log formats showed it: the
  previous log printed the line without its level.
- The engine's INFO lines (startup builds, recoveries) were not written under uvicorn: nothing
  configured the engine's loggers, so only warnings and errors reached the console.

### Changed (0.11 Q2, value indexes)

- A change set's unique checks and key references on a number, decimal, date or instant seek the
  value instead of reading every value of the attribute in the change set and its base: four partial
  indexes on `snapshot_attribute_values` (migration `20261023_01`). Live checks already sought their
  value. The indexes are the same for every model; what follows a workspace's model is which values
  are looked up (D186).
- A move's match by a unique attribute seeks the target workspace's unique values by digest; it read
  every value of the attribute in every workspace (J38.5).

### Fixed (0.11 Q2)

- The mapping inference counted only unique text values as values the two workspaces share, and
  proposed the match on the first attribute unique on both sides. Unique values of every type count
  now, and the match goes to the unique attribute whose values the records share (J38.1).

### Added (0.11 N3, several processes)

- `DATABASE_IDLE_TRANSACTION_TIMEOUT` (300 s, `0` off), reported by `GET /system`: the database ends
  a transaction a stalled process (frozen, starved of CPU, cut off) left idle that long, so the
  writes waiting for its locks go on. A frozen process held its workspace's writes until it resumed
  (J24.3). The startup lock's connection does not carry it.
- `503 DATABASE_UNAVAILABLE` takes `details.reason` `transactionEnded` when the database's notice
  reaches the resumed process.
- The concurrency and uniqueness invariants are tested across two server processes on one database:
  a unique value, a record's version, a parent cycle, a cardinality limit, feed positions, and a
  background job's item on one node against a live write on the other.
- `tests/test_boundaries.py` finds SQL text that writes record rows outside the write unit; the three
  modules that do are listed with the lock they hold. No database constraint was needed.

### Fixed (0.11 N3)

- A job step whose database connection was lost or ended failed the job with an internal error and
  a traceback. It is rolled back and left to its lease, and the worker reports the outage in one line.

### Added (0.11 Q1, database connections)

- Each process's database connections can be set: `DATABASE_POOL_SIZE` (5), `DATABASE_POOL_MAX_OVERFLOW`
  (10) and `DATABASE_POOL_TIMEOUT` (30 s), reported by `GET /system`; OPERATIONS gives the arithmetic
  per process and per instance. A start whose processes could need more connections than the server
  allows logs a warning naming both figures (J12.11).
- A request that gets no database connection answers `503 DATABASE_UNAVAILABLE` with `Retry-After`
  and `details.reason` `poolExhausted`, `tooManyConnections` or `unreachable`, logged in one line
  naming the cause and the settings. It answered `500 INTERNAL_ERROR` with no cause in the log
  (J12.8, J12.11). The job worker, the event deriver and the webhook dispatcher report an exhausted
  pool or a full server in one plain line, as an unreachable database, not as a failure with a
  traceback.

### Fixed (0.11 Q1)

- A process with a pool of one connection could not start: the startup lock held one pooled
  connection while the bootstrap install waited for another. The lock's connection is outside the
  pool.
- Five `NOT IN` subqueries, which PostgreSQL scans once per row once they outgrow `work_mem`, are
  `NOT EXISTS`: the people export's walk, the mapping list's exclusive targets, the move binding's
  related records, a query's negated relationship criterion and the relation matrix's state filter
  in a change set. Not measured at full volume.
- The move binding's and the people export's working tables are analyzed once filled; PostgreSQL
  never analyzes a temporary table by itself, so their joins were planned on guesses. Not measured
  at full volume.

### Fixed (the model editor's moves)

- A type could not be moved to another application: Move to… and a drop on an application only set
  its parent, so the type stayed where it was, and a parent in the other application left the draft
  invalid. `setContainment` takes `application` (and `fromApplication` for a type in several): the
  type and every type under it move there with their views and detail pages, their containment and
  relations kept, in one step. A drop on another application, or its top level chosen in Move to…,
  sends it (J33.15). Nothing that can stand in the other application is left out: a list moves with
  the type it lists even when a column reaches another application's type, mapping grids and
  matrices that need a moving type follow it, a page the other application has already takes the
  panels it lacks, and what stays keeps its columns. First delivered without these, it dropped a
  list whose language column reached the translations, columns of a staying panel, and mapping
  grids; a sweep of every type to every application over three real models found them. What can
  stand in neither application (a matrix whose types no application lists together, a staying page's
  children panel of a type that moved) goes, and is named: a history entry's new `removed` lists
  it, and the editor says it after the step and in History. History names the application a type
  moved to.
- A tree view's top type given a parent left the draft invalid ("cannot exist without a parent");
  a type moved to the top dropped out of the tree it was a node of. The tree now grows up to the new
  parent, or takes the type as a top of its own, and drops what it can no longer show or offer.
- Merging a type into its parent made the survivor contain itself, and left consumer APIs naming
  the merged-away type. The containment between the two is dropped, and the consumer APIs name the
  survivor.
- Add XREF rule… listed a field several exposed types share under the first of them alone, so
  the others (a model's means of transport) seemed to have no field to match on. A rule weighs a
  field on every exposed type alike, so the list now shows each field once, under "Attributes of the
  exposed types", as the field sources do.
- A list inside a dialog (the relationship dialog's record list) carried the wheel at its first
  or last row on to the page behind the dialog, so the table there moved. A list carries it no
  further than its dialog, and the dialog holds the browser's own carry too.
- The model pane did not scroll while a drag neared its top or bottom, so rows out of view could not
  be reached; it scrolls as the record tree does, through one shared helper.
- The t1 designer runner followed 0.11: a model of its own installs into a new workspace, read
  there by the consumer tier; a wait for an undone attribute no longer trips on two matching cells.
- The Install and activate dialog's buttons fell below its frame when the differences ran long; they
  stay at its foot as Map to…'s do.

### Changed (0.11 N2, the job worker on several nodes)

- A running job keeps its lease by a heartbeat, renewed every third of `JOB_LEASE_SECONDS` whatever
  its step. Before, a step longer than the lease (a move's binding, which renewed nothing; a chunk;
  one long statement of a migration) was taken over by another process and rolled back, and with
  two processes they could take it from each other indefinitely. A job now moves to another worker
  only when its process stops renewing (stopped, crashed, frozen, cut off from the database), no
  longer when its worker waits on a lock (J24.3 revised).
- A job queued through a process whose worker is busy starts at once on an idle process, which
  hears it through `LISTEN`; before, it waited for that process's next poll, up to 60 s.

### Fixed (0.11 N2)

- Two dry runs, inferences, mapping inferences or profile checks of one subject sent at the same
  moment both ran, neither stopping the other, and an older inference finishing last replaced the
  newer one's proposals. They are now decided one after the other; the later one stands.
- A profile, inference, dry run or check asked to stop after its last check still completed and
  wrote its result; it now ends cancelled, writing nothing.
- Two files uploaded to one import profile and profiled on two processes could leave the profile's
  check on the older file, when that file finished last. A file replaced meanwhile is no longer
  checked.
- A cancel sent while a move settled its rows, or deleted in its source, waited for that step; it
  now answers at once, and a cancel during the source's deletion stops it there.
- An export taken over by another process after its first stalled could be served corrupted or
  removed: both wrote one partial file, and the first, finding its lease lost, removed the job's
  files, the new owner's included. Each worker now writes and removes only a partial file of its
  own lease, and renames it into place under the job's lock.

### Added (0.11 N1, several processes)

- Model administration works with several processes on one database: Uvicorn workers
  (`WEB_CONCURRENCY` above 1) or instances on several nodes. Startup no longer refuses
  `MODEL_ADMIN_MUTATIONS_ENABLED` with more than one worker. A release activated or a workspace
  migrated through any process is served by every other from its next request, with no restart.
- Processes starting together on one database check, migrate and install the bootstrap model one at
  a time under a database lock; before, the second could fail its migration and stay in maintenance
  mode. Release installations take a database lock in place of the in-process one, so two processes
  installing the same model at once answer `201` and `200` with one release instead of a `500`.
- A read whose workspace was migrated, or whose change set was moved, to another release while it
  ran answers `409 MODEL_RELEASE_CHANGED` instead of one release's model over the other's data, in
  one process or several; the shell's notice offers Reload. The in-process guard it replaces covered
  only the moment a request resolved its release.

### Fixed (0.11 N1)

- A write whose commit check waited for an activation of its workspace could commit under the
  release it no longer ran, and an activation waiting for another one answered `503` ("runs no
  installed release") instead of `409 ACTIVATION_CONFLICT`. Both locked the workspace's assignment
  joined to its release; after the wait, PostgreSQL rechecked the join against the release read
  before it, and the switched assignment dropped out. They now lock the assignment alone.
- The Settings navigation test still listed the pages before "Copy and move" (X4).

### Fixed (0.11 X6, list reads)

- A table with relation columns opened in seconds: a column showing a value of each related
  record's ancestor built every related record whole (all its values, its path) and kept one value,
  250 ms of a 294 ms read for 200 rows, and the table read 200 rows at once. An expansion that names
  its fields (every relation column does) now reads only those fields, with the ancestor's value
  found by a walk up the parent chain, in the one statement it already ran; the answer is the same in
  live data, a change set and a publication. A 20-row page with relation columns now loads 3 to 4
  database rows per listed row instead of 6.5 to 8.5.
- Identical reads made while the first is still in flight share it: the development build's double
  mount no longer sends every read twice, and a page load reads capabilities, the workspace and the
  rail's lists once each. Nothing is cached.

### Changed (0.11 X6, long lists)

- Every long list (collections, record panels and relationships, the model editor's tables, job,
  migration, move and profile reports, the relation matrix, the mapping grid, change set review, the
  restructuring and tree-move dialogs, the matrix cell dialog and column filter, the record lookup)
  is drawn by row number: the scroll space spans the whole list, sized from its total, and only the
  rows on screen and a screen either side are in the page. A row whose page has not arrived shows as
  a loading row at its place, and pages arriving or rows forgotten move no other row. The browser's
  own scrollbar is the list's; the hand-drawn one is gone. Every read is the reader's page (20 by
  default); a scrollbar drag, a fling or the page field reads once where the list comes to rest. An
  edit in place keeps the list where it was. The record tree keeps its groups as they are.
- A list reads on in the background, a page at a time, until it holds about as much as it keeps
  (600 rows): a list of a few hundred records is held whole a moment after it opens, so scrolling
  never meets a row not read (reported 2026-10-19: grey rows while scrolling a few hundred records).
- Scrolling a table with relation columns no longer stutters. A relation cell works out how many
  chips fit from their text and its column's width instead of drawing every chip, measuring it and
  drawing again; the edit and remove buttons are drawn in the row the pointer is over or that holds
  focus, the other rows keeping their room (on a touch screen every row still has them); a row
  already drawn is not drawn again while the list scrolls; the visible rows are found from the
  scroll position, not read from the page. In the production build the reported view scrolls at a
  steady 60 frames a second.
- Fixed: a row could move under the reader while scrolling (row heights rounded to whole pixels;
  the first drawn row losing half its border), and Ctrl+End followed at once by Ctrl+Home landed at
  the end.
- Known limits: the browser's find in page finds only the drawn rows (the list's search finds every
  record); a screen reader browsing a table without moving focus meets a row's edit buttons only in
  the row that has focus.

### Fixed (tables)

- Lists drawn by the shared table (collections, record panels, the model editor's preview and the
  rest) scroll without jumping: the columns keep the widths the first rows laid out instead of
  moving as rows come and go; a page read while scrolling is drawn in the background, row by row;
  writing the list's place to the address no longer draws the page again. (The 200-row reads and
  the browser's scroll anchoring of this change were replaced in 0.11 X6 by lists drawn by row
  number.)
- The wheel is no longer held in a table: it first brings the whole table, with its controls, into
  view, and at the table's first or last row the page scrolls on. The table's height leaves room for
  the top bar, the data band and its controls. Carrying one gesture's momentum on from the table to
  the page is in place but not yet smooth (reported 2026-10-19).
- The model editor's issues and history start closed; Show issues opens them without keeping them
  open next time.

### Added (hierarchy browser)

- Expanding a record or type heading in a hierarchy (the rail and the tree lens) opens its child
  when it holds only one that can expand: a record's only heading, a heading's only record. Only
  that one level opens, so the reader sets the depth; with several children all stay collapsed. It
  happens at every expansion, also after the child was collapsed by hand, and the tree's first
  display opens a sole top-level heading. A reveal (the open record's path) or a drag does not.

### Fixed (navigation rail)

- The rail no longer scrolls by itself. A record group finishing its load (its first page, the
  active record's branches, a reload after a write) scrolled the rail to that group, so the rail
  jumped as lists arrived; now only keyboard movement in the tree scrolls it, and only the rail,
  never the page. The tree lens loads the same way, and shows a record it reveals on request.
- The rail keeps its place for one application in one workspace, across pages, records and views,
  and into and out of a change set or publication, which mount the frame afresh. Another application
  or workspace opens the rail at its top, instead of at the offset the previous one had.
- A record chosen in the rail leaves focus in the rail, as a collection or group already did; the
  record page no longer takes it.
- Rows dropped or added above the view (a long group paging on, Show earlier records) no longer
  shift it in a browser without scroll anchoring; scrolling past the rail's end no longer scrolls
  the page.

### Fixed (0.11 X5)

- Publishing a change set into a workspace whose records are newer than the database's statistics
  (a moved workspace, an import into an empty one) took minutes: freezing the publication's
  relationships joined both ends to the records and PostgreSQL paired every record with every
  other, and freezing its records recomputed the workspace's values for each record. A publish of
  11,000 moved records took 9 minutes and now takes 19 s; 110,000 records publish in 3.4 minutes.
  The same copy opens a change set over current live data, so a small move just after a large
  publication no longer waits two minutes (the 13-second wait seen in X3).
- A move's dry run built each record's item by reading every relationship once per record: 63 s of
  an 11,000-record dry run, now under 6 s.
- A move, an import or a publication of more than 65,535 records failed with a database error:
  the unique-value check after the write, the write unit's removals and the publication's merge
  listed every record as a parameter of its own. Each is now one array parameter or a join.
- Moving a whole subtree kept its top record in the source, "with dependants", when those
  dependants were the records the same move deleted: the source's deletions now run in passes, so
  a parent is deleted once its moved children are.
- A move's deletions refused before the copy is published name the copy's change set and workspace
  instead of its ID.
- The copy and move editor answers faster at everyday sizes: a step's figures in 0.3 s at 200
  records and 1.4 s at 2,000, the editor open in 1.1 s and 2.0 s. A dry run of records just written
  read the selection again for every record (4–7 s at 2,000 records, now under 1 s on the server);
  a repeated dry run in a larger workspace compared its own rows with each other (40 s, now 1.7 s);
  the relationships whose records do not move were looked up one by one; and the page redrew every
  mapping row for new figures.
- The mapping grid loads again: since the tables began reading 200 rows at a time it asked the
  coverage route for more than its 100 and showed "Could not load this content".
- The copy and move editor's default buttons say which field they change ("Set a default for
  Steward…"), so they are not two buttons both named "Change…".

### Added (0.11 X5)

- `test:browser:workspace-x5`, the move checkpoint: records copied and moved between workspaces of
  partly compatible models through a proposed and hand-completed mapping, the report, the reviewed
  change sets published, a second copy updating the same records, records moved back to their
  originals, and the editor timed at 200 and 2,000 records.
- The copy and move surfaces are in the accessibility and visual gates.
- `volume_baseline.py --only-move`: a whole volume workspace moved into another model, each step
  timed once, with every statement over half a second named.

### Added (0.11 X4)

- The move editor in the browser. Settings › Data operations › **Copy and move** lists the mappings and the
  recent moves; **New copy or move…** chooses two workspaces and a saved mapping or a new one, proposed by
  the engine and applied before the editor opens. A workspace's page in Settings › Workspaces has
  **Copy or move data…**, the same dialog with that workspace as the source.
- The editor (`/settings/moves/{mapping}?from=&to=`): both workspaces and models, what moves (every
  mapped type, the whole workspace, chosen types with filters, or one record and its subtree), Copy
  or Move, the dry run's figures with their change since the last step, the source's types, the
  mapping by type with every row a step marked **Proposed** while it is as proposed, undo and redo,
  and why a row was proposed with its evidence and alternatives. Each step runs the dry run of every
  item again and cancels the one before; a mapping with problems lists them, linked to their rows.
- **What cannot move**: every item by reason, linked to the mapping row that changes it; **Start the
  move…** opens the change set (and, for Move, the source's deletions) under a name given, and a
  mapping or release changed since the dry run asks to run it again. At 390px the editor is tabs.
- `ui/ProposalNote` and `ui/OutcomeCards`, shared with the workbook editor and the migration page;
  the model editor's undo and redo rules read a mapping's history too.

### Changed (0.11 X4)

- The move editor says what is happening in one status line under its title: the dry run in
  progress and why Start waits, the dry run ready, the copy or move loading with its progress, and
  done with the change set to review. A copy is called a copy throughout; the settings page is
  **Copy and move**.
- The change set bar shows "Change set validation passed" beside its buttons instead of in a notice
  below, so the buttons stay where they are.
- The workspace selector lists active workspaces only; a retired workspace is opened from Settings ›
  Workspaces.

### Fixed (0.11 X4)

- A move's relationship row names its two records (`fromName`, `toName` on `GET
  /api/v1/jobs/{jobId}/rows`), and the report shows each as "‹from› → ‹relationship› → ‹to›"; rows of
  one record looked alike, naming it by ID. A refusal by a relationship end's criteria reads "Record
  not allowed at a relationship's end", saying what it means.
- The jobs list names move and mapping-proposal jobs, which it showed without a kind.

### Added (0.11 X3)

- The move between workspaces whose models differ. A move's dry run (`POST /api/v1/moves`) now waits
  for confirmation, and `POST /api/v1/jobs/{jobId}/confirm` loads what it previewed into a new
  change set of the target workspace, opened for review over current live data; with `stage:
  execute` the move loads at once. Nothing reaches the target's feed or consumers until that change
  set is published.
- Where each record a move created came from (its source workspace and record) is kept: a second
  move updates the records found again, and a record moved back updates its original
  (`updateOriginal`, `foundBy: origin`) or, when a move deleted the original, is created again under
  the original's ID. A created record's row names its `origin`, and a record's history names it on
  every entry a move caused (`cause.origin`).
- `mode: move`: the copy, plus a change set of the source deleting each selected record that loaded
  with its own relationships; a record changed in the source since the dry run (`SOURCE_CHANGED`)
  or one that a record staying depends on (`OBJECT_HAS_DEPENDANTS`) is kept, each row saying what
  became of it in the source. The summary names both change sets, the source's feed position at the
  load and the deleted and kept counts.
- `409 MOVE_COPY_NOT_PUBLISHED`: a move's deletion change set publishes only after its copy;
  `422 MOVE_NOTHING_TO_MOVE`: a confirmation with nothing to create or update. A confirmation is also
  refused, leaving the dry run waiting, when the mapping changed (`MOVE_MAPPING_CHANGED`), either
  workspace runs another release (`MODEL_RELEASE_CHANGED`) or one is retired.
- Migration `20261022_01`: the table `record_origins` and a change set's `waits_for_change_set_id`.

### Changed (0.11 X3)

- A move's dry run ends in `awaiting_confirmation` instead of `completed`, and expires unconfirmed
  after the job retention, as an import's preview. Its rows can be filtered by the outcome
  `updateOriginal`.

### Fixed (0.11 S1)

- The job worker runs one chunk at a time whichever thread drives it: its claims accept its own
  leases, so a second thread of the same worker (a test calling `run_until_idle` while the service's
  thread ran) could run one chunk twice and fail the job.
- Three tests left behind by per-workspace activation (0.11 M1) assert it again: J35 and the J27
  export activate into the workspace they use, and the unique-value rows are checked per workspace.

### Changed (0.11 S1)

- Backend test runs: in a parallel run each journey test goes to a worker on its own, while any
  other test module stays on one worker, so a large journey module spreads over the workers (J34
  with J35, 1 min 10 s; J34 alone took 5 min 3 s). The journey model file is written whole before
  any worker reads it.
- The full backend suite runs with six workers (`pytest -n 6`) under a ceiling of 11 minutes,
  revised from 5 (D126): 10 min 15 s for 5,950 cases with the machine usable, where ten workers
  took 8 min 49 s at a load near 145. A package's checks have a ceiling of 3 minutes, revised from 2
  (D127). The development and test database folders are ignored by git also as links to `.nosync`
  folders.

### Added (0.11 X2)

- The dry run of a move between workspaces whose models differ (`POST /api/v1/moves`), a background
  job of kind `move`: what each selected record and the relationships it holds become in the target
  workspace through a model mapping at the version the client read, read from the source's live
  data or one of its publications. The selection is the whole workspace, types with an export's
  criteria, a subtree, records by ID, or several of these together. Every row is listed at
  `GET /jobs/{jobId}/rows` (filtered by `outcome`, `reason` and `sourceType`): `create` under the
  record's counterpart ID, `update` of a record found by its counterpart or by the mapping's match,
  `refused` with the target's own refusal, or `notMoved` with the mapping's reason and the step that
  changes it; with what a moving record leaves behind (attributes not mapped, values that do not
  convert, read-only attributes, effective periods the target type lacks) and possible duplicates.
  The job's `move` summary counts rows by outcome, type, relation type and reason. Nothing is written
  to either workspace.
- `422 MOVE_MAPPING_HAS_PROBLEMS`: a move whose mapping names what the two workspaces' releases
  lack or do not allow is refused with the problems.
- Migration `20261021_01`: the `pgcrypto` extension, the function `rdm_counterpart` (a counterpart
  ID derived in PostgreSQL, the same as the Python one) and the job kind `move`.

### Changed (0.11 X2)

- RDM Engine requires the `pgcrypto` extension beside `pg_trgm` and `btree_gin`; startup creates it
  or refuses with the instruction to install it, as for the other two.

### Added (0.11 X1)

- Model mappings (`/api/v1/model-mappings`): what each type, attribute, relationship and parent of
  one model becomes in another, with value maps, defaults and how existing target records are
  matched, saved between two workspaces' releases. A mapping changes only through operations
  (`mapType`, `mapAttribute`, `mapRelation`, `setParent`, `setMatch`, `setValueMap`, `setMissing`,
  `setDefault`, `setReleases` and their removals), with history, undo and redo; every read reports
  its problems (what a release lacks or no longer allows) and coverage (what it leaves out),
  against its releases or the releases two named workspaces run.
- The mapping's inference, a background job of kind `mappingInference`: proposals per type and per
  relationship from keys, names, attributes, parents and the records the two workspaces share, each
  with its evidence and alternatives, applied as steps marked as proposed. Two workspaces on one
  model are proposed as identity.
- Migration `20261020_01`: the tables `model_mappings`, `model_mapping_operations` and
  `model_mapping_proposals`, the job kind `mappingInference` and an index of a mapping's jobs.

### Changed (0.11 X1)

- A model draft and a model mapping share one history of steps, undo and redo; a draft's answers
  are unchanged.

### Added (0.11 V4)

- The schema-language window, 0.5–0.10, and the conversion rules between its versions written in
  one place (APPLICATION_MODEL, "Schema versions and the window"): reading, writing, running side by
  side, moving data between releases of different versions (by declarations only, never by version)
  and what happens outside the window. The window is declared once (`SCHEMA_VERSIONS`), held by a
  unit test.

### Changed (0.11 V4)

- Installing a draft of a schema outside the window answers `422 UNSUPPORTED_SCHEMA_VERSION` with
  `draftId`, `schemaVersion`, `supportedSchemaVersions` and `operation: "install"`, as activation
  does, instead of `422 INVALID_MODEL`.

### Fixed (0.11 V4)

- `RDM_MODEL_PATH` naming a model of a schema outside the window stopped startup with a traceback;
  it now refuses with a message naming the setting, the file, its schema and the supported ones.
- A workspace on a release of a schema newer than the window was logged with the schema 0.4 upgrade
  command, which cannot help; the log now says a later RDM Engine wrote the database and is the one
  to run.

### Added (0.11 V3)

- A change set left on a release its workspace no longer runs moves onto the workspace's release
  even when its content does not fit it: `POST /change-sets/{id}/model-migrations`
  (`expectedChangeSetVersion`, optional `targetReleaseId`, `typeMappings`), registered where
  background jobs run, starts a `migration` job (`parameters.moves: "changeSet"`). Its preview
  converts the change set's own content with a migration's rules, lays it over live data as it is
  now and lists every conversion, type change, loss and refusal, changing nothing; a record or
  relationship the change set changed that live data changed since it started is refused
  (`CHANGE_SET_CONFLICT`, `MAPPING_SET_CHANGED`), as is every rule the moved change set breaks.
  Confirmed (the change set's version, the workspace's assignment and feed position), the change
  set's rows, its base (now a capture of live data) and its release change in one transaction; live
  data, the workspace's release and its feed never do. Code `MIGRATION_TARGET_NOT_WORKSPACE_RELEASE`.
- The change set bar's notice offers **Move this change set to ‹release›…** beside V2's offer; the
  migration page names the change set, says live data stays as it is, confirms with **Move change
  set** and opens the change set when done.
- `snapshot_values.reindex_change_set`: a change set's typed value index rebuilt from its rows in set
  statements.

### Added (0.11 V2, API)

- A change set on a release its workspace no longer runs (typically one started from an older
  publication) is published by migrating the workspace to the change set's release:
  `POST /workspaces/{key}/model/migrations` takes `changeSetId` and `expectedChangeSetVersion`, and
  `targetReleaseId` is then optional. The preview also lists what would stop the publication as
  refused items (`CHANGE_SET_CONFLICT` and the graph's rules); the confirmation binds the change
  set's version and the active publication; the migration, the switch and the publication happen in
  one transaction, or nothing does. The summary names `changeSetId`, `changeSetVersion`,
  `activePublicationId` and `publicationId`. Code `MIGRATION_TARGET_NOT_CHANGE_SET_RELEASE`.

### Added (0.11 V2, browser)

- The change set bar of a change set on another release offers **Move ‹workspace› to ‹release› and
  publish…**; the migration page then says it publishes the change set, lists what would stop the
  publication, confirms with **Migrate and publish** and names the new publication.

### Added (0.11 V1, API)

- `POST /workspaces/{key}/model/migrations`: a workspace's data migrated to another installed
  release, of its model or another, as a `migration` job. Its preview changes nothing and lists, at
  `GET /jobs/{id}/rows`, every value converted, record reclassified, loss and refusal; `typeMappings`
  keeps a renamed type's records under their IDs. `POST /jobs/{id}/confirm` binds the reviewed
  assignment version and feed position and needs `acceptLoss` for a loss; the data and the
  workspace's release then switch in one transaction, each change audited with its feed position.
  Codes `MIGRATION_REVIEW_STALE`, `MIGRATION_HAS_REFUSALS`, `MIGRATION_LOSS_NOT_ACCEPTED`,
  `INVALID_MIGRATION_MAPPING`, `MIGRATION_TARGET_IS_CURRENT`, `MIGRATION_FAILED`.
- A job's `migration` summary; `POST /jobs/{id}/confirm` takes an optional body.
- Migration `20261019_01`: the `migration` job kind, `rdm_convert_value` and an index of a
  migration's items.

### Added (0.11 V1, browser)

- Settings › Model's activation dialog offers **Preview the migration…** when the data does not fit;
  the migration's page (`/settings/model/migrations/{jobId}`) lists what the release no longer has
  with a choice for each missing type and field, the items by outcome, and confirms once the loss is
  accepted; a stale review asks to preview again. `test:browser:workspace-v1`.
- A migration is refused with `409 CONSUMER_CONTRACT_VERSION_REQUIRED` when its target changes a
  consumer API's contract without a new version, as activation is.
- `test_migration_budget` (`budget`): a workspace of 100,000 records migrated once.

### Changed (0.11 V1)

- The compatibility analysis can list the records behind each rule a record breaks, and its scoped
  uniqueness count climbs from the rule's targets to their scope only (over 9 minutes at 100,000
  records before, 5.8 s now); activation shares it.
- A migration's long steps renew the job worker's lease as they run.
- ADR-034 amended (D71): a migration's type mappings change record types in live data.

## [0.11.0-alpha.1] - 2026-10-17

Each workspace runs a model of its own, released on its own (D12): everything since 0.10.0, Base
0.11 packages P0, M1 (with M2), M3, M4, M5, M6 and M6a. Moving a workspace's data to another release
(Track V) and data between workspaces whose models differ (Track X) follow in 0.11.0. One migration
since 0.10.0 (`20261018_01`, a release per workspace); a database of 0.10.0 upgrades on start.

### Added (0.11 M6a)

- `X-Expected-Model-Release-Id`, an optional request header on every management route: a request
  naming a release its workspace, change set or publication no longer resolves is refused with
  `409 MODEL_RELEASE_CHANGED` before anything is read or written. The browser sends it on its data
  writes; a page built before its workspace's model changed shows the refusal and a toast with
  Reload instead of saving under the new release.
- The API exposes `X-Model-Release-Id` to browsers on other origins.

### Added (0.11 M6)

- `test:browser:workspace-m6`: the workspace-model checkpoint, J36 composed in the browser on two
  generated models beside the starter.
- The workspace-model surfaces of M5 and M6 in the accessibility and visual gates, light and dark.

### Changed (0.11 M6)

- Settings › Model is laid out as Settings › Workspaces: the models in a list (the default
  workspace's first) beside the selected model's card with where it runs, its releases and its
  drafts. A redesign is planned for 0.14.
- "Activate a release…" is "Change model…"; its dialog groups the releases by model, the
  workspace's own first, and preselects nothing in another model.
- The top bar shows the default workspace's model's product name on every page, whatever model the
  shown workspace runs.

### Fixed (0.11 M6)

- On a phone, choosing a workspace from the band by tapping did nothing; only the keyboard switched.
- On the "not in this workspace's model" page the sidebar marked a collection as current; a
  workspace switch read the sidebar's collections twice.
- `test_boundaries::test_tiers_hold` failed on an import cycle in the source-file dry run; a model
  lifecycle test passed only after the tests before it.

### Added (0.11 M5)

- The browser follows each workspace's model: switching workspace changes the applications,
  navigation and pages to that workspace's model, with a toast when the model or release differs;
  the workspace selector names each workspace's model and release and marks another model or
  release.
- A page saying what an address asks for that the workspace's model lacks, with the workspaces
  whose model has it; the same for an unknown workspace and one whose release cannot be loaded.
- Settings › Model shows the workspaces with their models and releases, the installed releases by
  model with the workspaces running each, and the drafts; a release is activated into one workspace
  from that workspace's row or the release's page, checked against that workspace's data alone.
- Settings › Workspaces creates a workspace on another installed release; the model editor's
  Install and activate puts the release into an existing or a new workspace.
- `releaseName` on a workspace's model (workspace responses, its model route, `GET /workspace-models`,
  an activation's answer); `workspaceKey` on `GET /model-releases/{id}/diff`, whose `compatibility`
  and `consumerContracts` then describe activating into that workspace.
- `test:browser:workspace-m5`.

### Changed (0.11 M5)

- An address naming an application the workspace's model lacks no longer opens the start page
  silently; it says so.
- A job's page and toasts name types under the job's own workspace's model; the model editor's
  preview reads records only from a workspace running the draft's model; the load into a change set
  compares the draft with the release its chosen workspace runs.
- A release's page shows which workspaces run it and checks it against each workspace of its model;
  its Activate opens the activation dialog. The single "Active" release is gone from Settings › Model.

### Added (0.11 M4)

- `GET /objects` takes `workspaceKey` repeatable: two or more read those workspaces' live records
  in one paged list, each under its own workspace's model. A type or application some of their
  models lack is refused `422 MODEL_ELEMENT_NOT_IN_EVERY_MODEL`, naming those workspaces; a change
  set or publication with several workspaces is `422 WORKSPACE_CONTEXT_MISMATCH`.
- Every item of `GET /objects` names `modelReleaseId`, the release it was read under.

### Changed (0.11 M4)

- Counterparts stand only between workspaces running one model: an item or file row naming a record
  of a workspace running another model is refused `COUNTERPARTS_ACROSS_MODELS` (with the workspace
  and both model keys), and the import's notice says so, instead of loading it as this workspace's
  own record under a model it does not belong to.

### Added (0.11 M3)

- Import profiles belong to a model: `modelKey` on every profile, `workspaceKey` on its create,
  update, read and list, and the list's `modelKey` filter. A profile is refused
  (`422 IMPORT_PROFILE_MODEL_MISMATCH`) when saved, imported with or given a file in a workspace
  running another model, and reads there as not valid with that problem.
- Draft compilation and the release diff report `compatibility.workspaces`: what activating would
  need in each (not retired) workspace running the candidate's model, against its own release.
- The consumer API index and each OpenAPI document take `workspace` and answer `RDM-Workspace` and
  `X-Model-Release-Id`; the index's document links carry the workspace. The API reference page
  (`/docs`) takes `?workspace=`.

### Changed (0.11 M3)

- A draft is compared with its base release, or without one with the newest installed release of
  its own model, or with nothing when it is a new model (every element `added`, no consumer
  contracts, no data impact). A draft-only operation's impact counts only the workspaces running the
  draft's model. The top-level `compatibility` is what activating into the default workspace would
  do.
- Installing a draft whose profile key another model's profile holds is refused before anything is
  installed (`409 IMPORT_PROFILE_MODEL_MISMATCH`); installing no longer runs an unused
  compatibility analysis.

### Added (0.11 M1)

- Each workspace runs a model release of its own (ADR-042): `GET /workspaces/{key}/model`,
  `GET /workspace-models` (by model or release, paged), `modelReleaseId` on `POST /workspaces`, and a
  workspace's `model` on every workspace response. Two workspaces may run two different models.
- `POST /workspaces/{key}/model/activation` activates a release into one workspace: the compatibility
  check counts that workspace's data alone, the contract check compares with its release, only its
  subscriptions are suspended and its matrix states resynchronised; the answer lists its change sets
  left on the previous release (`changeSetsLeftBehind`).
- Every read and write resolves its workspace first, then that workspace's release: `GET /model`
  adds `RDM-Workspace`; a live write naming a record runs under the record's workspace model; jobs,
  batches, source files, consumer reads, subscriptions and webhook delivery under their workspace's.
  Unique values follow each workspace's release (D28).
- `GET /model-releases`: `assigned` and `workspaces` per release and the `assigned` filter (D24);
  activations name their `workspaceKey`.

### Changed (0.11 M1)

- The commit guard checks each workspace a write resolved, under a share lock on that workspace's
  assignment row: `409 MODEL_RELEASE_CHANGED` names `workspaceKey`, `resolvedReleaseId` and
  `currentReleaseId`. `CHANGE_SET_MODEL_RELEASE_CONFLICT` names the workspace.
- A release this version cannot serve makes only the workspaces running it unavailable
  (`503 MODEL_REGISTRY_UNAVAILABLE` with `workspaceKey`, `releaseId`, `schemaVersion`); `/health` is
  503 only when no workspace can be served (D29, D34).
- Settings › Model reads and activates the default workspace's model; Load into a change set
  activates the release into the workspace it loads into.

### Fixed

- Leaving a change set (discard or publish) left its confirmation as a notice above every page until
  the browser reloaded; it is now a toast, shown once and dismissable (reported 2026-10-15).
- Opening Settings reshaped the top bar: a way back was inserted after the product mark, shifting the
  application tabs, and the Settings icon became a wider "Settings" tab. The bar is now the same on
  every page: the Settings icon keeps its place and width and is marked current by the tabs' ink
  underline, and Settings has no way back of its own (the product mark and the application tabs
  leave it) (the user, 2026-10-15).

### Removed (0.11 M1)

- `GET /model-runtime-state`, `POST /model-releases/{id}/activation`, the `active` field and filter
  of `GET /model-releases`. Migration `20261018_01` gives every workspace the release the instance ran
  (version 1) and drops `model_runtime_state` and `model_releases.is_active`.

### Planned (0.11 P0)

- Base 0.11's design pass: each workspace runs a model of its own (ADR-042), with the decisions
  D4–D29 and the inventory of what a move between models meets accepted; the API design for a
  workspace's model, activation into one workspace, migrations, mappings between models and moves
  (API.md § Workspace models); journeys J36–J38; mock-ups of the shell and Settings across workspace
  models and of the move editor.

## [0.10.0] - 2026-10-15

Base 0.10 is released: the model designer and spreadsheet onboarding, accepted by R (a full review
of every change since 0.9.0, the full suites, the 49 browser runners, the accessibility and visual
gates with the spreadsheet and cell surfaces, the schema 0.10 checks and the budgets). Schema 0.10
(an application's `navigation`) is a released schema language; the starter stays content release
0.9.5 on schema 0.9.

Six migrations (`20261012_01`, source files and the `profile` and `dryRun` job kinds;
`20261013_01`, a model draft's import profile; `20261014_01`, a draft's proposals and the
`inference` job kind; `20261015_01`, the `profileCheck` job kind; `20261016_01`, a source file's
column statistics per block; `20261017_01`, indexes on the jobs a draft, a profile or a source file
has); a database of 0.10.0-alpha.1 upgrades on start.

### Fixed (0.10 R)

- An import that deletes the records missing from its file (`missing: delete`) through a source
  keyed by name no longer deletes a record a refused row names (an ambiguous name) (R-F1).
- The dry run's difference from the last one compares each source with its own figures when
  several load one type from one sheet (a list read block by block, translations by language) (R-F2).
- `allowRelation` with `required` to a released type is refused with its impact, as a required
  attribute is (R-F3).
- A list's single-valued relationship cell finds its relationship among every page of the record's
  relationships (R-F4); a relation column's chips use the cell's width again beside the edit icons
  (R-F18).
- A file's profile no longer blocks its owner's next upload and the draft's steps; a file's delete
  stops every job reading it first (R-F5, R-F8); inference and the profile's statistics renew their
  lease and stop for a cancel request (R-F6, R-F7); a dry run or check whose file went fails
  `SOURCE_FILE_NOT_FOUND`; the sweep supersedes a file a concurrent upload left current (R-F9);
  applying proposals locks the draft first (R-F10); a profile-only step's audit entry names the
  profile (R-F11).
- A rename or another step that cannot change the load leaves the running dry run to finish rather
  than stopping it with none to follow (R-F15).
- Checking the next version of a workbook that loads related records (translations) took 56 s at
  200 rows: the related records are found through each row's own relationships (R-F16). At 10,000
  rows a dry run's or a check's recording joined its fresh outcomes row against row: outcomes are
  inserted with their source and row, and the summary analyzes the job tables first; W1′'s check at
  10,000 rows 16 s again (R-F19).
- The dry run's, the check's and the inference's lookups of their earlier jobs use an index
  (migration `20261017_01`) (R-F14).
- Import profiles: an earlier read of the check answering late no longer sets the page back to
  Checking (R-F17).
- History names a renamed element by its name before the step; an editor table's cells break between
  words; Export, Import and both Load dialogs choose their workspace with the shared field, every
  page read; the editor's drawer counts every step of the draft.

### Added

- Base 0.10 A8c: lists of one shape read as one list under their headers (D140–D146; J34.10,
  J27.8). Three lists or more of a sheet laid out for reading under one title (or none) whose
  columns have the same kinds carry, on each list's proposal, the alternative "Read these N lists as
  one list under their headers": one step replacing them by a parent list of the headers and one
  list contained in it, a source per former list fixed to its header. A row under a list's header
  answering none of its yes/no columns is a second header row (a note with `meaning: "heading"`),
  skipped. Import: a source's `parent` (`objectTypeKey`, `matchBy`, `value`, `missing`) sets every
  row's parent, `PARENT_BOUND_TWICE` beside a parent column; a source keyed by name finds a row's
  record among its parent's children, one key under one parent across sources. `addSource` and
  `setSource` take `parent`. `test:browser:authoring-a8` gains the alternative applied from a list.

- Base 0.10 A9: a list's cells edited in place (D131–D139; J02.7, J13.11). In a collection or a
  record's table, the cell under the pointer shows a pencil and, where an optional value or a single
  relationship is set, a trash beside its value (always on touch); a click elsewhere still opens the
  record. A value or name is edited in the cell; a relationship a record holds one of is set,
  changed (among the binding's candidates) or deleted; one it holds several of is edited in a
  dialog of ticked records, saved as one inline atomic batch of the records added and removed. A
  toast says whether a save went to Live or the open change set. Ancestor columns, containment,
  required ownership, read-only bindings, computed fields and publications show no icons. The
  details panel's remove and the relationship panel's delete are one dialog each, shared with the
  cells. No API change. `test:browser:authoring-a9`.

- Base 0.10 A8b: the editor's source pane list by list (D122–D130; J34.10). A sheet laid out for
  reading shows its lists under their titles, each Proposed, Loaded or Not loaded, the open list's
  columns under it (one tree, keyboard operable); a selected list shows its titles, cells, note,
  what it loads, Proposed because and the sheet's cells around it. **Adjust list…** sets its header
  row, last row and columns over the cells (one `setSource`, and Name the list after the new
  header); **Don't load this list** removes its source and, when nothing else needs it, its list
  type, in one step; **Load as a list…** reads a rectangle as a list. API: `GET
  /source-files/{id}/profile/sheets/{sheet}/cells?range=` (paged rows of staged cells), `POST
  /model-drafts/{id}/inference/list` (a rectangle's `listBlock` proposal, not stored), `422
  INVALID_RANGE`; `setSource` moving a header row or narrowing a block keeps each binding on its
  column letter, the rest unmapped. `test:browser:authoring-a8`.

- Base 0.10 A8a: lists of a sheet laid out for reading, through the API (D114–D121; J34.10). A sheet
  holding no table but lists side by side and under each other is read list by list: each column
  run split at empty rows, prose left out, each list's header, the titles above it and a note under
  its header (`multiple answers`, `multiple choice`, `free field`, …); the profile's sheets gain
  `laidOut`, its blocks `titles` and `note`, and column statistics are kept per block (migration
  `20261016_01`; a column holding only its header listed with `filled` 0; an overlap names its
  `block`). The inference proposes a `listBlock` per list: a list type loading its block by name, its
  translations (else "Language k"), a yes/no column as an attribute, two or more as a flag set, the
  note row skipped and the note the type's description; a navigation group per title over two lists
  or more; a free field or a header without values is a warning. A source's key may be `{"field":
  "name"}` (`AMBIGUOUS_NAME_KEY`, `KEY_NOT_BOUND`); `addSource` and `setSource` take it. W3 gains a
  second band of lists with a workbook's shapes.

- Base 0.10 A7: model-description sheets and matching across files (D106–D113; J34.9). A sheet of a
  field, a type and a target column is read before every other rule: the described type, a list per
  target read from its sheet by its ID and name (a placeholder ID skipped), a list to be defined
  added with nothing to load, a relation per lookup field, an attribute per plain field, one set per
  flag target (`modelDescription`, `describedList`, `describedField`, `describedFlags`). Extend mode
  across files: a sheet matched to a type by its fields, a proposed list to an existing type of its
  name, a code column to a stored unique attribute; missing values and name drift against the stored
  records in the evidence and the warnings, each with an alternative (create on load; load the
  file's names). A source's `rowsWithoutKey` (`refuse`, `skip`, `SKIP_NEEDS_KEY`) and `skippedRows`
  in the binding report and the dry run; `setSource` takes it. The placeholder words gain `tbc`, `to
  be defined`, `to be decided`, `to be confirmed`. The editor: a description sheet's columns read
  Describes the model, the dry run's rows skipped figure, the new evidence words;
  `test:browser:authoring-a7`. W2's generator returns its structures.
- Base 0.10 A5c: the next version of a workbook (D82–D85, D104, D105; J35). A file uploaded to a
  stored import profile is profiled and checked by a job of kind `profileCheck`, writing nothing:
  columns new, missing and renamed (same position, at least half the values shared), the profile
  against the active release, the dry run of the file through the profile as it would read it, new
  values of match columns, name drift and records missing from the file
  (`GET /import-profiles/{key}/check`, its `new-values`, `drift`, `missing-records` and `rows`;
  `POST …/check` checks again). A source's `missing` (`report`, `delete`): records no row names are
  counted by every binding and the dry run, and deleted only into a change set, each with its own
  relationships (`422 MISSING_DELETE_NEEDS_CHANGE_SET` live); the kind `setMissing`.
  **Settings › Data operations › Import profiles** lists the profiles; a profile's page uploads the next
  version, shows the check (Accept a rename, Ignore a new column, keep or delete missing records)
  and loads into a change set whose review holds only the differences. The editor's Load dialog and
  the profile's share their parts (`ChangeSetLoad`). `test:browser:authoring-a5`'s A5c walk.
  Revised the same day after the user's run on the development server: Import profiles is a catalogue
  beside the selected profile, as Workspaces and Webhooks; a profile's answer carries `lastLoad`
  (the latest import naming it and whether its change set is open, published or discarded), shown
  in the catalogue and on the profile's page, where a profile loaded from the editor read "no file
  uploaded"; the record page's breadcrumbs became `ui/Breadcrumbs`, which a job's page uses too
  (Jobs › the job). A settings group **Data operations** holds Import profiles (at
  `/settings/import-profiles`; the old `/settings/imports` still opens it) and Jobs (renamed from Jobs
  and feed; the change feed's retention moved to Consumer APIs), ahead of Integration.

- Base 0.10 A6b: the editor filled by the inference (D94; J34.4, J34.6, J34.8). New from a workbook
  asks what to propose (a new application with its name, additions to the model, or nothing) and the
  workspace the columns are compared with; once the workbook is profiled the editor proposes and
  applies the proposals, one step each, and shows the sheet's type. What is still as proposed reads
  **Proposed** in the model and source panes (a tone of its own) and its centre says **Proposed
  because**, with its evidence and its alternatives as steps; History names each proposal; ⋯ ›
  **Propose again…**; disagreements are Issues with Go to column. Map to… reads a column as a related
  record matched by a unique attribute, or as a value of a related record under its parent; a
  column's centre lists its most frequent values. `test:browser:authoring-a6`.
- Base 0.10 A6a: inference over the table patterns (D86–D98; J34.4–J34.6), through the API.
  `POST /model-drafts/{id}/inference` runs a job of kind `inference` over the draft's source file in
  new-application or extend mode; `GET …/inference` reads its counts, disagreements, warnings and
  the elements still as proposed; `GET …/inference/proposals` lists each proposal with its pattern,
  columns, one-sentence summary, evidence, operations, alternatives and requirements; and
  `POST …/inference/application` writes the open proposals into the draft, one history step each,
  with one dry run after the last. The patterns: a sheet's key and name, a repeated parent with the
  columns constant within it, level columns, a code and name pair with its name drift, flag columns
  with a multi-valued column beside them, multi-valued cells, text lookups with their placeholders,
  references to another sheet, translations by row and by column, GUID columns, every other column
  as an attribute, and a navigation group of a sheet's lists (raising the schema language to 0.10
  when needed). Columns of several sheets with one header and type share an attribute type. Extend
  mode maps sheets, columns and lookups onto the draft's existing types, attributes and records
  first. Proposing again recognises its earlier proposals: what is still the engine's follows a
  newer workbook, what the administrator changed is kept and a column read otherwise is reported
  (`INFERENCE_DISAGREES` also among the profile's warnings); an undone proposal is not applied again.
  W1 goes from upload to a published change set by applying its proposals. The optional assistant
  is an interface only (`INFERENCE_ASSISTANT`, `INFERENCE_ASSISTANT_ROWS`), off by default.
- Base 0.10 A6a: `missing: "create"` on a flag set and on a related record's `parent`, and a
  `record: "existing"` row finding the record another source of the same file creates (D93); the
  kind `unmapColumn`, and `addValuesToList` on flag columns and related records; a profiled column's
  most frequent `values`.

- Base 0.10 A5a: a model draft's import profile, edited by operations (D74–D80; J34.2, J34.7,
  J34.8), through the API. A draft holds one profile, read by `GET /model-drafts/{id}/profile`
  with the import profile it stands for and its warnings against the draft's model. Eleven source
  and mapping kinds on `POST /model-drafts/{id}/operations` edit it (`setProfile`, `addSource`,
  `setSource`, `removeSource`, `ignoreSheet`, `mapColumn`, `setColumnReading`, `splitColumn`,
  `ignoreColumn`, `addValuesToList`, `setValueMap`), each one history step undone exactly. The model
  kinds carry the profile with them: a key change rewrites it, a moved attribute's column moves to
  the target type's source on the same sheet, a split starts a source of the new type joined by the
  split's relation, a merge re-points the merged type's sources, an attribute turned into a list
  type becomes a lookup creating its values, and what a removal takes away is kept as an unmapped
  column with a `COLUMN_UNMAPPED` warning. A step that can change what the load writes queues the
  draft's dry run with its profile (`dryRun` in the answer; not after labels, the release identity,
  layout, navigation or consumer API steps). Installing the draft saves its profile as the instance
  profile of its key, checked against the new release (`importProfile` in the answer).
- Base 0.10 A5a: `missing: "create"` on an import profile's `parent` and `relation` bindings matched
  by name: a cell naming no record creates one by its name, once per value per load, before the
  records naming it (D77); `CREATE_NEEDS_NAME_MATCH` refuses it with any other match.

- Base 0.10 A3: source files, their profiles and the dry run (D65–D71; J34.1, J34.3), through the
  API. `POST /source-files` keeps an XLSX or CSV file for a model draft or an import profile (in
  `JOB_FILE_DIR` as `{id}.upload`, under `IMPORT_MAX_BYTES`, deleted with its owner; an upload
  supersedes the owner's earlier file, deleted `JOB_RETENTION_DAYS` later) and queues a `profile`
  job, which stages every filled cell in PostgreSQL once and profiles it with set statements:
  `GET /source-files/{id}/profile/sheets` lists each sheet's blocks with their header rows (D68),
  `…/sheets/{sheet}/columns` each column's filled and distinct counts, value types, candidate key,
  delimiters, placeholders (D70) and overlaps with other columns and, in a named workspace, with the
  model's record names and unique text attributes (D69). `POST /model-drafts/{id}/dry-run` runs the
  import preview of the draft's file through an inline profile (D65) against the draft's compiled
  model, binding the staged cells (D66), over every item (D67), as a `dryRun` job that writes
  nothing; `GET …/dry-run` reads its summary per source with the difference from the previous one,
  `GET …/dry-run/rows` the rows behind a figure (`source`, `status`, `code`). A dry run of a draft
  changed since is cancelled, as is a running one when another is sent; a draft that does not
  compile is refused `422 INVALID_MODEL` (D71). `POST /imports` takes `sourceFileId` in place of the
  file part. The synthetic workbooks W1, W1′, W2 and W3 are generated by `tests/workbooks.py`.

- Base 0.10 A5b: the model editor with a workbook (D81, D84; J34.1–J34.3, J34.7, J34.8). **New from
  a workbook** on Settings › Model creates a draft with the workbook and opens it; an open draft takes
  one, or a newer one, from its ⋯ menu. A **source pane** left of the model pane shows the sheets as
  tabs and each column with its status and statistics; a selected column shows its mapping in the
  centre (what it feeds, its reading, match, split, created values, value map, key, refused rows and
  statistics), and the type it feeds is marked in the model pane. **Map to…** (from the column, by
  Shift+F10, or by dragging the column onto a type) maps a column to a name, an attribute or a new
  one, the parent, a related record or a flag of a relation, or ignores it, starting the sheet's
  source where needed, in one step. A value map starts from the column's placeholders. The drawer
  gains a **Dry run** tab with each figure and what it was, opening the rows behind it; the Issues
  tab lists the profile's warnings. **Load into a change set…** installs and activates the draft
  when its model changed (installing an unchanged one only saves the profile), opens a change set
  named after the file, loads the stored file through the saved profile and opens the review.
  `test:browser:authoring-a5` walks it on both designer models.

### Changed

- Base 0.10 A5c (D105): a relation column onto a relation its record holds one of (many-to-one from
  its side, or one-to-one) is mapped with `replace: true` by the mapping kinds, Map to… and the
  inference, so the next version's changed value switches the record instead of being refused
  `CARDINALITY_VIOLATION`. The dry run's summary counts `deleted` records and `missingRecords`; the
  binding report `missingRecords`.

- Base 0.10 A6b: an operation of a proposal holds when the binding has what it sets, so proposing
  again no longer re-applies a binding a value map was added to (found by the browser runner: the
  name drift's map was dropped and the dry run refused the drifting rows). The editor's marks name
  the proposal that created an element, not the last one naming it. Add a workbook and New from a
  workbook share one workspace field (`WorkspaceField`); a dialog lays two short fields side by side
  (`dialog-pair`); the model pane scrolls a selection made elsewhere into view.
- Base 0.10 A6a: profiling analyzes the staged cells once they are copied in, so the statements over
  them are planned for their real size: the inference of W1 at 10,000 rows took 54.6 s before and
  0.35 s after (profiling unchanged at 6 s). The step answer of the operation, undo, redo and
  application routes is one function (`management/steps.py`).
- Base 0.10 A5b: the editor keeps the selected element selected after a step that changes its key
  (the address used to keep the old key, and the centre lost it). The target list of Move to… is
  shared with Map to… (`TargetList`), the install dialog's release identity with the load
  (`ReleaseIdentityFields`), and the import job's rows table with the dry run's (`JobRowsTable`).
- Base 0.10 A3: D9's interactive dry-run budget (1 s for 10,000 rows, a sample above it) is replaced
  by D67, at the user's decision: every dry run checks the whole file. Measured once: profiling W1 at
  10,000 rows takes 6.3 s, its dry run about 7 s (19,453 items) after the fix and A3a below.
- Base 0.10 A3a: a trial run (an import's or a batch's preview, a dry run) records no audit entry and
  takes no feed position (D72), and relation sets advance in one array statement per thousand sets
  for every write (D73); the trial run of a 10,000-row workbook takes 5.75 s instead of 11.8 s, and
  holds the workspace's write lock that much shorter.

### Fixed

- Base 0.10 A6 (found by A8b's case 10): an element the administrator created again exactly as a
  proposal had made it (a list removed and loaded again) read as still proposed, and was marked
  Proposed and followed by Propose again. A step other than a proposal's that creates an element
  after its proposal now makes it the administrator's, as D92 says. Regression:
  `test_a_rectangle_is_read_as_a_list_on_request` (J34.10, seen failing without the fix).

- Base 0.10 A5, A6 (found by A8a's sample-file smoke): a column whose header begins or ends with a
  space could not be mapped in a draft (`unknownElement`), since the draft's sheets kept the spaces
  the import trims. The draft's sheets name a column as the import reads it.
- Base 0.10 A6 extend mode (found by A7's browser runner): a workbook the editor uploads names no
  workspace, and its columns were then compared with no records, so additions to the model matched
  nothing by value from the editor. A file without a workspace is compared with the default
  workspace's records, as its profile job already ran there.

- Import binding (0.9 J2, found by 0.10 A5c's 10,000-row measurement): finding each row's record by
  its key attribute, and a match by attribute, compared every row with every record of the context
  (21.9 s for 10,000 rows into a workspace holding them); they now join on a table of the values a
  key or a match reads, a hash join (the whole binding of W1′ at 10,000 rows: 2.4 s).

- Base 0.10 A6b (reported on a workbook): a workbook with nothing to propose got the new
  application alone, which left the draft refusing an application without types; now nothing is
  proposed and the inference says why. Load into a change set and Install and activate on a draft that
  does not compile blanked the page (its compilation has no changes); both now say the draft has
  errors, and Load says when nothing is mapped yet. A sheet with a note or small block beside its
  table is now read by its table. A page part failing while rendering shows what failed and a reload
  under the top bar instead of an empty page.
- Base 0.10 A6b, on workbooks (D99–D103): the proposed model no longer refuses rows
  of its own workbook. A type gets one parent (a further repeated column is a list it refers to),
  optional where rows leave it empty (`setContainment`'s `parent.optional`), and a source reads no
  record from a row holding nothing in its columns. Lists of a GUID and a name are proposed;
  translations are found by their values whatever their headers; a sheet's yes/no columns form one
  set; descriptions in sentences are long text, never a parent; names are written as words, a type
  named after its key column. A second column with an earlier column's header is left out with a
  warning.
- Base 0.10 A6b: New from a workbook offers **A new model**: the workbook's application in a draft
  that starts empty, without the active model's applications ("A new application" adds it to the
  model the draft starts from).
- Base 0.10 A6b: compiling a draft that does not compile sends `changes` empty instead of leaving it
  out, so the answer matches its type in clients and their test fakes. Browser runners fail on any
  uncaught page error or a page part the error boundary replaced, in every page a run opens.

- Binding an import whose profile has a relationship column grew with rows times links: the record
  items looked up each row's required links in a subquery run per row. They are collected once with
  a grouped join; a 10,000-row file binds in 1.4 s instead of 9.3 s.
- `GET /jobs/{id}/rows` serves a dry run's rows too and takes `source` and `code` internally for the
  dry-run rows route; the job list's `kind` filter takes `profile` and `dryRun`.

## [0.10.0-alpha.1] - 2026-10-12

The model designer, released on its own (D14): everything since 0.9.0, Base 0.10 packages A0, N1,
A2, A4a, A4b, A4c and the designer checkpoint T1. Schema language 0.10. The spreadsheet onboarding
line (A3, A5–A8) follows in 0.10.0. One migration since 0.9.0 (`20261011_01`, the draft operation
history); a database of 0.9.0 upgrades on start.

### Added

- Base 0.10 A0 (design, no product code): decisions D1–D10, D17–D21 and A-D5–A-D9 accepted;
  the model authoring API designed in API.md (draft operations and their kinds, history, undo and
  redo, source files and their profiles, the dry-run summary, inferences); ADR-041, model drafts
  change through recorded operations; journeys J33–J35 and their planned routes in the API
  inventory; the synthetic workbooks W1–W3 defined in test terms; the editor mock-up and the W1
  sample approved.
- Base 0.10 N1: schema language 0.10, opened with navigation groups (D1, D22–D27; J33.9). An
  application may declare `navigation.groups` (key, label, collections, `collapsed`); the sidebar
  shows the collections in no group first, then each group as a foldable section whose fold a
  reader's browser remembers, marks a folded group holding the open collection, and opens a group's
  page (`/apps/{app}/groups/{group}`) listing its collections with a search by name. A group naming
  no collection of its application (`INVALID_REFERENCE`), a collection in two groups
  (`INVALID_MODEL`), a group key twice (`DUPLICATE_KEY`) and `navigation` below schema 0.10
  (`INVALID_MODEL`) are refused at their pointers; a 0.9 model is unchanged, with the same hash. The
  browser runner `test:browser:authoring-n1`.
- Base 0.10 N1, at the user's request: on a phone (below 760px) the data-context band is one line
  whose workspace, application (with its tile) and data context (Live, change sets, publications,
  with the line saying what an edit does) each open their choice; the top bar shows no application
  tabs in any area and the drawer no workspace selector. A group page's rows show a chevron and a
  pressed state.
- Base 0.10 A2: model drafts change through recorded operations (ADR-041, D29–D35; J33.1–J33.8,
  J33.12, J08.9). `POST /model-drafts/{id}/operations` applies a request of typed operations all or
  none at `expectedVersion` as one step of the draft's history, answering the new version, the
  entries with their inverses and the compiler's diagnostics (a draft may be invalid between steps).
  34 model-side kinds: names and keys (every reference rewritten; an element a consumer API names is
  refused, D29), the release identity and schema version, applications, object types (with a
  generated table view and detail page, containment by `parent`, D30), split, merge and conversion to
  a list type, attribute types and bindings, relation types and the relations allowed between types,
  views, panels and their lists, navigation groups. A removal takes what exists only for the removed
  element (D31). `GET …/operations` pages the history; `POST …/undo` (a step, or `steps` together)
  and `POST …/redo` apply stored inverses as new steps (D32); a step later steps build on is refused
  `OPERATION_HAS_DEPENDANTS`. A draft-only change of an element of the draft's base release is
  refused `OPERATION_REQUIRES_MIGRATION` with the records, values and relationships it would touch,
  live and in change sets (D33). A whole-model `PATCH` is recorded as one `replaceModel` step;
  installation makes the installed release the draft's base, leaving its version (D17, D34). New
  codes `INVALID_OPERATION`, `OPERATION_REQUIRES_MIGRATION`, `OPERATION_HAS_DEPENDANTS`,
  `NOTHING_TO_UNDO`, `NOTHING_TO_REDO`, `OPERATION_BATCH_TOO_LARGE`; setting
  `MODEL_OPERATION_MAX_ITEMS` (500); migration `20261011_01` (`model_draft_operations`).
- Base 0.10 A4a: the model editor's model pane (D36–D42; J33 in the browser). A draft opens in the
  editor from Settings › Model (**Open in editor**; **New draft** opens it too), full width under
  the top bar: the model pane (applications with their types in their containment tree, navigation
  groups, relation types, attribute types, each marked new, changed or released), the selected
  element with its operations, the relationship matrix, the issues linked to their elements and the
  history in plain words with undo and redo. Every model-side operation is in a menu, through one
  dialog; Move to… moves an attribute or a type, and a drag in the model pane opens it with its
  target. A released element's draft-only change is refused with what it would affect; a step on a
  draft another editor moved on is held and offered again. Install and activate in one confirmed
  step, with the proposed version, the differences and the compatibility. On a phone the panes are
  tabs. `GET /model-drafts/{id}/outline` serves the draft's structure, the marks against the base
  release and the diagnostics with their elements. **New draft** from an empty model now starts a
  document of the newest schema language with a release identity, instead of `{}`. The browser
  runner `test:browser:authoring-a4a`.
- Base 0.10 A4b: the preview and layout editing (D43–D50; J33.10). **Preview** in a type's header
  shows its record page and table in the editor's centre, drawn by the record screen's own renderers
  from the draft before it is installed, over a record read live in a workspace and record chosen in
  the band (or an empty record for a new type); the page's controls are shown and disabled, and
  nothing the preview shows writes. **Edit layout** opens the layout editor over the whole editor,
  marked by its own band with Undo, Redo and **Back to the model editor**: panels moved within and
  between `main` and `side`, hidden or shown, renamed, their columns and sort; fields moved, grouped
  into new field groups and added; a table view's columns, filters and default sort; by menu and
  keyboard, or by dragging with mouse or pen. Each change is one step of the draft. A draft that does
  not compile is not previewed. `GET /model-drafts/{id}/model` answers a draft compiled as
  `GET /model` serves the active model, with its placements; the operations `addDetailPage` and
  `removeDetailPage` give a type without a declared detail page the page a new type gets. The
  browser runner `test:browser:authoring-a4b`.
- Base 0.10 A4c: the consumer API editor (D51–D59; J33.13, J33.14). The editor's left pane has
  **Model** and **Consumer APIs** tabs, ＋ adding within the open one. A consumer API opens with its
  tabs: the exposed types and public names and the related records it serves; its fields with their
  sources (chosen in order from a picklist of what the exposed types and the types above them hold),
  role and default, edited in place (no field name is typed by hand anywhere in the tab: match
  fields, related fields, XREF fields, sort fields, routes and watched outputs are chosen from what
  is valid there); the operations it offers, its lists, XREF match rules
  and custom events; its filters; and two documents with Copy and Download, the **Schema** of the
  message consumers receive and a **Message example**. Six operation kinds change definitions, each
  step with undo: `addConsumerApi` (a starting definition from the exposed types), `removeConsumerApi`
  and four part verbs naming a part by a JSON pointer (`setConsumerApiPart`,
  `insertConsumerApiPart`, `moveConsumerApiPart`, `removeConsumerApiPart`). The outline lists each
  definition with its contract against the active release, shown as "Needs v2" with a step that raises
  the version; the install dialog lists each consumer API's result and activates only when none needs
  a higher version. `GET /model-drafts/{id}/consumer-apis/{consumerApi}` and its `schema.json`,
  `example.json` and `openapi.json` serve a draft's definition and documents before it is installed.
  `setKey` on an element a consumer API names now rewrites the definition instead of refusing (D54,
  replacing A2's D29). Switching XREF off asks first, since its match rules go with it, and stops
  Resolve too. The browser runner `test:browser:authoring-a4c`.
- Base 0.10 T1, the designer checkpoint (D60–D64): US-P05 walked end to end in the browser on both
  designer models by `test:browser:authoring-t1`. An application designed from an empty draft, and
  the active model extended with a consumer API change that needs a higher contract version, are
  each installed, used on the record screen and served by the consumer tier. Each walk is taken once
  by keyboard alone and once by clicking every button. Each step is checked on the server, and the
  run fails on a console error or a failed request. The designer's surfaces (the editor, the matrix,
  its dialogs, history and install dialog, the preview and layout editor, a consumer API's fields and
  schema, the sidebar's groups, a group page, and the phone band, drawer and editor tabs) join the
  accessibility gate in light and dark and the visual gate.

### Fixed

- After a model draft was installed, the editor marked everything the draft had added, and the
  types and applications around it, as changed against the release just installed from it. The
  release holds each element with its defaults written out, and the outline compared it with the
  draft's authored form; marks now compare both in the release's form (0.10 T1, from A4a).
- The preview of a new type's empty record asked the server for the history of a record that does
  not exist (a 404 in the browser); the record page's History panel now reads through the page's
  client, which answers the preview's empty record itself (0.10 T1, from A4b).
- Every dialog's labelled fields: a label stood further from its own control than from the field
  before it; the label now sits right above its control with a clear step to the next field, and a
  dialog's buttons keep a margin from its bottom edge (0.10 A4a).
- `setRelationRule` refused a change of which records a released relationship may choose
  (`candidates`) as needing a migration; it is compatible (0.9 K7) and now applies (0.10 A4a).
- The model editor can remove a relation type that type pairs still use: the pairs and the type go
  in one step (0.10 A4a); every relation, a parent link included, has Remove relation in its menu.
- A relation allowed on a model draft joined a relations panel set up for other records (a
  translations panel sorted by its language) and made the draft invalid; it now joins only a plain
  relations panel or gets its own (0.10 A4a, A2's generated layout).
- Every table's cut-off cell shows its whole value, wrapped, on hover, focus or a long press (0.10
  A4a).
- Every menu (`⋯` and the like): items show hover, may carry a glyph, a second line and a section
  heading (0.10 A4a).
- Supported schema versions are listed oldest first by number (`0.10` after `0.9`), in
  `GET /system`'s `schemaLanguages`, a refusal's `supportedSchemaVersions` and the startup and
  upgrade messages; a text sort would have put `0.10` first (0.10 N1).

## [0.9.0] - 2026-10-11

Base 0.9, integration-grade APIs, and its schema language 0.9. Build acceptance (R) reviewed every
change since 0.8.0 and ran every gate; its fixes are under Fixed (R-F1–R-F28).

### Added

- Base 0.9 J6a: workbooks people fill in (D191–D199; J27.18–J27.21). `people.ownedColumns` lays an
  owned relationship out as a row per record and a column per parent and field (parents holding
  records plus those added; headers naming the parent and the ancestor the records are unique
  within); a filled cell creates the record under its parent, owned by its row's record, an edited
  one updates it under a version claim. Cells naming one record offer an Excel list from a reference
  sheet of the records the relationship may choose (`people.referenceLists`); every cell has a
  border. Import profiles gain `relatedRecord.versionColumn`. The Export dialog's Advanced offers
  Rows or Columns per parent, the parents to add and the fields, and the lists. Browser runner
  `test:browser:j6a`.
- Base 0.9 J6: a workbook for people (D179–D190; J27.15–J27.17). `POST /exports` takes
  `layout: "people"` with `people` (`columns`, `sheets`, `columnFields`) for one type as XLSX: the
  table's columns and labels, typed cells, relation columns as "; " lists of names or a field,
  hidden ID and version, a sheet per chosen relationship (owned records, or relationships with their
  values), the type hues, a frozen, filtered header, and the import profile that reads it on a hidden
  sheet; `422 INVALID_EXPORT_LAYOUT` otherwise. An XLSX imported without a profile is read through
  the profile it carries (`parameters.profile.embedded`). Import profiles gain `key.versionColumn`,
  `key.nameColumn` and a relation binding's `idColumn`, `versionColumn` and `attributes`. The Export
  dialog offers For people with an Advanced section; the import page names the workbook; the job
  reads "Workbook for people". Browser runner `test:browser:j6`.
- Base 0.9 K7: which records a relationship may choose (D168–D178; J13.9, J13.10, J03.9, J10.11,
  J01.11). A binding may carry `candidates`, criteria for the records at its `from` end, its `to`
  end or both, over their name, any non-JSON attribute, and an ancestor's name or attribute
  (`ancestor:<type>.<field>`), with the list filter's operators. Every picker for the relationship
  offers only those and says so; a record that does not meet its own end is not offered the
  relationship, with the reason. The per-type list takes `candidateFor` with `anchorTypeKey`; the
  relationship view's and matrix's candidates apply the criteria. A new relationship outside them is
  refused with `422 RELATION_CANDIDATE_REFUSED` on every write path (batches check a chunk's targets
  in one statement per restricted end); relationships made before are kept. The model-aware query
  takes `ancestor:<type>.<field>` criteria. Browser runner `test:browser:k7`.
- Base 0.9 K6a: `GET /relations/held`, the records a set of records holds through one relationship,
  each with how many of them hold it (D165; J32.7), which Change relationships' Remove lists.
- Base 0.9 K6: filtering a list by its records' relationships (D153–D159; J01.10, J32.6, J27.6,
  J08.12). A table view's `filterFields` may name `related:<key>`; its Filter menu then keeps the
  records related to any of chosen records (picked with the record search), to none or to any, the
  chip naming the records, also after a reload. The per-type list takes
  `filter.related:<key>.eq=<record ID>` (repeatable) and `.isNull=true|false` for any relationship
  the type has, built by Q3's relationship hop in every context; `INVALID_FILTER` otherwise. The
  selection's "all matching", the bulk actions and Export carry it. The starter is content release
  0.9.5 with these filters on system values and master values. Browser runner `test:browser:k6`.

### Fixed

Found by the 0.9 release review (R step 0, D200):

- A workspace deleted and created again under its key could never be written: its old feed entries
  kept their positions. Deleting a workspace now takes its feed with it: its audit entries stay
  as history without a feed position, and its idempotency keys go (R-F1, D208).
- Activating a release could deadlock with a webhook delivery, a subscription change, or a write of
  an attribute whose `unique` the release changes. Activation now locks the active subscriptions,
  and when `unique` changes the unique values, before the runtime state (R-F2, R-F3).
- A relationship's candidate criteria (K7) treated a record a batch had just created without a value
  as meeting `isNull: false` (R-F4).
- An import column with `replace: true` whose cell was empty left the relationships in place; the
  set is now replaced with none, as in a workbook for people whose relation cell is emptied (R-F5).
- A filter on `createdAt`, `updatedAt` or a date-time attribute takes a day (`YYYY-MM-DD`), compared
  by the whole day in UTC; the collection's date filter sent one and was refused (R-F6).
- A workbook for people whose type or relationship name held `&` or `<` was reported damaged by
  Excel: the list rules are now escaped (R-F7).
- A webhook's `stateAt` and its object are read in one snapshot, as the pull feed reads them (R-F8).
- A preview past its retention was confirmed until the hourly sweep marked it; it is now refused
  `410 JOB_EXPIRED`, and the sweep skips a job a confirmation holds (R-F9).
- A file sweep could remove an import's file before its job was committed; a file of no job is
  kept for ten minutes (R-F10).
- One workspace whose events cannot be derived no longer holds up the others (R-F11).
- An atomic job's chunk, a preview and an export's set statements renew the job's lease while they
  run, so a second process never takes a running job (R-F12).
- The pull feed's `ETag` changes with live data as well as with derived events (R-F13).
- Three route descriptions named error codes in lower case (R-F14).
- An `ancestor:<type>.<field>` value shows the ancestor of that type nearest the root everywhere:
  the workbook for people and consumer API projections now agree with lists and Q3 (R-F15, R-F16,
  D209).
- New webhook offered only the first 100 active workspaces (R-F19).
- Three colours were written outside the tokens, skipping the dark theme's shadows (R-F20).
- Each consumer API's document states the engine's own read limits rather than copies (R-F21).

Found by the 0.9 release's browser runners (R step 3):

- In a relation matrix cell, Create pressed before the cell's containers had loaded did nothing and
  said nothing: once a single container loaded, the notice that none was chosen was not shown. The
  button now waits for the containers (R-F22).

Found by the 0.9 release's deletion timing (R step 8, D124):

- Deleting a large selection, about 100,000 records, could not finish: three statements stopped
  scaling once a run's IDs no longer fit in PostgreSQL's `work_mem`. The run's relationships are
  found through its joins, not `IN (run) OR IN (run)` (R-F23); a change set's matrix walk leaves
  out the rows the change set replaces with `NOT EXISTS`, not `NOT IN` (R-F25); and reading the
  records of a change set takes any number of IDs, a statement at a time, where more than about
  32,000 failed with "number of parameters must be between 0 and 65535" (R-F24). In a change set
  the closure's walk finds a record's required owned records by their keys, where it read every
  record of their type for each record reached (R-F26), and the matrix states' upkeep no longer
  walks the cells under the records the change set just deleted (R-F27). Deleting 100,000 records
  now previews in 49 s live and in a change set, and runs in a change set in 51 s.
- A query's or a list's expansion in a publication counted its total once per row of its page:
  20,000 related records expanded took 103 ms, now 68 ms (R-F28).
- A filter or sort naming an attribute the type does not bind answered `invalid_filter` and
  `invalid_sort` in lower case; they are `INVALID_FILTER` and `INVALID_SORT` (found in 0.9 K6).
- An export with a `related` criterion failed in the worker (`INVALID_QUERY`, "A related criterion
  names no field, operator or value"): the stored request carries every field, null ones too, and
  the check counted a null value as named. It now checks values (found in 0.9 K6).

### Changed

- The record tree's leftovers from UA9's flat scrolling are removed: the windowed version kept in
  comments, the unused wheel routing (`useTreeWheel`, `treeWheel`) and the group frame's glow
  (R-F17). Documentation and comments name no example-model content (R-F18, D210).
- 0.9 R: the accessibility and visual gates cover every 0.9 surface approved by screenshot (D202),
  light and dark, on a harness of their own with webhooks on: Settings › Integration, a webhook's
  configuration and deliveries, relation columns, the filter editor, the selection bar, the three
  bulk dialogs, exporting and importing with their notifications and job pages (36 new baselines).
  34 baselines were re-recorded for changes delivered since UA7 (UA8, UA9, K1, K6a, J1u, J4, U4,
  U5). The browser runners that had drifted from later packages were brought up to date, and the
  comprehensive command set names all 38. `volume_baseline.py --only-deletion` times deleting about
  100,000 records (D124).
- Schema 0.9 is the released schema language from 0.9.0 (D206): APPLICATION_MODEL describes it as
  such, with what it adds to 0.8 and how a 0.8 document using it is refused.

- Base 0.9 K6a: collection filters redesigned (D160–D164): active filters as pills, ＋ Filter's field
  menu, one compact editor per field type, a bottom sheet with "Show N records" on phones. The
  selection bar's actions are icon buttons with an indigo tint on the light theme, and Change values
  and Change relationships were redesigned (D166, D167): Change values as cards per field, Change
  relationships with pills, a segmented action and a checklist whose Remove lists only what the
  selection holds. D133 revised by D167: Add and Remove are separate actions.
- D142 revised (0.9 K6a): the per-type list's `expand` takes as many keys as the type has
  relationships, each once; the fixed maximum of 5 is gone.
- Base 0.9 K5b: a relation column shows as many related records as its width holds (D143 revised by
  the user): whole chips, then "+N more" for the rest, and no "+N more" when they all fit; resizing a
  column shows more or fewer at once without reading the list again. Lists ask for up to 20 related
  records per row (`expandLimit=20`); a 20-row page costs 11–34 ms on the 0.1 volume fixture.

### Added

- Base 0.9 K5a: a field of the related records in a relation column (D148–D152; J01.9, J08.12).
  `related:<key>.<field>` shows each related record's value of a field instead of its name: `name`,
  an attribute the types at the other end bind, or `ancestor:<type>.<field>`, written as in a
  consumer API definition ("Has translation · Language code": `ar` `cs` `en` +4 more). A record
  without a value shows "—"; such a column never sorts. `expand` takes the same text; the entry names
  its `field` and each record carries the value beside its name (`INVALID_EXPAND` for a field that
  does not resolve). Q3's answers are unchanged.

- Base 0.9 K5: relation columns (D140–D147; J01.8, J08.12). A table view's columns, and a children
  or table panel's, may name `related:<key>` in schema 0.9, `<key>` a relation type's key (read
  outgoing) or reverse key (read incoming): each row shows its first three related records as chips
  in name order, then "+N more", kept on one line; a column hidden in the table's display settings is
  not read. Where a row holds at most one (one binding, whose listed end holds one), the column sorts
  by the related name, rows without one last; elsewhere it is refused in `sortFields`, and it is never
  a filter. `GET /objects/{objectTypeKey}` takes `expand` (repeatable, at most 5) and `expandLimit`
  (1–20, default 3), answering each item's `expanded` in Q3's shape, `422 INVALID_EXPAND` otherwise,
  and `sort=related:<key>`; the list's response is now `TypedObjectPage` (`QueryObject` items). The
  starter is content release 0.9.4 with relation columns on system values and master values. Q3's
  expansions read a page in one `LATERAL` statement per expansion (a page of 100 with two keys: 45 ms
  live, was 611 ms). Browser runner `test:browser:k5`.

- Base 0.9 UA9: the record tree scrolled as one list, several records selected and moved together
  (U-D21–U-D28; J14.9). The sidebar's tree and the hierarchy lens scroll with the sidebar or the
  page, their type groups start folded and open like records, and a long group reads more as its
  end comes into view (**Show earlier records** above a group opened partway down; Ctrl+Home and
  Ctrl+End within a group). Records are selected with Cmd/Ctrl, Shift, Ctrl+Space and Shift+arrows,
  without changing the page, and dragged together onto a new parent, in the sidebar as well as the
  lens, or moved with **Move to…**: one confirmation, one atomic batch (`update` items with `parent`
  and each record's version, live or in the change set). A target that cannot take one refuses them
  all, naming it; several records are never moved where their type would change. Browser runner
  `test:browser:ua9`.

- Base 0.9 UA8: actions in place on the record (U-D15–U-D20; J02.6). A record's header edits its
  title (usually the name) and subtitle in place, as its details fields are, on the full page and in
  the inspector, and offers Add for an empty subtitle; one component, `EditableField`, draws and
  edits a field in both places. The header's Edit record button is gone; **Edit record** (was Edit
  all fields) is the first item of the record's ⋯ menu, also on every collection row. A relationship
  row's actions are icon buttons with tooltips (change to another record, edit values, delete,
  `ui/IconButton`), and a row managed through the parent or required shows a lock with the reason.
  Browser runner `test:browser:ua8`.

- Base 0.9 K3a: many-to-one relationships (D136–D139; J08.11, J11.12, J32.5). A binding may declare
  `"cardinality": "many-to-one"` in schema 0.9: each `from` record holds at most one relationship of
  it, and a `to` record serves any number. A second one is `409 CARDINALITY_VIOLATION` on every write
  path; a release tightening a binding to it needs a migration while a `from` record holds more than
  one (`RELATION_CARDINALITY_VIOLATED` at the binding's `cardinality`, with the count). It cannot be
  `required` (D137, in TODO), and is refused in schema 0.8. Which end holds one is one rule in the
  engine and one in the browser (D138); the relation matrix, the mapping grid's candidates and the
  consumer API read it, so a field `via` a many-to-one binding answers one object or `null`. On a
  record, where it may hold only one relationship of a kind, its Relationships panel offers **Set**
  while it holds none and **Change** and **Delete** on the one it holds (D139); Change replaces it in
  one write through the mapping replacement, claiming the set as read, and is refused if the
  relationship changed after the list was read. The selection's Change relationships… offers Set to
  and Clear from that side. The example model 0.9.1 uses it (its `rdm` consumer API at contract
  version 2).

- Base 0.9 K3: changing the relationships of a selection, and relationships named by their ends
  (D127–D135; J11.10, J11.11, J32.4). A batch item **`ensureNoRelation`** (`relationTypeKey`,
  `from`, `to`, optional `expectedVersion`) deletes the relationship of that type joining the two
  records as `DELETE /relations/{id}` does, with its refusals, or answers `unchanged` when there is
  none, so a removal sent again changes nothing (D129). A `replaceRelationSet` in a preview needs no
  `expectedRelationSetVersion`: its outcome names the version it found
  (`previousRelationSetVersion`, also in its refusals' details), and confirming carries it into the
  stored item, so execution refuses `RELATION_SET_VERSION_CONFLICT` only the sets changed since the
  preview (D130). In the browser, **Change relationships…** in the selection bar offers every
  relationship the model allows the type, in both directions, except containment and required
  ownership (D127), with the actions its cardinality allows: Add and Remove together, Replace with,
  Set to, Clear; never Remove or Clear on a required one (D128, D133). The other records are chosen
  with the record picker (`ui/RecordListField`); the dialog states how many changes the selection
  makes and explains a change over `BACKGROUND_JOB_MAX_ITEMS`, or a replacement over
  `JOB_PREVIEW_MAX_ITEMS`, before sending (D131, D134); relationship values are not edited (D132,
  after 1.0 in TODO). A batch's job page says relationship outcomes in a relationship's words.
  Relation columns in collections are K5 (D135).

- Base 0.9 K2b: deleting a selection, and cascading batch delete items (D120–D126; J11.6, J32.3;
  PG-D18). A `delete` item takes `cascade` and `deletionPreviewToken` as the single `DELETE` does:
  without `cascade` a record with dependants is refused `OBJECT_HAS_DEPENDANTS` with its `impact`;
  with it the item deletes the record with its dependants under the impact its token confirms. A
  batch preview gives each delete item's `impact` (records by type, relationships, those reaching
  records that stay, and the token) and the preview's `deletion` totals; confirming carries each
  token into the stored item, so execution deletes exactly what was previewed and refuses only an
  item whose impact changed (`DELETION_PREVIEW_CHANGED`). Items are decided in order: a record an
  earlier item of the job deleted answers `unchanged` with `deletedWithItem` (D122). Deletion is one
  path for the single `DELETE` and a batch's delete items, live and in a change set, as set
  statements in PostgreSQL whatever the impact's size or depth (D123); its token is the same from
  either. In the browser, **Delete…** in the selection bar previews what deleting removes (the
  selected records, those going with them by type, the relationships) before a destructive
  **Delete N records** naming the whole (D126); the deleted records leave the selection, the refused
  ones stay for Preview again, all matching is cleared (D125). A batch's job page shows what
  deleting removes and each delete's impact.

- Base 0.9 K2: changing values of a selection, and previewing a batch (D112–D119). `POST /batches`
  takes `stage: "preview"` for a background batch (inline is refused): its items run without
  writing anything, as an import's preview runs, and the job waits in `awaiting_confirmation` with
  `preview` (no `rows`); `POST /jobs/{id}/confirm` runs the stored items as an execution, which is
  authoritative. In the browser, **Change values…** in the selection bar sets or clears fields of
  the selected records (not read-only or hidden ones; a required one is never cleared), all or
  nothing up to `atomicJobMaxItems` or the records that can change; "all matching" is read with
  progress and Stop; the preview's counts and refused records, each openable, come before Apply;
  the result, Preview again and the selection keeping the versions the change left (D118) follow.
  A batch's job page lists its items' outcomes, linked to their records, and applies or cancels a
  waiting preview. Leaving the dialog before Apply (Back, Cancel, ✕, Escape, a click outside)
  cancels the preview; View job keeps it waiting for its page (D115 amended). Every change is a
  previewed background job (D114, amending D104); deleting a selection moves to K2b (D116).

- Base 0.9 K1: selecting records in a collection (D102–D111). Where the data can be written and jobs
  can be created, a table view has a checkbox column: rows by hand, a Shift range over the loaded
  rows (pointer or Shift+Space), the loaded rows from the header checkbox, then **Select all N
  matching**, also with Cmd+A (Ctrl+A) in the table; a row unchecked under all matching stays an
  exception. A bar above the table states the selection and clears it; a polite status region
  announces each count. A selection over `backgroundJobMaxItems` is refused with an explanation
  naming the count, the limit, `BACKGROUND_JOB_MAX_ITEMS` and what to do. Sorting, scrolling and
  opening records keep it; a new search, filter, scope or data context clears it. No writes yet
  (K2, K3); no backend or contract change.

- Base 0.9 J5: another workspace's export loads as this workspace's own records (D96–D101).
  `otherWorkspaceIds: "counterparts"` on `POST /imports` and `POST /batches` makes an ID held by
  another workspace's record stand for its counterpart here, whose ID is derived from the original
  ID and the workspace key (a name-based UUID in a documented namespace, marked as version 4); the
  same file sent again finds what it created, types load file by file, a change set takes the live
  IDs, and a workspace's own IDs and free IDs are used as given. Every record ID an item names is
  translated, a profile's `matchBy: {"field": "id"}` too; relationship IDs are not. The file's
  versions are ignored on counterparts (`onExisting` decides); outcomes name `sourceId`; the
  notice reads `RECORD_IDS_AS_COUNTERPARTS`; a reference to a counterpart not loaded yet says to load
  its file first. The import dialog offers the choice, loading them by default. Amends D49.

- Base 0.9 J4a: an import says why rows cannot load when the file is another workspace's export.
  Record IDs are unique across the instance, so such a file loads only into the workspace it came
  from (D49); until now every row was refused with no reason a user could act on. The job carries
  `notices` once bound (`RECORD_IDS_OF_ANOTHER_WORKSPACE`, with the workspace and the rows),
  `OBJECT_ALREADY_EXISTS` names the workspace holding the ID (`details.workspaceKey`, live and in a
  change set), and `REFERENCE_NOT_FOUND` names what the reference is for and that workspace. The
  import's page shows the notices above the preview, and a row's reasons wrap instead of being cut
  off. Loading another workspace's export into a workspace is planned separately.

- Base 0.9 J4: the import screen (SC-10 in the browser, D89–D95). **Import** on a collection page
  that can be written loads into its data; **New import** on Settings › Jobs and feed chooses a
  workspace and its live data or a change set. The dialog takes a file, a stored profile (one no
  longer valid listed and not choosable, a keyless one warned) or none, the policy, and whether
  records the file finds are updated (by default with a profile, not without one, D92); it always
  previews (D90) and opens the import's page at once (D91). The job page of an import shows the
  preview with **Load the file** and **Cancel import**, the refused rows paged with every failing cell
  and its column, the binding report per source and column, then the result and how to load refused
  rows (D94); a refused confirmation keeps the preview waiting. Notifications say Preview ready with
  Review, and none shows while the job's own page is open; a waiting preview's stream is closed until
  it is confirmed. A collection reloads after an import this tab started loaded into it. Jobs and
  feed's limits list the import file size and preview items. `ui/FileField` is the one file input
  (the model draft dialog uses it). No backend or contract change. New runner `test:browser:j4`.

- Base 0.9 C18: consumer API definitions written for readers, as schema 0.9 (CONSUMER_API
  C-D132–C-D141). A definition names what it `exposes` (public names default to the key in
  PascalCase), the `operations` it offers (`objects`, `xref`, `resolve`, `lists`, `events`: listed
  means offered), `object.fields` with roles, `related` blocks by a relation's `key` or
  `reverseKey` (role fields may stand anywhere and are output first), `operations.xref.matchOn` and
  `alsoMatchThrough` (`field: "code"` for each code source), `filters` with one verb each (`byType`, `under`, `linkedTo`, `onRelated`), lists `within`
  a filter, events `perType` or `custom` (watching outputs and `related` blocks), and optional descriptions carried into the OpenAPI
  document. Every reader works on one internal form, so for a definition offering every operation
  nothing a consumer reads changes. An operation not offered answers `404 OPERATION_NOT_OFFERED`
  and leaves the OpenAPI document; dropping one needs a new `contractVersion`. Mistakes are refused at
  the pointer the author wrote. `GET /api/v1/model/consumer-apis/{consumerApi}` answers a definition
  with every default written out, for 0.8 and 0.9 releases; the Webhooks page reads it. Install,
  draft compile and `POST /model-validations` refuse a new schema 0.8 document that declares
  `consumerApis` (`UNSUPPORTED_SCHEMA_VERSION` at `/schemaVersion`), and startup refuses such a file
  named by `RDM_MODEL_PATH`; stored 0.8 releases read and
  activate as stored. The starter is content release 0.9.3 and the example model
  0.9.0, both on schema 0.9.

- Base 0.9 J3: import preview and confirmation. `POST /api/v1/imports` takes `stage: "preview"`:
  the file is bound, its first `IMPORT_PREVIEW_MAX_ITEMS` (10,000) items run independently against
  the data in a transaction rolled back whole, and the job waits in `awaiting_confirmation` with
  `preview` (coverage `complete` or `sample`, items and rows covered, counts by action, the result
  under the request's policy) (D80, D82, D83). `POST /api/v1/jobs/{jobId}/confirm` queues it to
  bind the stored file again and execute (D81); it is idempotent, checks the context again and
  refuses with `409 JOB_NOT_AWAITING_CONFIRMATION` or `410 JOB_EXPIRED`; cancel ends a waiting
  preview at once and retention expires it (D87). Every import carries `bindingReport` per source
  and column (D86); `GET /api/v1/jobs/{jobId}/rows` reads its outcomes by row and `/items` takes
  `ref=` (D84); a row refusal lists every failing cell in `details.cells` (D85). Revision
  `20261007_08` adds `jobs.report`, `jobs.confirmed_at` and the source and row of inputs and
  outcomes; `integrationJobs.limits.importPreviewMaxItems` reports the setting.
- Base 0.9 J2a: the database holds unique attribute values. `unique_attribute_values` keeps each
  live value of an attribute the active release declares `unique` once per workspace, keyed by the
  SHA-256 of its canonical JSON under a deferred unique constraint (D75, D77); PostgreSQL triggers
  on `attribute_values` and `model_runtime_state` keep it, so it follows every write and every
  activation (D76). A write that wrote a duplicate past the rule is refused at its end with the
  rule's `409 DUPLICATE_ATTRIBUTE_VALUE`, and at commit by the database; values handed between
  records within one batch or one publish pass. Live data only (D78). Revision `20261007_07` adds
  the table and fills it from the stored values. No API change.
- Base 0.9 J2: imports. Import profiles (`/api/v1/import-profiles`: create, read, list, replace at a
  version, delete; instance-wide, D65) say how a file's sheets and columns become records and
  relationships, checked against the model with every problem at its JSON pointer and read as no
  longer valid when a release breaks them. `POST /api/v1/imports` takes a file and its request as
  `multipart/form-data` and queues a job of kind `import`: XLSX or CSV through a profile, or JSON
  Lines batch items, or an export's CSV or XLSX tables without one (the records table gains
  `applicationKey`, D71). The worker binds the file in one transaction, converting values through
  the attribute registry and resolving keys, matches (also to records the same file creates),
  hierarchy order and related records (D70) by set statements in PostgreSQL (D68); rejected rows
  are the job's first outcomes, named `{sheet}!{row}` with their column, and the items then run as a
  background batch (D72, D73). Rows repeating a key load as one record when they agree and are all
  refused otherwise (D69). `IMPORT_MAX_BYTES` (200 MB) caps a file. Revision `20261007_06` adds
  `import_profiles`. openpyxl becomes a runtime dependency and `python-multipart` is added (D67).
- Base 0.9 J1u: export in the browser and pushed job notifications. **Export** on a collection page
  opens a dialog prefilled with the page's type, data context, filters and parent narrowing (the
  search is not carried); **New export** on Settings › Integration › Jobs and feed exports any types
  of a workspace. A notification says an export started, and another when it ends: completed with
  Download and View job, failed or cancelled with View job. Each job has its own page
  (`/settings/jobs/{jobId}`) with its state, progress, error, Cancel and, for an export, the file's
  facts and Download. `GET /api/v1/jobs/{jobId}/events` streams a job (server-sent events) at once and
  after each committed change until it ends; a trigger on `jobs` (revision `20261007_05`) notifies
  the engine at commit, so nothing is polled (D57–D63).
- Base 0.9 J1: export jobs. `POST /api/v1/exports` exports a stated scope of one workspace (live, a
  change set or a publication; object types each with their own criteria, a subtree, `asOf`,
  relationships `none`, `withinScope` or `all`) as JSON Lines, CSV or XLSX, in the background from
  one database snapshot. The job's new `output` field states what the file holds (counts per type,
  context, the feed position it equals, model release, format, size, SHA-256), and
  `GET /api/v1/jobs/{jobId}/output` serves the file only once the job is completed. JSON Lines holds
  `upsert` and `ensureRelation` batch items with each record's version, so the file sent back as a
  batch changes nothing; CSV and XLSX share one table layout (D49–D56). Exports run on a worker of
  their own. New setting `JOB_FILE_DIR` (default `var/job-files`); revision `20261007_04` adds
  `jobs.output`. The feed's `410 FEED_POSITION_EXPIRED` names the export route beside the
  publication (`details.export`).
- The example model 0.8.0 declares events on its consumer APIs: one per
  exposed object type (`<type>-changed`), each for
  created, updated and deleted, with no watch, so any change to the object's output counts. The
  contract versions stay, as adding events is compatible.
- Webhooks › Deliveries: an event's object ID opens its record, in the webhook's workspace and the
  first application showing that type (none for a deleted record).
- Base 0.9 U5a revision: resend a delivered event by hand. `POST
  /api/v1/consumer-subscriptions/{id}/deliveries/{deliveryId}/resend` sends one event of a request
  again exactly as it was sent (a notice as it was), alone in a new request with the same `eventId`
  and the header `RDM-Redelivery: manual`; once, during the call, on any subscription; the new
  request names the one it repeats (`resendOf`). Revision `20261007_02`. In Webhooks › Deliveries,
  the event's dialog has **Resend**, asking first when the event was already delivered. The edit,
  suspend and delete buttons are on the Configuration tab only.
- Base 0.9 U5a: webhook names and the delivery log.
  - A subscription has a `name` (required on create, editable; existing ones are named after their
    URL's host and path). Renaming alone keeps a batch being retried.
  - Every request the dispatcher sends is logged with its events, the body as sent and each
    attempt's start, duration, status code or error and up to 4 KiB of the answer:
    `GET /api/v1/consumer-subscriptions/{id}/deliveries` (a row per event, newest first, narrowed
    by status) and `…/deliveries/{deliveryId}`. Kept for `CONSUMER_WEBHOOK_LOG_RETENTION_DAYS`
    (7, in capabilities); a pending batch longer; deleted with its subscription. Revision
    `20261007_01`.
  - The Webhooks page: the new-webhook dialog rebuilt in sections, with events as all or a chosen
    few (a searchable list, chosen ones as chips) and filters added from a menu, their values as
    chips; the webhook's page has **Configuration** and **Deliveries** tabs above its name; an
    event opens with its attempts and the request and response bodies as coloured JSON.
- Base 0.9 U5: Settings › Integration › **Webhooks**. Subscribe a receiver to a consumer API's
  events from the page: the consumer API and workspace, the events (each with what it covers), the
  URL (the allowed hosts named), filters per declared parameter, payload and delivery mode; a
  refusal is shown at its field. The signing key is shown once after creating. Subscriptions are
  listed with Active, Retrying or Suspended beside the selected one, which shows the last delivery,
  a failing batch's attempts, receiver answer and next attempt, and when suspended the reason, its
  details and what fixes it. Edit, suspend, resume (from the first event not acknowledged, or with
  `reset`; a refusal lists what to edit, expired events choose the reset) and delete. With
  subscriptions off, the page names the setting. No API change.
  - A workspace that cannot be deleted because of its webhooks lists them, each linked to its page.
  - `ui/CatalogueLayout` and `CatalogueEntry` replace the catalogue markup Workspaces and Model each
    had; Webhooks uses them too.

- Base 0.9 U4: Settings › Integration. **Consumer APIs** shows each consumer API of the active
  release, read only: its name in the address, contract version, base URL and OpenAPI document
  (with copy buttons), its source in the API reference, exposed types under their public names,
  lists and events, and the release that declares it. **Jobs and feed** lists the jobs of every
  workspace newest first with state, result and counts, cancels a queued or running job after
  confirming, and shows the batch, job and feed limits. **API reference** lists the `/docs` sources
  with their versions and documents. No API change; API.md states the `?api=` slug's form.
  - The starter model is content release 0.9.2: it declares a consumer API `rdm` (domains,
    codelists and values; three lists; the event `values-changed`), so a fresh installation has one
    (U-D5). An existing database installs it beside 0.9.0 without activating it.
  - `ui/SettingsTable`, the shared job-limits list and settings read hook replace Deployment's own
    copies; `CopyValue` can link its value; `ConfirmDialog` takes a label for its dismiss button.

- Base 0.9 U3: the Settings area. `/settings` has its own frame without workspace or data context:
  a top bar reading "{product} / Settings" with **Back to applications** (to the last application
  route of the session) and the account, the settings navigation in the rail (in the navigation
  drawer below 760px, opened from a **Settings: {page}** bar), and pages as wide as the application
  pages, built from new `ui/` components (`SettingsLayout`, `Section`, `DescriptionList`,
  `FormField`, `EmptyState`, `Skeleton`, `Toast`).
  - **About**: engine and management API version, schema languages, the active model release and
    when it was activated, the database revision. **Deployment**: the capability groups on or off
    with their settings and limits, then every setting with its value, default, source and what it
    controls; secrets only as Set or Not set, the cursor-key warning when it is ephemeral. Read only:
    settings change with a restart (U-D2). **Appearance**: theme and the default table density for
    this browser; a view's own density (now with **Default**) overrides it.
  - **Workspaces** and **Model** moved under Administration, as the screens they were: the catalogue
    beside the selected workspace, release or draft, each at its own address (U-D10 as revised).
    `/models` and `/workspaces` addresses redirect. Confirmations are toasts; a workspace with
    webhook subscriptions says why it cannot be deleted.
  - The application top bar has a **Settings** link and an **Account** popover (theme, **All
    settings**) in place of Models, Workspaces, the model version and the settings popover. Only
    built pages are listed (U-D11). The workspace switcher is back at the top of the rail, where it
    was before U2.
  - `GET /api/v1/system` answers the same facts. Settings come from a catalogue in `config.py` (group,
    description, secret) held against `Settings` and OPERATIONS by a unit test; the engine version
    has one home, `config.ENGINE_VERSION`. Journey J31 (operator: check what a deployment runs).
  - Planned next: the **Atlas** visual direction (ADR-040), today's shell with a colour for every
    kind of record, applied to every surface in UA before U4 and U5.

- Base 0.9 C13: the events' acceptance. The CONSUMER_API event scenarios are walked end to end,
  from a write through the deriver and the dispatcher to a receiver, on two generated models: a
  publish delivered in batches exactly as the pull feed has it, work that never reaches live data
  (a rolled-back batch, a refused write, a validated and discarded change set) sending nothing,
  filters scoping deliveries as the lists do, a reset and re-sync after expired events missing
  nothing, and a running application delivering on its own. Webhook delivery has a volume budget
  (C-D113): the dispatcher's claim, a delivered batch and a coalesced round hold their statements
  as the data grows, with full-volume figures in POSTGRESQL_BUDGETS §7. CONSUMER_API, OPERATIONS
  and the journeys now say that a filtered subscription is not told when a record leaves its
  filter's scope, and how a receiver handles it (C-D114).

- Base 0.9 C12: webhook delivery. While `CONSUMER_SUBSCRIPTIONS_ENABLED` is on, a dispatcher thread
  in the API process sends each active subscription's events to its URL, in position order, one
  request at a time per subscription.
  - Per change: up to 100 events and at most 1 MiB of body per request, an event alone over 1 MiB
    sent alone (C-D104); each event as the pull feed has it, with the object as get by ID answers
    it (`full`) or without it (`identity`). Coalesced: one notice per event once the newest
    matching event is `debounceSeconds` old, or the oldest 10 minutes old (C-D105).
  - Every request is signed: `RDM-Signature: sha256=<hex>`, the HMAC-SHA256 of
    `"{RDM-Timestamp}.{body}"` keyed with the subscription's `signingSecret`; `RDM-Delivery-Id`
    stays the same on every retry of a batch (C-D12).
  - Any `2xx` acknowledges. A failed batch (another status, a redirect, which is never followed, no
    answer in 10 s, a connection or TLS failure, a refused address) is retried with the same events
    after 10 s, 30 s, 1, 2, 5, 10 and 30 min, then hourly, each ±20 %, for 24 hours from its first
    failure; then the subscription is suspended `DELIVERY_FAILED` (C-D103). Nothing later is sent
    past a failing batch.
  - The host is resolved at each attempt and the request goes to the address checked: link-local
    addresses are always refused, loopback ones unless the URL names a loopback host (C-D107).
  - A subscription answers `delivery`: `lastDeliveredAt`, and `pending` while a batch fails, with
    its attempts, first failure, last error and next attempt; delivery never changes `version`
    (C-D108). `GET /capabilities` reports the limits in `consumerSubscriptions.delivery`.
  - The dispatcher also suspends a subscription whose host left the allowlist (`HOST_NOT_ALLOWED`),
    one with a filter value no record matches any longer, before sending (`FILTER_MATCHES_NOTHING`,
    C-D109), and one whose next events expired (`EVENTS_EXPIRED`, new, C-D110).
  - Several processes share delivery through a 60 s lease per subscription (C-D106).
  - Migration `20261006_03` adds the delivery state to `consumer_subscriptions`.

- Base 0.9 U2: the UI foundation and the shell (ADR-039, Direction B "Open").
  - Design tokens are in three layers in `styles/tokens.css`: primitives, semantic roles (dark mode
    redefines only these) and component tokens.
  - A contrast test holds every text pair to WCAG AA, and control borders, focus and state
    markers to 3:1 (U-D9).
  - Instrument Sans and JetBrains Mono are bundled and served with the UI (OFL-1.1).
  - A top bar holds the workspace switcher, the applications as underlined tabs, and Settings.
  - A data-context band names the data in view: a green Live pill, an amber band in a change set
    with its Review, Validate and Publish actions, and a violet band in a publication.
  - `ui/PageHeader` now draws all ten page headers; there are also `ui/StatusPill` and `ui/Card`.
  - Every screen takes the new colours and type through the older token names, kept as aliases
    until U6 (U-D7). All visual baselines were re-recorded, and `change-set-editing-dark` was added.

- Base 0.9 C11: webhook subscriptions. With `CONSUMER_SUBSCRIPTIONS_ENABLED` (off by default), an
  operator manages subscriptions at `/api/v1/consumer-subscriptions`: create, list, read, edit with
  `expectedVersion`, suspend, resume and delete. A subscription names a consumer API, a workspace,
  some of its events, filters in the definition's parameters, an HTTPS URL on a host in
  `CONSUMER_WEBHOOK_ALLOWED_HOSTS`, `perChange` or `coalesced` delivery and the `full` or `identity`
  payload. Each filter value must match a record (C-D100). It starts after the feed's head, or after
  an earlier `startAfter` (C-D97). Its signing key is shown once and stored sealed (AES-256-GCM)
  under `CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY`, which startup requires with the capability on;
  `python -m app.cli.generate_key` makes one (C-D96). A subscription is `active` or `suspended`
  with a reason (C-D98). Activating a release that drops what it names suspends it
  `MODEL_CHANGED`, one that raises the contract version `CONTRACT_VERSION_CHANGED`, and retiring
  its workspace `WORKSPACE_RETIRED` (C-D99). A resume checks it again and, after unacknowledged
  events expired, needs `acknowledgeLoss` (C-D93). A workspace with subscriptions cannot be
  deleted (`deleteBlockedBy: subscribed`). `GET /capabilities` gains `consumerSubscriptions`. New
  codes: `FILTER_MATCHES_NOTHING`, `INVALID_WEBHOOK_URL`, `WEBHOOK_HOST_NOT_ALLOWED`,
  `SUBSCRIPTION_NOT_FOUND`, `SUBSCRIPTION_ALREADY_SUSPENDED`, `SUBSCRIPTION_NOT_SUSPENDED`,
  `SUBSCRIPTION_NEEDS_EDIT`, `WORKSPACE_HAS_SUBSCRIPTIONS`. Migration `20261006_02`. Nothing is
  delivered yet (C12).

- Base 0.9 C10: consumer events and the pull feed. After a live write commits, a deriver thread in
  the API process turns the workspace's feed entries into the events each consumer API declares,
  without the write waiting: `created`, `updated` naming the watched outputs that changed (also for
  a change to a record the object shows: its parent, an ancestor's name, a projected record, a
  projection's items) and `deleted`; a type change as seen from each event (C-D82, C-D83, C-D87).
  `GET /api/consumer/{consumerApi}/v{contractVersion}/events` reads them in position order from
  `after` or a lasting `cursor`, with `caughtUp`, narrowed by `event` and the definition's
  parameters (C-D90, C-D91); `payload=full` (default) carries each object as get by ID answers it,
  labelled `stateAt`, `payload=identity` leaves it out (C-D7 revised). Every event of the API is
  served, each naming its contract version (C-D88). Events expire with the change feed
  (`410 EVENTS_EXPIRED` naming the publication to re-read) and start, for an existing workspace, at
  its active publication's position (C-D92). New codes: `EVENTS_NOT_DECLARED`, `UNKNOWN_EVENT`,
  `INVALID_PAYLOAD`, `EVENT_POSITION_AHEAD`, `EVENTS_EXPIRED`. `payload` becomes a reserved parameter
  name. A record's feed entry now also keeps its parent and previous parent, not shown in the feed
  (C-D95). Migration `20261006_01` adds `consumer_events` and `consumer_event_checkpoints`.
  Renaming a group with 20,000 items below it tells 20,001 objects in 0.7 s on the deriver's
  thread.

- Base 0.9 C9: consumer API event definitions. A definition declares `events`: exposed types, change
  kinds (`created`, `updated`, `deleted`) and an optional `watch` of the outputs and projections that
  count as an update, named as consumers read them (C-D81). Each mistake is refused at
  `/consumerApis/<key>/events/<event>/…` (C-D84); an event that tells consumers less needs a higher
  `contractVersion`, one that tells them more is compatible (C-D85). What `updated` means and how a
  type change is reported are settled for C10 (C-D82, C-D83). `event` and `after` become reserved
  parameter names, refusing a definition parameter so named (C-D86). No event is produced yet.

- Base 0.9 C16: business dates on the consumer API. `asOf=YYYY-MM-DD` on get by ID, lists, XREF and
  batch resolve keeps the records effective that day by their type's declared effective period, live
  or pinned to a publication. Types without a period are left unfiltered in a lookup and refused as
  `400 AS_OF_NOT_SUPPORTED` on a list or record; a malformed date is `400 INVALID_AS_OF`. Only the
  returned records are dated, not projection items or ancestors (C-D76). Lists, XREF pages and batch
  resolve carry `asOfApplied`, and every dated answer the `RDM-As-Of-Applied` header (C-D78). Each
  API's OpenAPI document declares `asOf` where it applies. SC-11 passes through the consumer API.

- Base 0.9 C8: consumer API parity acceptance. A test-only fixture shaped like the reference
  deployment (the starter with locations, availability, durations and a one-to-one self relation)
  and CONSUMER_API's definition written out answer the parity scenarios, each answer validated
  against the API's own OpenAPI document. A projection field may read `objectType`, the related
  record's public type name, where the definition exposes every type the projection reaches
  (C-D73). The consumer read budgets are collected in POSTGRESQL_BUDGETS §7 (C-D74).

- Base 0.9 V2: the API reference page `/docs` lists every consumer API of the active release beside
  the management API, labelled `{name} · v{contractVersion}`, built per request. A link to a source
  (Scalar's `?api=<slug>`) opens it; before, the parameter was refused.

- Base 0.9 C6b: the consumer API index `GET /api/consumer` (each API's `consumerApi`, `name`,
  `contractVersion` and `openapi` URL, paged, C-D69) and each API's own OpenAPI 3.1 document at
  `/api/consumer/{consumerApi}/v{contractVersion}/openapi.json`: paths written out with the name and
  version, `info.version` the contract version, schemas from the contract, the limits stated. Both
  answer an `ETag`. Dev dependency `openapi-spec-validator` checks the document and real answers
  against it (C-D70).

- Base 0.9 C6a: consumer API reads pinned to a publication. `publication={id}` or `latest` (the
  workspace's active publication) on get by ID, lists, XREF and batch resolve's URL reads the
  publication's records, values and relationships, with the definition of the release it was
  published under (`409 PUBLICATION_CONTRACT_MISMATCH` when that release declares another contract
  version, C-D60); `404 PUBLICATION_NOT_FOUND` for an unknown publication, another workspace's, or
  `latest` with none current (C-D61, C-D62). `RDM-Publication` and an envelope `publication` field
  name it (C-D63); a cursor keeps its publication, also with `latest` (C-D64).
  `GET /api/consumer/{consumerApi}/v{contractVersion}/publications` lists them newest first with
  `eventSequence` and `status` (C-D66). Every consumer `GET` answers an `ETag` and `304` to a matching
  `If-None-Match` (C-D65). Publication lists sort by an attribute through value-order indexes, on the
  management API too (D47, C-D67). Migration `20261005_03`: publication read indexes (C-D68).

- Base 0.9 C15: consumer API crosswalk. `to.{name}` on get by ID, lists, XREF and batch resolve
  names a `projection` parameter declared `targetable` and a value; the projection shows the items it
  matches, and each object carries them again as `target`, before `matchScore`. It changes no object,
  score, order or total, and cursors do not bind it (C-D54). A read of one object answers one target:
  `404 TARGET_NOT_FOUND` for none, `409 AMBIGUOUS_TARGET` for several, each naming the object; a
  page refuses nothing (C-D55). One `to.` name per read (`400 MULTIPLE_TARGETS`); a `to.` name of
  anything but a targetable parameter is `400 UNKNOWN_PARAMETER` (C-D56, C-D57). Turning
  `targetable` off is `version_required` at `/parameters/<name>/targetable` (C-D58). No migration.
- Base 0.9 C14b: a consumer read's ancestors are walked by ID and read by the walked list
  (170–192 ms to 10 ms at full volume), and contains reads are built without table aliases; a
  1,000-lookup batch resolve takes 236 ms (was 817 ms).
- Base 0.9 C14a: batch resolve resolves each distinct lookup once (same terms and parameters, in
  any order); a batch sending one heavy lookup 100 times fell from 1.7 s to 0.8 s at full volume.
- Base 0.9 C14: consumer API batch resolve:
  `POST /api/consumer/{apiKey}/v{contractVersion}/resolve`.
  - **Items.** Up to 1,000 items (`CONSUMER_RESOLVE_MAX_ITEMS`, reported by `GET /capabilities` as
    `consumerApi`; more are `413 BATCH_TOO_LARGE`), each a `query` or an `id`, with an optional
    `ref` and the definition's parameters over the request's `defaults`; JSON values are never
    split on commas (C-D47, C-D50).
  - **Outcomes.** In item order, each the single read's answer: `found` with the object, or
    `not_found`, `ambiguous` or `rejected` with that read's error, a rejection pointing into the item
    (`QUERY_OR_ID_REQUIRED` for both or neither of `query` and `id`); a body of the wrong shape or a
    wrong name in `defaults` refuses the request (C-D48, C-D49).
  - **One scoring path.** XREF is a batch of one: exact matches of every term are read at once,
    contains matches one select per term with its pattern bound; items group by their parameters,
    each group in a fixed number of statements (C-D51). A single best match is sought with the exact
    rules first, so an `expect=one` lookup its exact matches settle is no longer refused for what its
    contains terms match (C-D52, amends C-D37).
  - **Index.** Migration `20261005_02` adds a trigram index on names holding the workspace and type;
    it needs the `btree_gin` extension, which startup now requires beside `pg_trgm` and creates when
    it may.
  - **Budgets.** 1,000 lookups in 816 ms at full volume (451 ms over three parameter sets); XREF's
    lookups 13–65 ms. `test_consumer_xref_volume` checks equal statements for 10 and 100 items.
- Base 0.9 C5: the consumer API's parameters on XREF.
  - **Parameters.** Every definition parameter (`objectType`, `ancestor`, `related`, `projection`)
    narrows XREF with its list meaning: an object is a result when it scored and every parameter
    keeps it, with its unchanged score; `totalCount`, the pages and `expect=one` follow the narrowed
    set, and the cursor binds the parameter values (C-D42). A definition parameter on XREF is no
    longer `400 PARAMETER_NOT_SUPPORTED`. The 10,000-match limit still counts what the terms match
    before parameters (C-D44).
  - **`scoresFrom`.** A `projection` parameter declaring it limits which related records pass
    weights through its projection when the request gives it; own scores are untouched (C-D43).
    Refused at `/consumerApis/<key>/parameters/<name>/scoresFrom` without a `match.promoted` entry
    over the projection (C-D45); turning it on or off is `version_required` (C-D46).
  - **Budgets.** `test_consumer_xref_volume` adds a lookup narrowed by an ancestor and one with
    `scoresFrom`, with equal statements at two sizes.
- Base 0.9 C4: consumer API XREF lookup:
  `GET /api/consumer/{apiKey}/v{contractVersion}/xref?query=…&expect=any|one`.
  - **Scoring.** The live records of the exposed types, scored by the definition's `match` at read
    time over the existing indexes (no consumer index, C-D34): own exact weights add up, contains
    weights count only without an exact one (C-D35); a related record's first matching `firstMatch`
    weight passes to the objects it relates to through the projection, only to the preferred types
    where it relates to one (C-D36). One statement scores; ordered by score, public type name, name
    and object ID. Each result is the shared object with `matchScore` (C-D41).
  - **Migration** `20261005_01`: `ix_objects_workspace_lower_name` on `objects (workspace_key,
    lower(name))` and `ix_attribute_values_key_lower_text` on `attribute_values (attribute_type_key,
    lower(text_value))`, so an exact match ignoring case is an index seek rather than a recheck of
    every record the trigram index finds.
  - **Terms and limits.** Comma-separated (a comma inside a term as `%2C`) or repeated `query`, at
    most 100 (`400 TOO_MANY_TERMS`), none `400 QUERY_REQUIRED` (C-D38). Contains needs 3 characters;
    a query matching more than 10,000 records is `400 QUERY_TOO_BROAD` (C-D37).
  - **Paging and `expect=one`.** Cursors both ways, `position`, `from=end`, `totalCount` always
    (C-D39); `expect=one` answers the bare object, `404 NO_MATCH` or `409 AMBIGUOUS_MATCH` naming the
    tied objects (C-D40). `400 INVALID_EXPECT` for another `expect`. `query` and `expect` off XREF
    are `400 PARAMETER_NOT_SUPPORTED`. Definition parameters apply to XREF from C5.
  - **Model.** A `contains` weight on `id` or a typed attribute is refused at its
    `/match/…/contains` pointer (schema 0.8).
  - **Budgets.** `test_consumer_xref_volume` holds the statement counts at two sizes. At full volume
    lookups take 34–58 ms; refusing a term found in every item takes 116 ms, recorded in TODO.
- Base 0.9 C3b: consumer API parameters list several values as OpenAPI 3 serialises a list in a query
  (RFC 3986): repeated, or separated by literal commas, with a comma inside a value sent as `%2C`.
  C3's `\,` escape is withdrawn; the raw query is split before it is decoded.
- Base 0.9 C3a: lists sorted by an attribute read in value order. Migration `20261004_04` adds an
  index per typed value column on `(attribute_type_key, value, object_id)`, and a live attribute sort
  pages its records with a value through it, then those without one. Nothing changes for callers.
  At full volume a consumer list by rank pages in 10–12 ms (was 0.5–2.6 s) and the per-type list's
  rank sort under the 20,000-child parent in 9.9 ms (was 104 ms, POSTGRESQL_BUDGETS E3 live). A
  consumer list below a parent or an ancestor reads its containers first. Decisions D46–D48; change
  sets and publications follow in C6.
- Base 0.9 C3: consumer API lists and parameters:
  `GET /api/consumer/{apiKey}/v{contractVersion}/lists/{listKey}`.
  - **Lists.** Every live record of the list's type, or those anywhere below the parent records named
    by object ID (C-D27, C-D28), as the shared object; ordered by the list's new optional `sortBy`
    (records without a value last), then name, then creation order (C-D29). Paged as the management
    lists are: cursors both ways with `anchor`, `position`, `from=end`, `seek` and `includeTotal`,
    `pageSize` 1–100, default 20 (C-D30). The envelope names `workspace`.
  - **Parameters.** Every definition parameter applies to lists and to get by ID (C-D31):
    `objectType`, `ancestor` (any depth), `related` (through a projection, `self` or a shared
    projection) and `projection` (limiting the projection's items; `requireMatch` drops records left
    with none). Several values, repeated or comma-separated (a comma inside a value as `%2C`), are
    alternatives; different parameters combine (C-D32 as amended by C3b, C-D33). Each is a SQL predicate, so totals and position
    jumps stay in the database.
  - **Model.** `sortBy` on a consumer list (schema 0.8), validated at `/lists/<list>/sortBy` and part
    of the contract; `from`, `seek` and `includeTotal` are reserved parameter names.
  - **Refusals.** `404 LIST_NOT_FOUND`, `404 PARENT_NOT_FOUND`, `400 UNKNOWN_OBJECT_TYPE`,
    `400 INVALID_PAGE_SIZE`, `400 INVALID_PAGE_PARAMETER`; the shared paging codes answer `400` on
    the consumer tier. A declared parameter on get by ID is no longer refused; a paging name or a
    list's parent parameter there is `400 PARAMETER_NOT_SUPPORTED`.
  - **Budgets.** `test_consumer_list_volume` holds the statement counts at two sizes. At full volume
    a list by parent reads in 7 ms; reads ordered by `sortBy` take 0.15–2.6 s (the attribute sort's
    known cost, POSTGRESQL_BUDGETS E3; C3a reads it in value order).
- Base 0.9 C2: the consumer API tier at `/api/consumer`, with get by ID:
  `GET /api/consumer/{apiKey}/v{contractVersion}/objects/{id}`.
  - **The shared object.** Exactly the fields the definition declares, built from the definition
    alone: the roles and attributes (first source with a value, then `default`, then `null`; empty
    text is no value), `parent` (or `null`, with `objectType` `null` for a type not exposed),
    `path` and `hierarchy` (the ancestors, top down, without the object) and each projection as an
    object or `null`, or an array ordered by name, by the relationship's cardinality. Values keep
    the management API's encoding. Decisions C-D21–C-D26.
  - **Identity.** `{id}` is the object ID (C-D24); another identifier is found with XREF (C4).
  - **Live, by workspace.** Reads live data from the active release's definition, never a change
    set; `workspace` selects the workspace (default: the deployment's), named in the
    `RDM-Workspace` header.
  - **Refusals.** `404 CONSUMER_API_NOT_FOUND`, `404 CONTRACT_VERSION_NOT_FOUND` (naming the served
    version), `404 WORKSPACE_NOT_FOUND` (unknown or retired), `404 OBJECT_NOT_FOUND`,
    `400 UNKNOWN_PARAMETER`, and `400 PARAMETER_NOT_SUPPORTED` for a declared parameter until C3.
  - **Cost.** One statement for the records and their values, one per projection and one recursive
    CTE for the ancestors, whatever the number of objects. The routes stay out of the management
    OpenAPI document.
- Base 0.9 F2: change feed retention and recovery.
  - **Retention.** `FEED_RETENTION_DAYS` (default 30, reported as `changeFeed.retentionDays` by
    `GET /capabilities`). `earliestPosition` is the first entry within the period. A position below
    it is `410 feed_position_expired`, naming `earliestPosition`, `headPosition` and the active
    publication with its `feedPosition`, the baseline to re-read before following on.
  - **Always a way back.** The earliest position never passes the active publication's, and a
    workspace without one keeps every entry (D40). The audit log is not pruned.
  - **Publications** carry `feedPosition`.
  - **Cost.** A 500-entry page reads in 25–35 ms with 4 statements, at the head and in the middle of
    a 1,000,000-entry feed.
  - **Migration** `20261003_03`: the index the retention floor is found by. Decisions D40–D41.
- Base 0.9 F1: the change feed `GET /api/v1/workspaces/{key}/feed`.
  - **Positions.** Every change to a workspace's live data has a position: per workspace, gapless and
    in commit order. A live write takes positions under the workspace lock it already holds (one
    statement per write), so a refused or rolled-back write leaves no gap. Change-set work takes
    none.
  - **Reading.** A reader passes the last position it processed (`after`) and pages with `pageSize`
    (1–1,000, default 500) until `nextAfter` equals `headPosition`. `kind` and `objectTypeKey`
    (repeatable) filter within a scan of at most ten pages, never an unbounded one.
  - **Entries.** Each entry names the record or relationship, its type, version, the changed fields
    and attribute types (never values), the cause (a user, a job or a publication) and the model
    release.
  - **Publishing.** A publish writes one entry per record and relationship it changed in live data
    (`reclassified` with the previous type for a type change), then its `published` entry.
    Withdrawing adds `withdrawn`.
  - **Refusal.** A position past the head is `409 feed_position_ahead`.
  - **Migration** `20261003_02`; the feed starts empty, with no backfill. Decisions D31–D34.
- Base 0.9 B3: relationship items in `POST /api/v1/batches`.
  - **Items.** `createRelation`, `ensureRelation` (unchanged when the relationship already exists
    with the same values), `updateRelation` and `deleteRelation`, with the ends named by ID or by a
    unique value, and set claims as on the single routes.
  - **Set replacement.** `replaceRelationSet` makes a record's set of one relationship the listed
    records. Kept relationships keep their identity and values, the set's version is claimed (or
    the request declares an overwrite), and an equal set answers `unchanged`.
  - **Bulk.** Relationship items are decided in memory and written in bulk with the object items
    around them: 40–43 statements per chunk of 500 at two data sizes (D35).
  - **Set versions on the anchored read.** `GET /relations?objectId=…` names every set the record
    anchors with its version as `relationSets`, an empty set included (D38).
  - Decisions D35–D39. No migration.

### Changed

- Base 0.9 K2b: a change set's deletions are audited per record (`change-set-object`, `deleted`), as
  its creates and updates are; the single delete's preview token is computed differently (it stays
  opaque), so a token issued before this release is refused `DELETION_PREVIEW_CHANGED` and previewed
  again. The bulk change dialog's flow is shared by every bulk action (`BulkJobDialog`).

- Base 0.9 K2 (D119): `IMPORT_PREVIEW_MAX_ITEMS` is renamed `JOB_PREVIEW_MAX_ITEMS` and
  `integrationJobs.limits.importPreviewMaxItems` `previewMaxItems`, without an alias, since the
  limit now bounds a batch's preview too. The OpenAPI schema `ImportPreview` is `JobPreview`, its
  `rows` an import's only; a batch's `parameters` name its `stage`.

- Base 0.9 C17: webhook delivery choices. A subscription chooses how requests are made, three
  independent choices: `maxEventsPerBatch` (1–1,000, default 1: one event per request; batched, a
  request holds what is waiting, up to that many and 1 MiB), `payload` (`full`, "with the object",
  or `identity`, "notification only") and `format` (`rdm`, default, or `cloudevents`: CloudEvents
  1.0 in structured mode, one event per request as `application/cloudevents+json`, batched as an
  `application/cloudevents-batch+json` array, each with the RDM event as `data`). The coalesced mode,
  `mode` and `debounceSeconds` are removed (C-D105 retired); sending them is `422`. Capabilities'
  `delivery.maxEvents` is now `maxEventsPerBatch` (1,000). The delivery log has no notice rows and
  its detail no `kind`; a resend needs `eventId` and repeats the event in the format it was sent in.
  Revision `20261007_03`: existing subscriptions take the defaults and logged notices are deleted.
  The webhook dialog's Delivery section has the three choices, and a webhook's page shows them.

- Webhook URLs may name any host (C-D101 revised): HTTPS on any host and port, plain HTTP only to
  `localhost`, `127.0.0.1` or `::1`. `CONSUMER_WEBHOOK_ALLOWED_HOSTS` is removed, with
  `consumerSubscriptions.allowedHosts` in capabilities, `WEBHOOK_HOST_NOT_ALLOWED` and the
  `HOST_NOT_ALLOWED` suspension; adding a receiver no longer needs a restart. The dispatcher still
  refuses link-local addresses (cloud metadata) when it connects. The Webhooks dialog and the
  Deployment page drop the allowed hosts.

- Base 0.9 UA1: every application and every kind of record has a colour (ADR-040). Each takes one
  of eight hues by its position in the model, so any model is coloured and no screen knows a key;
  the application tabs and the rail's Collections show it as a tile with the model's icon. The
  hues, their dark values and the context strips are tokens held to the contrast minimums in both
  themes.
- Base 0.9 UA2: the record browser shows what contains what. Every record carries its type's
  tile, an open branch hangs from a guide line, a type's heading is a quiet label with its count
  and never looks like a record, and the selected record is filled with its type's colour.
- Base 0.9 UA3: the collection page in the Atlas look. The page header carries the type's tile,
  Live is a soft green strip with dots of the change-set and publication colours on their switches,
  a column that shows another record (an `ancestor:<type>` column) shows it as a chip in that
  type's colour, the selected row takes its type's colour, booleans read Yes and No in plain text
  everywhere, the first page loads as rows in the table's shape, and an empty collection shows its
  tile and the Add action.
- Base 0.9 UA4: the record in the Atlas look. The record's header is a band tinted in its type's
  colour with the type's tile, the type named in its colour, and the ancestors in the breadcrumb as
  chips in their types' colours that open them; history markers take the type's colour. In the
  inspector beside a tree lens the sections are ruled, fields sit beside their labels, and the
  relationship panels become one **Connected** list of chips in the related types' colours (with
  **Show more** and a way to manage them on the full page); the full page keeps the tables.
- Base 0.9 UA4 revision: one table for every list of records in rows (`ui/DataTable`): collections,
  a record's children and its relationships. Relationship tables gain the Display menu (columns,
  density, page size, widths), table-shaped loading rows, the empty state, row colours and the phone
  layout's three columns with **Show all columns**. Columns resize by dragging the edge of their
  header (it was reachable by keyboard only): a drag starts from the column's drawn width, keeps the
  other columns as they were, and may make a column narrower than its content, which then ends in an
  ellipsis. The look of a table that has not been resized is unchanged.
- Base 0.9 UA4 revision: a record's fields are edited by clicking their value, not by Edit, Remove
  and Add value buttons. The value is a button that reads as text, with a soft fill and a pencil on
  hover and focus (a plus on an empty field, which adds a value); an optional value's trash icon
  shows with the row's hover or focus and always on touch, and removing still asks first. Saving
  stays explicit, a selected text is left for copying, and focus returns to the value after
  editing. Read-only fields and publications show plain values.
- Base 0.9 UA4 revision: Settings › Appearance has **Type colours**: palette B (magenta and olive,
  the default) or A (plum and gold) for the record type colours, saved in this browser.
- Base 0.9 UA4 revision: Settings › Appearance has **Edit pencil**: a record's editable fields show
  their pencil on hover and focus (the default) or faintly all the time, saved in this browser.
- Base 0.9 UA4 revision: the top bar takes a way back (`TopBar`'s `back`), shown after the product
  mark. Settings uses it: **Back to {application}** returns to the exact page Settings was opened
  from, or to the home page when Settings was the first page opened.
- Base 0.9 UA4 revision: the record's header shows its ID (the `id` the management and consumer
  APIs return) under the title, in monospace with a copy button (`ui/CopyValue`), in the inspector
  and on the full page.
- Base 0.9 UA5: change sets and publications in the Atlas look. A change set is the soft amber
  strip and a publication the soft violet one, as Live is green, each with a line saying what an
  edit does there; the pill names the context and the change set's bar gives its name, version,
  source and model with its actions at the end: **Review changes**, **Validate change set**,
  **Publish change set** (the indigo primary action) and a **More change set actions** menu
  (`ui/ActionMenu`, in place of a hand-made one) for **Change model version** and **Discard change
  set**. The change set and publication lists are ruled rows on one card (`ui/RuledList`), grey
  under the pointer as table rows are; a publication's **Start a change set from this publication**
  and **Withdraw publication** moved into its row's menu, beside **Open publication**. An empty
  change set list offers **Start from current live data** as the header does. In **Review changes**
  the kind of change is a pill (Added green, Changed grey, Removed red), a record shows its type's
  tile, and a relationship's two ends are chips in their types' colours.
- Base 0.9 UA2 revision: the record browser's group frames show only while a group scrolls, in the
  sidebar and the hierarchy lens. At rest they are invisible, and the glow on the group under the
  pointer is removed.
- Base 0.9 UA2 revision: a type group's heading in the record browser no longer shows its count;
  screen readers still hear it with the heading's name.
- Base 0.9 UA7: dark mode and the gates. Every surface was checked in dark beside its light
  version. Checkboxes and radios are drawn from the design tokens instead of the browser's own
  controls, which in dark were grey discs where a disabled choice looked like an enabled one. A
  table's column resize handles stand outside the header cells, so a column header is named by its
  label alone (it read "Path Resize Path column"). The visual gate holds 64 baselines, every
  screen in light and dark, adding the mapping grid and its dialog and a collection and a record at
  390px; the accessibility gate checks the same pages (73 checks, no violations).
- Base 0.9 UA6 revision: the settings navigation's group headings are dark and bold, and their pages
  hang one step in from a guide line, so headings and pages no longer look alike. In the 390px
  drawer the navigation keeps the rail's inset and the headings their size (they took the dialog's
  heading size and sat against the screen edge).
- Base 0.9 UA6: the remaining surfaces in the Atlas look. The relation matrix, mapping grid and
  tree lens carry their row type's tile in the page header, as a collection does; a matrix cell's
  record and a mapping's targets (in the grid and in its dialog's **Currently**) are chips in their
  type's colour, and mapping states are pills (Mapped green, Unmapped grey, Ambiguous amber). The
  dialogs that list records to choose (move, mapping target, matrix link and place, restructuring's
  siblings) show each record's type tile, through one `ui/Candidate` row; the matrix cell dialog and
  the restructuring plan show it before each record. Every state tag is a `StatusPill` (release
  and workspace states, capabilities, diagnostics, model changes, refusals), every panel a
  `ui/Card`, every notice `ui/Notice`. Removed: the 51 older token aliases in `base.css` (the
  stylesheets read the roles), the `.surface`, `.pill`, `.compatibility` and mapping badge rules,
  and six rules no screen used.
- Base 0.9 UA2 revision: the record browser's groups sit in frames of their type's colour, nested
  as boxes inside boxes; a group glows in the accent while it scrolls and in teal while the pointer
  is in it; with a pointer, a scrolling group stops at its first and last row; records sit one step
  in from their group's heading. Folding headings is built and switched off (`FOLDING_GROUPS`).
- Record browser: the group under the pointer owns the mouse wheel, its heading included; at its end
  the wheel moves the window around it only until the whole group is in view, so a group partly
  scrolled out of sight can always be brought back from inside it.
- Record browser: a new scroll gesture on a group that is at its end moves the area around it on,
  so the sidebar never gets stuck; scrolling up into a group also shows the record it belongs to;
  the groups' resting frames are fainter.

- Base 0.9 C12: `POST /consumer-subscriptions/{id}/resume` takes `reset` instead of
  `acknowledgeLoss` (C-D93 revised, C-D110). `reset: true` starts delivery after the workspace's
  feed head, whatever happened before; without it a resume after expired events is still
  `409 EVENTS_EXPIRED`, its message naming `reset`. A resume and an edit now also clear a failing
  batch's retries, so the next attempt is at once. A filter value that stops matching suspends
  the subscription without delivering the deletions first (C-D94 revised).
- Base 0.9 C12: the job worker, the event deriver and the new dispatcher log a database they cannot
  reach in one plain ERROR line, with the traceback at DEBUG, then a WARNING a minute; other
  failures keep their traceback. J12's outage case no longer fails when the deriver polls during
  the outage.

- Base 0.9 C8: a consumer object's `parent` keys its fields by the roles' output names, as the
  object's own fields (`masterId`, not `id`, where the `id` role's output is `masterId`; C-D75).
  The reference deployment's parent has these names, and a flow reading a field from an object and
  then from its parent uses one name.

- The example model 0.6.0 declares one consumer API, `rdm`, over every object
  type of the model, so one XREF looks up any ID, code or name across every type, systems and
  translations; `type` narrows it, and `system` and
  `language` resolve and translate codes (crosswalk). Lists per type. It replaces 0.5.0's four
  APIs split by audience, whose XREFs each searched only their own types.
- Base 0.9 CN1: the consumer API's name is written `consumerApi` in public contracts, not
  `apiKey`, which reads as a credential: the route `/api/consumer/{consumerApi}/v{contractVersion}/…`
  and the planned API index, subscriptions, webhook bodies and events (U-D1). No response changes:
  none carried the name, and the not-found errors gain no field (C-D59). The model keeps `key`.
- **Breaking — Base 0.9 C2: a consumer API's identity is the object ID.** The `id` role's source is
  `["id"]`; a `unique` attribute as its source, which C1 accepted, is refused at
  `/consumerApis/<key>/object/id/source`. Publish a former system's ID as an attribute field.
- **Breaking — Base 0.9 T1b: error codes are upper case** on every API: `object_not_found` is now
  `OBJECT_NOT_FOUND`. It covers error bodies, the errors and unprocessed `reason` of batch and job
  item outcomes, and validation diagnostics (D42). Status, action, kind and classification values
  keep their case; a consumer contract's `version_required` classification is unchanged. Revision
  `20261004_03` upper-cases the codes already stored in job results (D43). A check in the
  `contract` group refuses a new lower-case code (D45). Clients comparing codes must compare the
  new spelling.
- Base 0.9 T1a: current-live change-set bases and publications copy records, relationships, typed
  values and matrix states inside PostgreSQL. Publications copy live data after applying the
  change; merge and graph validation remain in Python. Revisions `20261004_01` and `20261004_02` add
  the `rdm_value_json` and `rdm_decimal_text` encoding functions; a decimal at any stored scale
  (1e-16383 answered `500`) encodes as Python does. API behavior is unchanged.

- Base 0.9 B3: the single relationship writes and the mapping save are batches of one through the
  same decide steps as batch items, so they answer with the same codes.
  - A relationship update checks its version before its values, live as in change sets.
  - A change-set relationship delete records an audit entry.
  - A mapping transition's audit payload lists `newTargets`.
- Base 0.9 B3 (D36): replacing a required relationship's only target, through the mapping save or a
  set replacement, is `422 required_relation` when the record losing it has no other.

- Base 0.9 F1 (D15): a publish's changes to live data now show in record history, one entry per
  record with `cause: {"kind": "publication", "id"}`; `AuditCause.kind` gains `publication`.

### Fixed

- Base 0.9 UA0: with a popover open (Account, Display, Filter), the first click on the page only
  closed it, so a tab or link seemed not to respond. `ui/ControlPopover` is now non-modal: a press
  outside, or the user's own wheel or touch scrolling, closes it and the press acts; a scroll the
  layout causes, such as an applied filter shortening the list, keeps it open. Escape and focus
  leaving it still close it. `test:browser:settings` clicks an application tab, a settings link and
  the page heading with Account open.
- Base 0.9 UA0: the workspace switcher, opened before the current workspace had loaded, showed only
  that workspace: its name arriving as the field's value filtered the open list. The switcher is
  disabled until the current workspace is known. This was `test:browser:w4`'s intermittent miss.
- Base 0.9 UA0: the application tabs stood 20px after the product name in the top bar; they start
  36px after it, as ADR-040 says.
- Base 0.9 UA0: Settings had a top bar of its own, whose product mark could not be clicked and
  which had no applications. Every page now has the same top bar (U-D14): on Settings no
  application is current and **Settings** shows as the current tab (gear, name, underline), an application's tab goes back to it (the one last
  looked at, to the same view and query), and the mark goes home. "Back to applications" is gone.
  One frame (`app/ShellFrame`) and one top bar (`app/TopBar`) serve every area, and copied markup
  is replaced by shared components: `ui/SearchField`, `ScopeBanner`, a release picker and a
  change list.

- Base 0.9 C8: the `consumer` test group now selects the J29 journey tests; since C4 it had left
  them out (`JOURNEY_GROUPS` had no `J29`).

- Base 0.9 C6b: a consumer API document was not valid OpenAPI when a list's parent parameter shared a
  definition parameter's name (`Duplicate parameter`); the list's operation now lists the name once,
  as the parent, as the route reads it.

- Base 0.9 C15: a model shape error inside a typed union (a view's or panel's `config`, a consumer
  API parameter) was reported at a path holding Pydantic's type tag, such as
  `/applications/1/views/1/tree/config/pageSize`, which names no node of the document, so the model
  draft editor could not go to it. The tag is left out: `/applications/1/views/1/config/pageSize`.
- Base 0.9 T1: creating a change set from current live data and publishing a change set failed with
  `500` in a workspace holding more than about 65,000 records. Both read every record's values and
  relationships with a list of all the record IDs, one statement parameter each, and PostgreSQL
  refuses more than 65,535. They now select by workspace, and the publish checks each relationship
  end with a primary-key probe.
- Base 0.9 T1: capturing current live data and publishing slowed quadratically with the number of
  records they wrote. The typed value index's flush hook rebuilt SQLAlchemy's set of pending rows
  once per row. At about 10,000 records (4 % of the volume fixture), capture now takes 4.6 s instead
  of 28.1 s, and publish 6.0 s instead of 29.9 s.
- Base 0.9 T1: applying a publish to live data flushed the session once per changed record, with
  the whole workspace loaded. It now writes the changes with explicit flushes, and copies the
  publication and a change set's base in multi-row statements. Publishing 1,000 changes in a
  26,000-record workspace takes 11.3 s instead of 25.0 s.
- Base 0.9 B3: relating the same two records twice with one relationship type answers
  `409 duplicate_relation`. Live, it answered `500`; in a change set, the duplicate was staged.

## [0.9.0-alpha.1] - 2026-10-03

Everything since 0.8.0: Base 0.9 packages Q1–Q4, C1, V1, B1 and B2, and the PostgreSQL runtime
(PG1–PG3b, PG5; PG4 dropped) with the test harness (H1–H4d-1).

### Added

- Base 0.9 Q1: cross-type lookup `GET /api/v1/objects`. It lists records of every object type, or of
  those a repeatable `objectTypeKey` names, in live data, a change set or a publication, with the object
  list's paging, seek and cursors. `applicationKey`, `parentObjectId` or `topLevel` narrow it, `search`
  matches the name, and filters and sorts take built-in fields. A model-declared field is refused
  (`422 invalid_filter` or `invalid_sort`) with the per-type route that answers it. Items have the
  per-type list's shape. Over the 258,000-record volume fixture a first page takes 5–9 ms and a name
  search with its total 72–80 ms in every context.
- Base 0.9 Q2: the workspace edge list. `GET /api/v1/workspaces/{key}/mappings` takes `publicationId`
  (with `changeSetId` it is `422 mutually_exclusive_context`), and the same list is published as
  `GET /api/v1/workspaces/{key}/relations`: every edge of any relation type in live data, a change set
  or a publication, with one response shape. Each route's cursors are its own. A publication's rows
  carry `mappingVersion` 0. `GET /api/v1/relations` is unchanged.
- Base 0.9 Q3: the model-aware query `POST /api/v1/workspaces/{key}/queries/objects`. It lists one
  object type's records in live data, a change set or a publication by criteria combined with AND:
  the object list's field criteria with typed JSON values, `ancestor:<type>` by ID, and one relation
  hop (`related`, inverted with `not`). One `sort`; `select` returns chosen values under `fields`;
  `expand` adds up to 20 related records per item with their `count` and a cursor that continues on
  `GET /relations`, one statement per expansion for the page. Paging by cursor, position or `from`,
  with cursors bound to the body. Model-dependent mistakes are `422 invalid_query` with a JSON
  pointer; `asOf` was refused as `as_of_not_supported` until Q4. Decisions D17–D19. Over the
  100,000-item volume fixture every measured query takes 4–91 ms.
- Base 0.9 C1: schema 0.8 with consumer API definitions (`consumerApis`). A definition declares its
  `key` (the `apiKey`), `contractVersion`, exposed types with public names, the shared object's roles
  and attributes with their sources, projections over relation routes, scoring weights, parameters of
  kind `objectType`, `ancestor`, `related` and `projection`, and lists. Every reference is validated
  against the release and refused at its JSON pointer; a field's sources share one type (C-D19), the
  identity is `id` or a unique attribute, and match fields are searchable or unique (C-D20). Draft
  compile and release diff report `consumerContracts` against the active release, and activation
  refuses a breaking change without a higher `contractVersion` (`409
  consumer_contract_version_required`; C-D17, C-D18). Schema 0.5–0.7 models and their hashes are
  unchanged. Decisions C-D17–C-D20.
- Base 0.9 Q4: effective periods and `asOf`. Schema 0.8 lets an object type declare one
  `effectivePeriod` over two `date` attributes it binds (inclusive start, exclusive end, either open).
  Writes refuse an end not after its start with `422 invalid_effective_period`, live and in a change
  set, and change-set validation reports it. `asOf=YYYY-MM-DD` on `GET /objects/{objectTypeKey}` and in
  the model-aware query keeps the records effective on that date in live data, a change set or a
  publication; a type without a period, and the cross-type lookup, refuse it as
  `as_of_not_supported`. Activating a release that declares a period over records it would refuse is
  `model_migration_required` with their count, and removing a period from a type a consumer API
  exposes needs a higher `contractVersion`. The starter is content release 0.9.0 on schema 0.8, with
  a period on master values. Decisions D20–D22.
- Base 0.9 V1: the API reference at `/docs` is [Scalar](https://github.com/scalar/scalar) (MIT) over
  the management OpenAPI document, replacing Swagger UI and ReDoc (`/redoc` now answers `404`). The
  Scalar script (1.72.2) is bundled with the engine, so the page works without internet access and
  loads nothing from another host; `RDM_API_REFERENCE_SCRIPT=cdn` loads the same version from
  jsDelivr under its integrity hash. The page is outside the OpenAPI document, which is unchanged.
- Base 0.9 B1: bulk object writes as jobs. `POST /api/v1/batches` runs `create`, `update`, `upsert`
  and `delete` items inline, live or in a change set, under a required policy: `atomic` (all or
  nothing) or `independent` (each item alone, in order, seeing earlier applied items). Each item goes
  through its single write and is refused with the same code; records are named by ID or by a unique
  attribute's value, an upsert by an ID or a unique attribute, an item that would change nothing is
  `unchanged`, and an upsert that finds a record needs `expectedVersion` or `onExisting: "overwrite"`.
  The response is the job with its counts and `result` and its outcomes in item order, each with a
  JSON pointer when refused. `Idempotency-Key` answers a retry with the first job. `GET /api/v1/jobs`,
  `/jobs/{id}` and `/jobs/{id}/items` read jobs back; object history names the job as each change's
  `cause`. Limits and retention are settings reported under `integrationJobs` in `GET
  /capabilities`; `INTEGRATION_JOBS_ENABLED=false` removes job creation. Decisions D23–D26; D13
  confirmed: 1,000 upserts take 3.3 s live and 6.8 s in a change set on the volume fixture.
- Base 0.9 B2: background batches. `run: background` queues the batch (up to 1,000,000 items in a
  50 MB body) and answers `202` with the job; a worker in the API process applies it in chunks of
  500, each committing its changes, outcomes and progress together, so a job resumes after a crash or
  restart at its first item without an outcome and never applies one twice. The worker holds a lease
  on the job (`leaseOwner`, `leaseExpiresAt`), which another worker or the restarted process takes
  over once it expires. `POST /api/v1/jobs/{jobId}/cancel` stops a job at its next chunk (an atomic
  job rolls back completely); a model release activated meanwhile, a change set written by someone
  else or an internal error fail it, and the items it did not reach are `unprocessed` with the
  reason. Finished jobs expire after their retention with their summary kept. New settings
  `BACKGROUND_JOB_MAX_ITEMS`, `BATCH_BACKGROUND_MAX_BYTES`, `JOB_CHUNK_ITEMS` and
  `JOB_LEASE_SECONDS`. Decisions D27–D30. On the volume fixture a
  100,000-item background batch runs at 433 items/s live and 151 in a change set; on SQLite, other
  writes wait until such a job ends.

### Changed

- 0.9.0-alpha.1 PG1: PostgreSQL is the only database. `DATABASE_URL` is required and must name a
  PostgreSQL database with the ICU root collation `und` (PG-D11: a language-independent Unicode order,
  so names sort case- and accent-aware, `Elan, élan, Élan, Emil`, where SQLite sorted by code point).
  Startup refuses a missing or non-PostgreSQL URL, another driver, an unreachable server, another
  collation, an unknown schema revision and a `pg_trgm` it cannot create, each with what to do and
  `/health` 503. The 23 SQLite migrations are one PostgreSQL baseline (`20261001_01`); a migration
  runs in one transaction. `scripts/postgres.sh start|stop|status|backup` runs a development server
  from Homebrew's `postgresql@17`; the backend tests start their own and reuse seeded template
  databases until the migrations, model or seed code change (`python -m tests.seeds list|build`).
  The Docker Compose database and CI use ICU `und`. Existing SQLite databases are carried over in
  PG4.
- 0.9.0-alpha.1 PG1: the relation list's sort by `ancestor:<type>` works on PostgreSQL (it used a
  SQLite-only grouping); the ancestor chosen is unchanged.
- 0.9.0-alpha.1 PG2: the PostgreSQL forms. Starting a change set from current live data
  (`source: currentLive`) works on PostgreSQL: the base is read from one snapshot while share locks
  keep a retirement or an activation from committing, and a change the snapshot cannot hold answers
  `409 change_set_snapshot_retry` (`change_set_snapshot_unsupported` is gone). Activation and
  workspace deletion wait for row locks instead of failing on a busy database, so
  `model_activation_retry` and `workspace_delete_retry` are no longer returned, and the
  `SQLITE_LOCK_WAIT_SECONDS` setting is removed. Search reads `pg_trgm` GIN indexes over text values
  (revision `20261001_02`) with the same results, and case-insensitive search folds every script
  (`ünal` finds `Ünal`). Foreign keys are enforced; every `ondelete` rule is pinned in
  `test_foreign_keys`, and a record written into a workspace deleted meanwhile still answers
  `404 workspace_not_found`. Relation matrix states and pages walk each cell record up to its
  column once, with nothing joined back: building the states of the volume fixture at scale 0.005
  took 14 s and grew about four times per doubling; it now takes 0.3 s, 1.0 s at 0.02 and 7 s at
  0.1, and a matrix page at 0.01 went from about 120 ms to 40 ms. Relation expansions and the restructuring
  planner order names as the database does. The browser runners run on the development server
  (`scripts/postgres.sh start`), each on its own database cloned from a seed built once
  (`tests/browser_seeds.py`).
- 0.9.0-alpha.1 H2: the backend tests run in parallel with `pytest -n auto` (pytest-xdist, a dev
  dependency; each module on one worker, each worker with its own session database). Timing-based
  tests carry a `serial` marker (the `volume` group and two timer-decided tests); a parallel run
  leaves them out and names the command that runs them without `-n`. The 968 parallel tests take
  1 min 49 s on 10 cores.
- 0.9.0-alpha.1 H3: the full-size batch budgets (`test_batch_volume`, `test_background_volume`)
  carry a `budget` marker and run only when `-m` names `budget`. `serial` holds only the three tests
  whose outcome depends on wall time; the counting volume modules run in parallel. The run summary
  lists every test over 10 s and the wall time. The full suite without `budget` takes 2 min 41 s.
- 0.9.0-alpha.1 H4b: tests are of two kinds, journey tests in `backend/tests/journeys/` that name
  the user journeys they walk (`@pytest.mark.journey`, checked against USER_JOURNEYS.md;
  `--journey J02` selects them) and unit tests in `backend/tests/unit/` that mirror the module they
  test. `pytest --testmon` runs only the tests whose code changed, `python -m tests.affected` says
  what a change requires (migrations, the starter model and the harness select everything), and
  `python -m tests.journey_trace` shows the code each journey reaches and the code no test reaches.
  `test_api_journeys` keeps the API inventory (`docs/testing/API_JOURNEYS.md`) complete: every
  operation, parameter, error code and setting with its journeys.
- 0.9.0-alpha.1 H4c: every route refuses a query parameter it does not take with
  `422 unknown_parameter` naming each in `details.parameters` (a misspelt `pagesize` was silently
  ignored, as was a `publicationId` on a write, which then wrote live data). `GET
  /api/v1/workspaces/{key}/mappings` is removed; `GET /api/v1/workspaces/{key}/relations` is the same
  list, and the path keeps the replacement's `PUT`. API.md documents the 32 error codes it lacked.
- 0.9.0-alpha.1 H4c: journey tests for every journey and variant of the catalogue with an API or
  operator side (160 tests, 345 runs on two model configurations each, about 1 minute in parallel),
  written from the catalogue and API.md before the code was read. Each runs on a generated model and
  on the starter model or a second generated one, against a seed built once through the API. The
  operator's journey starts the service on prepared databases and runs its commands as processes.
- 0.9.0-alpha.1 H4c, decided from the journey tests: a stale `expectedVersion` on a record or
  relation write answers `409 version_conflict` with `details.currentVersion`, as a workspace update
  did. A live write naming an unknown relation type is `422 unknown_relation_type` (was 404), and a
  live create whose `initialRelations` repeat one relationship is `422 duplicate_initial_relation`
  (was `409 cardinality_violation` or `duplicate_relation`), as in a change set. The relation matrix
  answers an unknown `applicationKey` with `404 unknown_application`. `/health` asks the database
  and answers `503` while it is unreachable; it recovers without a restart.
- 0.9.0-alpha.1 H4c: a duplicate unique value is refused alike live and in a change set: the message
  names the attribute, `details` carry `attributeTypeKey` and `conflictingObjectId` (live had no
  details). Empty text in a unique attribute is no value in a change set too, so records may share
  it there as live. A change set holds a breach of a binding's ancestor scope written directly (a
  relation create, initial relations, an edit, a move or a set replacement) as it already held one a
  moved container brought: the matrix shows the conflict, validation reports it and publishing
  refuses it, so a change set's edits can come in any order. Live still refuses it at once.
- 0.9.0-alpha.1 H4c: a live relation create or initial relation naming a record that does not
  exist answers `422 relation_endpoint_missing` naming it (was `404 object_not_found`), as a change
  set does.
- 0.9.0-alpha.1 H4d-1: the jobs and batches tests are journey and unit tests. Four old modules
  (73 cases) are removed; their checks are in J11, J12 and J24 or in unit tests of
  `engine/jobs/*`, `records/audit.py`, `models/commands.py`, `config.py` and `main.py` (62 cases),
  which run the engine on a clone of a journey seed without starting the application. 14 faults
  planted in the area's rules were each caught by the tests that remain.
- 0.9.0-alpha.1: no SQLite copy command (PG4 dropped). Starting on a SQLite `DATABASE_URL` is refused
  with the instruction to name a PostgreSQL URL; the message no longer points to a copy command.
- 0.9.0-alpha.1 H4: the testing consolidation stops after H4d-1 (H4d-2 onwards and H4e postponed,
  no dependency for 1.0). Journey tests, unit tests and the older modules form the suite; a package
  selects its checks with testmon and the journeys it touches, and its test work is capped in
  proportion to the feature (AGENTS.md).
- 0.9.0-alpha.1 PG3: live writes of one workspace serialize on its row lock, and workspaces write
  in parallel (PG-D5). Every live write locks its workspace before it reads, so two writes racing
  for one unique value, a parent cycle, a cardinality limit, a required relation, a relation-set
  version or one relation matrix cell no longer both commit: the second reads what the first
  committed and is refused with its single write's code. A relation create and a mapping save on
  one edge no longer deadlock (a 500); the mapping save answers `409 mapping_version_conflict`. A
  workspace deleted or retired while a write waited is refused with `404 workspace_not_found` or
  `409 workspace_retired`, nothing saved. A background job holds the lock for one chunk, so a live
  write in its workspace waits for that chunk only; a cancel request is answered while a chunk runs.
  The cascade deletion no longer locks three whole tables. Retirement, default switching, deletion
  and publishing take their locks in one documented order (ARCHITECTURE). A change-set write now
  locks its workspace against retirement and deletion too: a retirement waits for it instead of
  committing beside it, and a later write is refused `409 workspace_retired`. Publishing no longer
  holds up writes in other change sets of its workspace.
- 0.9.0-alpha.1 PG3b: batch items are decided in memory and written in bulk. The create, update and
  upsert items of an inline batch or a background chunk are checked one after another by their
  single writes' rules, each against what the items before it left, and the accepted ones are
  written together: records, attribute values, relations, relation-set versions and one audit
  event per item, each kind in multi-row statements. A chunk now costs 30–49 statements for 100 or
  500 items, at two dataset sizes (a live upsert item alone cost about 20), and a chunk of 500 items
  takes 0.25–0.46 s; a live write beside a background job waits that long at most. Items are
  refused with the same codes, messages and details as their single writes, and single writes go
  through the same code as a batch of one. Delete items keep their per-item path. A bulk write that
  fails on a row the rules could not see, such as an ID another workspace took meanwhile, is redone
  item by item, so only that item is refused. An `atomic` job looks for a cancel request before
  every 500 items and before it writes, instead of before every item, and still rolls back
  completely. A chunk checks its model release before it writes relation matrix states, so an
  activation that removes a matrix view can no longer deadlock with it; the chunk fails
  `model_release_changed`.
- Base 0.9 B1: a change set write's record lookups probe the change set's own rows by key instead of
  listing all of them on every statement, so a write costs the same however many records the change set
  holds (a lookup took 361 µs at 4,000 own rows, now 39 µs; page reads unchanged or faster). On SQLite,
  a write waits up to `SQLITE_LOCK_WAIT_SECONDS` (60) for another transaction's writer lock instead of
  failing after the driver's 5 s.
- Base 0.9 B2: a live write's unique-value check and a record reference by key seek to the value
  through a new index (`ix_attribute_values_key_text`) instead of reading every value of the
  attribute, so their cost no longer grows with the records holding it (creates into a workspace
  gaining 30,000 records went from 2.3 to 5.2 ms each; now a flat 2.0 to 2.1 ms).

- Backend boundaries (E1–E3, [record](docs/BACKEND_BOUNDARIES_PLAN.md)). `backend/app` is split into
  tiers: `common/`, `engine/` (no FastAPI, no API schemas), `management/` (the `/api/v1` routes,
  schemas, presenters and projections) and the `consumer/` slot, checked by `tests/test_boundaries.py`
  with no exceptions, no import cycles and no function-level imports. The write rules are written once
  (`engine/records/rules.py`) and read live data or a change set through a lookup; where the two
  contexts word a refusal differently the difference is one entry in `engine/records/refusals.py`,
  pinned by `tests/test_rule_parity.py` (31 violations, both contexts, two models). Every record,
  relation and attribute-value row is written through `engine/records/writes.py`, the seam F1's feed
  position goes into. The live and change-set mapping replacement is one flow, and `change_sets` is a
  package. Both OpenAPI documents are unchanged. When one request breaks two parent or relation rules,
  which one is reported can differ from before.
- A live page's ancestor paths read only the columns a path shows, not whole records. A page of deep
  records loaded 163 ORM rows for 20 records and now loads 84, on the per-type list and the lookup alike.

- 0.9.0-alpha.1 PG5: every volume budget re-measured on PostgreSQL. Statement and row budgets hold
  for every read; 143 of the 154 full-volume reads stay within 100 ms. The eleven over it (change-set
  matrix state filters, change-set searches matching nearly every record, the attribute sort under a
  20,000-child parent, the live history-only matrix filter) are deferred to the first fixes after
  1.0; `docs/POSTGRESQL_BUDGETS.md` holds the figures, causes and fix plan. Batches: 1,000 upserts in
  0.8 s, 10,000 atomic creates in 5.4 s live and 17.8 s in a change set, 100,000 background items in
  52 s live and 64 s in a change set (on SQLite 231 s and 663 s), with writes beside the job waiting
  0.35 s at most.
- 0.9.0-alpha.1 PG5: search reads trigram indexes on record names as well as values (revision
  `20261003_01`). The per-type list reads a search's candidates first and, with at most 1,000, reads
  only those records, in live data, a change set or a publication: a name or code search with its
  total over 100,000 records takes 12–23 ms in every context (was 50–226 ms on PostgreSQL before).
  Results are unchanged; a search matching very many records, or of one or two characters, matches
  every record as before. A search costs one statement more.
- 0.9.0-alpha.1 PG5: the relation matrix's state filter sends its matching rows to the database once
  per statement instead of once per part of it (change-set filters 210 → 136–154 ms), and the query
  constructs written to steer SQLite's planner are removed, which made change-set object pages, the
  ancestor criterion and history sorts faster on PostgreSQL (for example the ancestor criterion in a
  change set 141 → 69 ms).
- 0.9.0-alpha.1 PG5: version 0.9.0-alpha.1 (backend, API document, frontend package).

### Fixed

- 0.9.0-alpha.1 PG5: a 20-row relation expansion of a record with 20,000 relations
  (`expand` in the model query) took about 0.4 s on PostgreSQL: it walked the name index over every
  record of the workspace until 20 belonged to the record. It reads the record's relations first and
  their records by ID: about 70 ms.
- 0.9.0-alpha.1 PG5: a change-set read right after the change set was started from current live data
  could take seconds: on rows without statistics yet, PostgreSQL looked up each record's attribute
  value through an index that read every value of the attribute. That redundant index
  (`ix_snapshot_attribute_values_owner_key`) is dropped in revision `20261003_01`.
- The background job worker no longer spins when its database is unreachable. A failed first pass
  left its next sweep in the past, so it retried without waiting and logged a full traceback on
  every pass (3,111 attempts in half a second in the regression test; a 28 GB log overnight). It now
  waits its 2 s between retries, logs the traceback once per outage, then one line a minute, and
  says when the database is reachable again.
- The volume tests' statement counts no longer include the background job worker's own statements,
  which made a restructuring budget test fail when a run was slow.
- `python -m app.cli.model_schema_upgrade --help` names every supported schema (0.5–0.8); it
  named 0.5–0.7 while it also accepted 0.8.
- Startup refused with an unsupported model schema named the supported schemas as 0.5–0.7; it names
  every supported schema (0.5–0.8).

## [0.8.0] - 2026-09-29

### Added

- Base 0.8 R1b and R2 (2026-09-29): build acceptance of B5, B5b and Milestone C in one pass. The full
  backend suite, Vitest, all 22 browser runners and the accessibility and visual gates pass with no fix
  or re-baseline, and no migration is needed, so 0.8.0 is released (D43).
- Base 0.8 S1: a Track S volume fixture and read baseline. `tests/volume_fixture.py` generates a model
  with its own keys and bulk-seeds 10,000 root records, 100,000 contained records (20,000 under one
  parent), a seven-level self-hierarchy, a record with 1,500 relations of one type and a parent with
  children of two types, then records revision 1 and derives a draft with scattered edits, tombstones
  and new records. `tests/volume_baseline.py` measures time, SQL statements and ORM rows per request
  in live, draft and history contexts; the full-volume figures and the budgets are recorded in the
  Base 0.8 plan. The new `volume` test group holds the budgets at two scales: live reads and writes
  meet them, while draft/history reads and draft writes are strict expected failures until S2.
- Base 0.8 S2: draft and history reads in SQL. Migration `20260925_01` adds
  `snapshot_attribute_values`, a typed index of revision, draft-base and draft object values (D1),
  backfilled from existing rows and kept current by an ORM flush hook, plus ordered page indexes on
  revision and draft-base objects. Object pages, single records, attributes, relation pages and draft
  write responses read one base-plus-overlay statement instead of the whole draft or revision; at full
  volume a draft page takes 3–6 ms (was about 3.1 s) and a history page 2–5 ms (was 1.1–2.6 s). Live,
  draft and history share one object query builder, held by a parity test across all four contexts.

- Base 0.8 S3: cursor and position paging on every collection endpoint (ADR-030). Pages add
  `prevCursor`, an `anchor` that reopens the page, and with `includeTotal=true` a `totalCount` and
  `startIndex`; requests add `from=end`, `position=N` and, on object, relation and mapping-coverage
  lists, `seek=<value>`. Selecting a page two ways is refused with `422 conflicting_page_parameters`.
  Existing cursors keep working.
- Base 0.8 S4: `topLevel=true` on object lists pages records without a parent in every context;
  relation lists gain `search` (the related record's name and searchable fields) and `sort` (`name`,
  and `createdAt` live) in live, draft and history. Migration `20260925_02` adds (owner, endpoint,
  relation ID) indexes on revision, draft-base and draft relations, so a draft or history relation page reads the
  record's own relations instead of the whole revision.
- Live object page indexes (migration `20260925_03`): (workspace, type, name, sequence) and
  (workspace, parent, type, name, sequence). Name-ordered live pages past the first, their totals and
  position reads now seek instead of scanning the type: 2–13 ms at full volume (a deep position read
  took about 500 ms).

- Base 0.8 S5: continuous-scroll lists (ADR-030). `useCursorWindow` keeps at most five pages,
  prefetches one page ahead of either edge and evicts the page furthest from the viewport;
  `ui/ScrollWindow` keeps rows still as pages arrive above them, shows quiet start and end markers
  and a loading marker only while the user waits, and offers a proportional scrollbar sized from the
  total (a click or a drag's release sends one position request), a page field, start and end
  buttons, Ctrl+Home/Ctrl+End and, on the collection lens, **Go to** a value. Arrow keys move
  through rows across page boundaries. Adopted by the collection lens, record panels (which gain a
  sort, by name by default), relation panels (which gain search and sort), the mapping lens, the
  mapping candidates and the object picker, now a search field over a listbox.
  `tests/volume_seed.py` seeds the volume fixture for the new `test:browser:s5` runner.
- Base 0.8 S6: the sidebar record tree reads by parent. Each root (`rootCreatable`) type of the
  application pages its top-level records (`topLevel=true`) in its own bounded, scrolling group;
  expanding a record pages each child type separately with `parentObjectId`, headed by the type and
  its count, and collapsing releases the branch. **Load more objects** and the global per-type load
  are gone, and with them the record with an unloaded parent drawn at the top level. The tree is a
  `role="tree"` with one tab stop, `aria-setsize` and `aria-posinset` from totals and arrow keys that
  load across a window's edge. Search lists matching records of every type with their ancestor path.
  `ui/ScrollWindow` reads only its own rows, so windows nest, and gains a `group` role for rows owned
  by an enclosing widget. New runner `test:browser:s6`.
- Base 0.8 S7: composed Track S acceptance. New runner `test:browser:s7` walks one collection-lens
  journey per context (scroll, scrollbar click, seek, end, page number, copied URL) over the volume
  fixture and the starter model, checks each landing against the same context's API read, and opens a
  record deep in the tree; it passes at full volume (`S7_VOLUME_SCALE=1`). The accessibility and
  visual gates gain a `scrolling-list-tree` scenario in light and dark, and every visual baseline was
  refreshed after review. `volume_baseline.py` adds a whole-type name search and a deep record read.
- Base 0.8 S8: indexed search (D25). Migration `20260926_03` adds SQLite FTS5 trigram indexes over
  live and snapshot text values, kept equal to the values by triggers on every write. A search of
  three or more characters looks up values only for the records the index names, and still decides
  with the same case-insensitive "contains" match, so results are unchanged in every context. A
  whole-type name search with its total at 100,000 records takes 37 ms live, 73 ms in a draft and
  40 ms in history (was 0.7–0.9 s). Names stay on the (type, name) index; one- and two-character
  searches, and phrases in more than 10,000 values, read each record as before.
- Base 0.8 W6: delete an unused workspace to correct a mistyped key (ADR-019 amendment, D27).
  `DELETE /workspaces/{key}?expectedVersion=N` removes a workspace that is not the default, was never
  published and has no objects or change sets, active or retired; the key can be created again. It
  refuses with `workspace_is_default`, `workspace_has_publications`, `workspace_not_empty` (with
  counts) or `version_conflict`, changing nothing, and is gated by `WORKSPACE_ADMIN_MUTATIONS_ENABLED`.
  Single-workspace responses add `deletable` and `deleteBlockedBy` (OpenAPI lock re-baselined). The
  Workspaces screen offers **Delete…** with a confirmation naming the key, or says why it cannot.
- Base 0.8 A1: the schema 0.7 `relationMatrix` view contract (D8, D9). Rows are records of one type,
  columns the records of a type that can contain the cell type at some depth, and a cell the row's
  related records through one binding, read from either end (`direction`), required or optional, of
  any cardinality. A view declares `rowColumns`, `columnLabelField`, `cellFields`, `searchFields` and a
  closed `cellActions` set (`create`, `edit`, `link`, `unlink`); an action that could never succeed for
  the model is refused. Each failure points at the failing config node, and schema 0.5 and 0.6 models
  refuse the view at its `type`. The view groups as a lens of its row type's collection and renders a
  placeholder until A4. The starter (still content 0.8.0) configures it three ways: codelist and
  master-value translations by language, codelists by system and master values by system; the
  translations and systems applications now include codelists.
- Base 0.8 A2: `GET /api/v1/workspaces/{workspaceKey}/relation-matrix` reads a `relationMatrix` view in
  live, change-set and publication contexts. Rows page like any collection (cursor, position, seek,
  totals), searching the view's `searchFields`; columns are named with `columnIds` (at most 20) or
  paged by name with their own cursor (D10). Each cell reports `one`, `several` (with `conflict` when
  the binding's uniqueness scope is the column type), `inactive`, `historyOnly` or `none` (D11), with
  counts, up to five records with their `cellFields`, versions and relation IDs, and each row its
  relation-set version. `state` with `columnIds` filters rows across the whole list before paging, by
  one recursive walk down from the selected columns (D12); at full volume the filter is over its time
  budget (seconds), a temporary exception that A3b's stored cell state removes (D12). A page costs a fixed number of statements.
  The volume fixture gains a `vol-matrix` application (30 columns, a three-level container hierarchy,
  150,000 cells at full scale, an outgoing conditioned and an incoming many-to-many matrix), measured
  with the other reads; the generated model is now schema 0.7. Object query builders accept a
  view's search fields and an ID predicate that also narrows a change set's overlay parts.
- Base 0.8 A3: writes from a relation matrix cell, live or in a change set, through the generic
  object and relation APIs. `GET …/relation-matrix/containers` lists where a new cell record can go
  (the column record and the records under it that can directly contain the cell type, with their
  path), naming the column's only container as `defaultContainerId` (D13).
  `GET …/relation-matrix/link-candidates` lists the cell-type records under a column record for a
  row, the ineligible ones with a reason (`alreadyLinked`, `rowCardinality`, `candidateCardinality`,
  `scopeTaken`). Relation create and delete accept an optional relation-set claim
  (`expectedRelationSetVersion`, `relationSetDirection`) and refuse a stale one with
  `409 relation_set_version_conflict`; a claimed create returns the set's new version. Cell records
  carry `relationVersion`. OpenAPI lock re-baselined; the paging inventory counts 20 collections.
- Base 0.8 A3b: stored relation matrix cell states (ADR-033). Migration `20260927_01` adds
  `matrix_cell_states` and `matrix_state_builds`; the application builds every missing owner (live,
  publication, change set base, change set overlay, publication history) and matrix shape at startup,
  on model activation and when change sets and publications are created, and recomputes the rows a
  write touches before it commits. The row state filter reads them by index, once per request, and
  derives cells from records only where a context is not built. The API contract is unchanged.
  `matrix_states.verify` rebuilds and compares every stored state; matrix tests run it after each test.
- Base 0.8 A4: the relation matrix lens replaces the A1 placeholder. Rows scroll as every list does,
  the row header stays pinned with the view's row columns, and columns are the ones chosen in the
  Filter popover or a page of the column type, paged sideways. Each cell shows its state with an icon
  and a label, explained by a legend of the states the binding can produce. The Filter popover chooses
  the columns (searchable) and a cell state; both live in the URL. The grid is keyboard operable
  (arrow keys across cells and pages, Enter to open). A cell's dialog offers only the view's
  `cellActions`: create (the column's only container preselected, otherwise a searchable picker;
  **Create from this** for a history-only cell), edit, link (candidates listed with the reason any
  cannot be linked) and unlink, live or in the selected change set, and read-only in a publication.
  A save re-reads only that cell. `ScrollWindow` keeps a grid cell's column on Up and Down. New
  browser runner `test:browser:a4`.
- Base 0.8 A5: Milestone A acceptance. Browser runner `test:browser:a5` runs SC-09's translation half
  by keyboard (fill a missing translation live, a refused duplicate, restore one from history in a
  change set and publish it from the change set screen), links and unlinks a system value, and fills
  a cell on the generated volume model. The accessibility and visual gates gain the relation matrix,
  its cell dialog and Filter popover in light and dark, with four reviewed baselines. Full-volume
  matrix reads measure 23–82 ms in every context, within the 100 ms budget.
- Base 0.8 B1: the schema 0.7 `tree` view contract (D9). A tree declares its `rootObjectTypeKeys`, the
  node types it shows (`objectTypeKeys`), a `labelField`, an optional `secondaryField`, a `childSort`
  per node type, a `pageSize` and a closed `actions` set (`createChild`, `rename`, `move`,
  `setAvailability`, the last with a boolean `availabilityField`). A node type unreachable from the
  roots through the types the tree shows, a root type that cannot stand without a parent, a field
  missing from a node type and an action that could never succeed are each refused at the failing
  config node; schema 0.5 and 0.6 models refuse the view at its `type`. The view groups as a lens of
  its first root type's collection and renders a placeholder until B3. The starter (still content
  0.8.0) adds a system hierarchy (systems, recursive system groups, system values) and a domain
  hierarchy (domains, codelists, master values); the generated volume model adds one over its groups,
  items and deep node self-hierarchy. The Domains and Systems tables gain a lens switch; four visual
  baselines were updated after inspection.
- Base 0.8 B2: move targets. `GET /api/v1/objects/{type}/{id}/parent-candidates` lists every record of
  a type that can contain the record, in its application and workspace, live or in a change set, in
  name order with search, cursors, positions and totals. A candidate the move would refuse or not
  change stays listed with `eligible: false` and a `reason` (`self`, `descendant`, `currentParent`;
  D14), and every candidate carries its root-first `path`. The generated volume model lets groups
  nest, so a record with 20,000 records under it can move.
- Base 0.8 B3: the tree lens replaces the B1 placeholder. It shows the view's root types, and under
  each record one branch per child type the tree shows, ordered by the view's `childSort` and paged by
  its `pageSize`, with the `labelField`, `secondaryField` and, where declared, the availability field.
  It reuses the sidebar tree (S6): bounded scrolling branches, totals, one tab stop and arrow keys, plus
  type-ahead (a space typed mid-word continues it). A search result, and the record open beside the
  tree (also after a reload, Back or Forward), is revealed where it sits: each branch on its path
  opens at it with `seek`, and unrelated branches stay closed. Records open in the inspector beside
  the tree (the retained split view), full width below 1080px. The view's `actions` come from a node's menu
  (Shift+F10, the context menu key or the row's ⋯): add a child of each type the node can contain (the
  new node appears in its branch with focus), rename in place (F2), set availability (also the row's
  switch) and **Move to…**, a dialog over the B2 candidates where ineligible targets are listed
  disabled with their reason; a move keeps focus on the moved node and refreshes both branches. A
  refused write keeps the user's input and place. Writes go to the selected change set; a
  publication's tree is read-only. New browser runner `test:browser:b3`.
- Base 0.8 B4: Milestone B acceptance. Browser runner `test:browser:b4` runs SC-09's hierarchy half by
  keyboard on the system hierarchy (live, 1440px) and the domain hierarchy's nested master values
  (live, 390px): find a nested record reading only its ancestors' branches, add a child and a
  grandchild, be refused the move beneath the grandchild in the dialog and by the API, move the child
  and see its new path in the tree and breadcrumb with its containment edge changed and unrelated
  branches unchanged. A move staged in a change set reaches live only when the change set is
  published. The accessibility and visual gates gain the tree lens and its move dialog in light and
  dark, with four reviewed baselines. The tree lens's keyboard helpers are shared by both runners
  (`e2e/helpers/tree.mjs`).
- Base 0.8 P2a: change lists. `GET /api/v1/change-sets/{id}/object-changes` and
  `/relation-changes` list only what a change set changes, read against its source: each record or
  relation it touched as `added`, `changed` or `removed` (D31), with `before` (the source's row) and
  `after` (the change set's), typed values in the object read's shape, `changedFields` and, for
  records, the path. A record created and deleted inside the change set is left out, as publishing
  skips it; one edited back to its source values stays listed with no changed fields. Relation
  entries name both ends and mark engine-maintained parent edges with `containment` (D32), so a move
  is a `changed` record with `parent` plus one removed and one added edge. Filters by kind, type and
  containment; every paging mode. The volume fixture gains a review change set touching 12,073
  records and 8,273 relations at full volume, where every measured page takes 3–52 ms in 4–6
  statements.
- Base 0.8 P2b: change set review screen. **Review changes** on the change set bar (and a link in the
  publish confirmation) opens `/apps/{app}/change-sets/{id}/changes`: **Records** and
  **Relationships** tabs, each a continuous list of what the change set adds, changes and removes, with
  a kind badge in words, the type and model labels from the change set's model, the path or both
  ends, and the changed fields. A row expands to a before/after table of those fields with typed
  values as the record screen shows them; a moved record names its old and new parent. Added and
  changed records open in the change set. Filter by kind and type; parent links are hidden from
  Relationships unless asked for (D32). Tab, filters and scroll position live in the URL. The object
  change entry gains `beforePath`, where the source held a moved record, read in the same walk as
  `path`. New runner `test:browser:p2`; the accessibility and visual gates gain the review in light
  and dark.
- Base 0.8 B5: drag and drop in the tree lens, a second way to **Move to…** for mouse and pen where
  the view allows moves, live and in a change set. Drop onto a record, into a gap between rows (the
  branch the gap belongs to; at a branch end the pointer's horizontal position picks the level, shown
  by the drop line's indent) or onto a type heading (its parent). While dragging, the record's row is
  dimmed and a preview names it; an accepted target glows green, a refused one red with its reason as
  text (**The record itself**, **Inside the record**, **Current location**, **Can't contain …**,
  **In another application**) and a no-drop cursor. Resting on a collapsed record opens it, and the
  tree scrolls near its edges. A drop opens the move dialog with the target chosen, so Enter confirms
  the same write as Move to…; Escape or a release elsewhere writes nothing. Touch pointers, the
  sidebar tree and publications never drag (touch drag in 0.11, D35). `test:browser:b3` gains the
  drags; the accessibility and visual gates gain a drag over an accepted and a refused target, light
  and dark.
- Base 0.8 B5b: moving a record to the top level from the tree lens, by both paths (D36). **Move to…**
  lists **Top level** above the candidates, outside the paged list, and confirming writes no parent.
  Dragging onto a top-level heading, into a gap between top-level rows or to the left end of a gap
  that ends branches down to the top level offers it too, and the drop opens the dialog with **Top
  level** chosen. Only a nested record of one of the tree's root types goes there; any other type is
  refused as **Not shown at the top of this tree**, and a record already there as **Current
  location**. A search's matches offer no top level. `test:browser:b3` moves a nested group of the
  generated volume tree to the top live by Move to… and in a change set by a drag.
- Base 0.8 C1: a record's type can change in a change set (ADR-034). `services/type_changes.py`
  changes one record's type, optionally under a new parent, with a given attribute mapping: values
  are kept, mapped (same value type, or `text` to `longText` and `integer` to `decimal`), restored or
  given as inputs, and the rest have no place; the containment edge becomes the relation the model
  allows, and each child's edge the relation the new type contains it by; relationships the new type
  may not have are removed and the others keep their IDs; relationships offered back are restored
  under their former IDs, and required relationships are inputs. Uniqueness, required values and
  relations, uniqueness scopes, cycles and the record version are checked by the change set write
  services, and `check_type_change` runs every check without keeping a write. Each change records a
  `reclassified` audit event with the full before state, which the history read lists with
  `changedFields` and `attributeTypeKeys`. Publishing needed no change: it writes the new type to
  live and refuses a live edit of the record or a live relationship the new type cannot have. The
  restructuring API that exposes the service is C3.
- Base 0.8 C2: the restructuring planner (`services/restructuring.py`) plans a move or a type change
  of one record and its subtree in a change set. It works out the possible types at the target and
  asks once per (type, parent type) pair where several are possible; cascades level by level, each
  child the new parent cannot contain becoming a type it can; suggests each attribute's source by the
  D40 rules, which a choice per type pair overrides; and lists per record what is kept, mapped,
  restored, given or without a place, the inputs still needed and the refusals. Values and
  relationships are offered back from the record's reclassifications in the current change set and in
  published ones, relationships under their former IDs. A ready plan is dry-run through the change set
  write services and rolled back; its digest binds an apply to the previewed plan and the change set
  version. More than 500 records is refused with `restructuring_too_large`: D44 lowers C0's 5,000
  because the dry run takes 48 s at that size and 2.8 s at 500. The routes are C3.
- Base 0.8 C3: the restructuring API. `POST /api/v1/change-sets/{id}/restructurings/preview` plans an
  operation and writes nothing; `POST /api/v1/change-sets/{id}/restructurings` applies it when the
  recomputed plan matches the previewed `planDigest` and the change set is still at
  `expectedChangeSetVersion` (`409 restructuring_plan_changed`, `409 change_set_version_conflict`,
  `422 restructuring_not_ready`). Five kinds: `move` (with a type change where the target needs it),
  `changeType`, `insertLevel` (a new record between a parent and chosen children, its values given
  under the ID `new`, its ID returned as `createdObjectId`), `removeLevel` (a record deleted with its
  relationships, its children moved to its parent, changing type where needed) and `changeTypeUnder`
  (every record of one type under a record). The plan's records page by position in plan order with
  the standard page links, filtered by `outcome`; cursors bind the change set version and the plan.
  Parent candidates take `includeTypeChanges=true` in a change set, listing the records a move with a
  type change could go under, each with `objectTypeKeys`.
- Base 0.8 C4: restructuring in the tree lens, in a change set only. **Move to…** and a drag also
  offer places where the record's type cannot stand but another type of the tree can: the candidate
  and the drag say **Becomes <type>**, and choosing one opens a preview instead of moving. The node
  menu adds **Change type…**, **Insert level above…**, **Remove this level…** and **Change type of all
  <type> in here…**, each only where the model makes it possible. The preview shows the plan by
  record (new type and place, each value's origin, what has no place, what is restored, inputs asked
  in place) and by type pair (each attribute's source changeable in place), answers type questions,
  lists refusals, applies the reviewed plan and links to the change set's review. **Insert level
  above…** lists the record's siblings to choose more records to group under the new level.
- Base 0.8 C4 (D45): `GET /api/v1/model/placements` serves where the context's model lets records
  stand, per application: the types at the top and, per parent type, the types it contains and the
  types a record can become under it. It is the engine's one rule (`services/model/placements.py`);
  the browser loads it with the model and no longer derives containment itself.
- Base 0.8 C4: parent candidates take a repeatable `withinObjectTypeKey`, keeping the candidates and,
  with `includeTypeChanges`, the types the record would become to a set of types; the server filters,
  so totals stay truthful. The tree lens passes its types, so Move to… offers what the drag offers.
- Base 0.8 C5: Milestone C acceptance. `test:browser:c5` runs the restructuring journey on the starter
  model and the generated model against a real backend: a move that reshapes a subtree across two
  levels of types, answering the preview in place, inserting and removing a level, the review,
  publishing from the change set screen, live, the publication and both ends' history, then changing a
  record back in a second change set with its values or its relationship restored. The accessibility
  and visual gates add Move to… with a type change, the preview by record and by type, and the insert,
  remove and change type dialogs, light and dark. User story US-H03 and scenario SC-17.

### Changed
- Base 0.8 C4: the change set review names a record's type change on its row and as **Type** in its
  before/after table. The browser follows a record opened under a type it no longer has to its
  current route (D42), replacing the old route and keeping focus. In a change set, a tree lens record
  dragged to a place its type cannot stand, such as an item to the top level, now becomes a type that
  can (B5b refused it); live, such a place's reason adds that a change set can change the type. A
  cursor list's reload whose anchor went stale reopens at the start instead of failing.
- Base 0.8 C1 (D42): every `/objects/{objectTypeKey}/{objectId}` route answers
  `409 object_type_changed` with the record's current type for a record found under another type in
  the selected context, live, in a change set or in a publication, where it answered `404
  object_not_found`. A change-set `PATCH` now checks the route's type, which it ignored. The change
  lists' object entries carry `objectTypeKey` on `before` and `after`, name `objectType` first in
  `changedFields` when it changed, and the `objectTypeKey` filter matches either side; a relation
  entry is `containment` by the type its `to` end has on either side.

- Design: Base 0.9 integration APIs. Decisions D1–D16 and CONSUMER_API C-D2–C-D16 are accepted. A code
  check revised D5: the feed is positioned by a per-workspace counter taken under the workspace lock
  until commit, so feed order is commit order on PostgreSQL too; and added D15 (a publish writes one
  audit entry per record it applies to live) and D16 (feeds carry keys, never the `reclassified`
  before state). `docs/INTEGRATION_API.md` gains sections B (batches with record references, upsert,
  relation items and relation-set replacement), F (the workspace change feed, position, retention and
  `410` recovery), Q (cross-type lookup, `/workspaces/{key}/relations`, the model-aware query and
  `asOf`) and J (import with preview and confirm, the file contract, the import profile with a generic
  `relatedRecord` binding, and export). APPLICATION_MODEL describes schema 0.8 (`effectivePeriod`,
  `consumerApis`). ADR-036 (a batch is a job), ADR-037 (the audit log orders the feed and consumer
  events) and ADR-038 (effective periods) are accepted.
- Planning: the Base 0.9 plan follows the 0.8 layout: how a package is delivered, a numbered delivery
  queue with dependencies and the D9 cut line, and work packages Q1–Q4, B1–B3, F1–F2, V1–V2 and
  J1–J4 with design references, scope, tests, budgets, test groups and exits, the C1–C16 table and R
  build acceptance. New test groups `jobs`, `feed` and `consumer` and runners `test:browser:v1` and
  `test:browser:j4` are planned. The API reference track is renamed V.
- Design: Product 0.10 is model authoring and spreadsheet onboarding (ADR-035,
  `docs/MODEL_AUTHORING.md`): one editor for the model and the import mapping, where every edit is a
  validated operation on a model draft, inference from an uploaded workbook proposes operations, and
  saved import profiles load the next version as a reviewed upsert. Production hardening moves to
  0.11 and security to 0.12 across the documentation; 1.0 keeps changes to released structure,
  protected publishing and extensions. 0.9 D3 is revised: import runs an import profile, with XLSX.
  New stories US-P09 and US-P10. A-D1–A-D3 decided (one type per list, declared navigation groups,
  profiles stored apart from releases). `docs/BASE_0_10_IMPLEMENTATION_PLAN.md` is the provisional
  0.10 plan: packages A0–A8 and R, synthetic acceptance workbooks, decisions D1–D10.
- Design: Base 0.8 C0. ADR-034 accepts that a record's type can change, keeping its ID, in a change set
  only, within its application. The attribute mapping is derived from the model (same value type or a
  lossless widening), relationships are kept or removed, and descendants follow level by level. An
  operation is previewed, then applied against the change set version and the plan's digest. Each type
  change records a `reclassified` audit event with the full before state, and later type changes offer
  its values and relationships back. A route naming another type than the record's returns
  `409 object_type_changed`. One operation changes at most 5,000 records. API.md gains the restructuring
  API design (`/change-sets/{id}/restructurings[/preview]`). D37–D43 are accepted; 0.8.0 now waits for
  Milestone C and R2 (D43).
- Planning: Base 0.8 Milestone C, structure refactoring (C0–C5, R2 build acceptance), for delivery before
  0.9. A record's type changes when it moves where only another type is allowed. The new type and the
  attribute mapping are derived from the model, with no declarations, and confirmed in a preview.
  Values without a place stay in history and are offered back later. Named refactorings (change type,
  insert or remove a level, change type under a record) run in a change set. D37–D43 are open.
- Planning: Base 0.8 B5, drag and drop in the tree lens, added in the Milestone B review. Records can be
  dropped onto a node, into a gap between rows or onto a type heading. Drops are accepted by the
  model's containment rules, show a green or red glow with the reason, and are confirmed in the
  existing move dialog. D34 decides the targets and the confirmation; D35 defers touch drag to 0.11.
  B5b, an amendment to B5, adds moving a record to the top level in Move to… and by drag, for the
  tree's root types (D36). R1b is added as an amendment to R1: the build acceptance for B5 and B5b,
  required before 0.8.0 releases. One record is moved at a time.
- Documentation: the bundled model is described as an example set. `docs/EXAMPLE_MODEL.md` explains
  how engine, model and application relate, lists the views each example application declares and
  explains why they differ (only the example's declarations, never the application). It also shows
  what each gap would take. README, AGENTS, PRODUCT, APPLICATION_MODEL, UI_MODEL and the functionality
  catalogue state that every application gets the same feature set. Milestone A is named the Relation
  matrix throughout, with ADR-031 and the W1 note amended.
- Base 0.8 B3: the sidebar tree's tab stop returns to the open record once it is drawn, unless the
  user has since focused another item; it also gains type-ahead. A record's inspector re-reads the
  record when the collection beside it writes, and a narrow inspector wraps the record's actions
  below its title.
- Base 0.8 B2: moving a record costs about what a rename does, however much lies under it. A live
  update re-checked ancestor-scoped uniqueness for every relation into the record's whole subtree on
  every write, rename included; it now checks nothing for a rename, the record's own relations for a
  value change, and after a move only the records below whose scope record is above the moved one,
  for bindings that declare a scope. Stored matrix cell states no longer walk down from a moved
  record that can hold no cell below a column, recompute a written relation's ends only in shapes of
  its relation type, and find a cell record's rows by its own endpoint index. Moving the
  20,000-descendant record at full volume takes 6 ms live (was 773 ms) and 13 ms in a change set (was
  53 ms), and a change set rename 8 ms (was 17 ms). Moving a container of about 2,500 matrix cells
  stays seconds in both contexts and is a known 0.8 budget exception (D29).
- Base 0.8 A6: a migrated database now has the schema the ORM declares (D28). Ten single-column
  indexes declared on publication and change set tables were never created by a migration. Migration
  `20260928_01` gives `change_set_objects` the (owner, type, name, object) and (owner, parent, type,
  name, object) indexes the publication and base object tables have, so relation matrix walks through
  a change set seek children by parent instead of building an automatic index per statement; the
  other eight declarations are removed because owner-leading indexes already serve every read, and a
  database built by an earlier `create_all` loses them on upgrade. New `test_schema_drift` fails on
  any difference between a migrated head and the metadata. Volume budgets and statement counts are
  unchanged.
- Base 0.8 A5: a relation matrix cell refused for uniqueness says so in the view's terms, naming the
  row, the column (or the scope) and the condition, for example "Delivery Methods already has a
  translation in cs where Active is Yes, and only one may count there.", instead of the API's generic
  "A related object already exists for this ancestor scope". The API is unchanged.
- Base 0.8 A3: relations an object create adds through `initialRelations` now advance both ends'
  relation-set versions, live and in change sets, like every other relation write (ADR-022); a
  matrix row's `relationSetVersion` therefore counts them. `409 duplicate_relation_scope` on relation
  and object writes names the record already in the scope (`conflictingObjectId`,
  `conflictingRelationId`); the change set diagnostic adds `conflictingObjectId`.

- Base 0.8 W4: a global **Workspaces** screen beside **Models**, in the same list-and-detail layout,
  lists every workspace including retired ones and creates, renames, retires, reactivates and sets
  the default with their version claims; a conflict shows the current state and is never retried.
  It appears in the header, and as **Manage workspaces** in the workspace selector, only when
  `workspaceAdmin.manageWorkspaces` is true. The selector is a read-only label while one workspace
  exists. Models and Workspaces show the deployment capabilities read only, naming the setting of a
  disabled group, which `GET /capabilities` now reports in each group's new `setting` field
  (OpenAPI lock re-baselined). The narrow navigation drawer is titled for its screen. New browser
  runner `test:browser:w4`; the a11y and visual gates gain `workspaces-admin` light and dark, and
  every shell baseline was refreshed for the header entry and the single-workspace label.
- Base 0.8 W3: `WORKSPACE_ADMIN_MUTATIONS_ENABLED` gates only workspace create, rename, retire and
  set default (ADR-031). Change-set create, update, delete, model-release change, validation and
  publish, and publication withdrawal, are always registered and still refused in a retired
  workspace. Their OpenAPI tag is `change-sets`.
- Base 0.8 W2: data drafts are **change sets** and workspace revisions are **publications** in every
  layer (ADR-031), with no aliases. Breaking API changes:
  - Routes: `/workspaces/{key}/drafts` → `/workspaces/{key}/change-sets`,
    `/workspace-drafts/{id}` → `/change-sets/{id}`, `/workspace-drafts/{id}/activation` →
    `/change-sets/{id}/publication`, `/workspaces/{key}/drafts/{id}/model-release` →
    `/change-sets/{id}/model-release`, `/workspaces/{key}/revisions` → `/workspaces/{key}/publications`,
    `/workspace-revisions/{id}` → `/publications/{id}`, and `POST /workspaces/{key}/retirement` with
    `expectedActiveRevisionId` → `POST /publications/{id}/withdrawal` with no body (the path ID is the
    claim). Lists stay under their workspace; single items are flat by global ID.
  - Fields and parameters: `workspaceDraftId` → `changeSetId`, `workspaceRevisionId` →
    `publicationId`, `expectedWorkspaceDraftVersion` and `expectedDraftVersion` →
    `expectedChangeSetVersion`, `workspaceDraftVersion` → `changeSetVersion`,
    `expectedActiveRevisionId` → `expectedActivePublicationId`, `derivedFromRevisionId` →
    `derivedFromPublicationId`, `supersedesRevisionId` → `supersedesPublicationId`, `revisionNumber`
    → `publicationNumber`, `activatedAt` → `publishedAt`, `retiredAt` → `withdrawnAt`, source
    `"revision"` → `"publication"` and publication status `retired` → `withdrawn`. A publication also
    returns `modelReleaseKey` and `modelReleaseVersion`.
  - Error codes: `workspace_draft_*` → `change_set_*` (`change_set_not_found`,
    `change_set_version_conflict`, `change_set_model_release_conflict`, `change_set_required`,
    `change_set_snapshot_retry`, `change_set_snapshot_unsupported`), `draft_content_incompatible` →
    `change_set_content_incompatible`, `workspace_revision_not_found` → `publication_not_found` and
    `workspace_active_revision_conflict` → `workspace_active_publication_conflict`.

  Migration `20260926_04` rebuilds the draft and revision tables as `change_set*` and `publication*`
  with their columns, indexes and constraints, renames `workspaces.active_revision_id` and
  `relation_set_versions.workspace_draft_id`, records snapshot value owners as `publication`, `base`
  and `change_set`, and rewrites stored audit names (`change-set`, `change-set-object`,
  `publication`/`published`, `publication-withdrawn`) and payload keys. It resumes an interrupted run
  on SQLite and refuses another dialect with a recovery instruction. The browser says "Change set ·
  name", "Publish change set", "Publication N" with its model release and date, and "Withdraw
  publication"; its URLs are `/apps/{app}/change-sets` and `/apps/{app}/publications` with
  `changeSetId` and `publicationId`. The OpenAPI lock is re-baselined, the `drafts` test marker is
  `change_sets`, and the WP9 runners are `test:browser:change-sets` and `test:browser:publications`.
- Base 0.8 W1: documentation adopts the ADR-031 terms. The glossary defines workspace, live, change
  set, publication ("Publication N" and its per-workspace number), model draft, model release, and the
  verbs publish, install, activate, withdraw and retire, with a diagram of one workspace's live data,
  change sets and publications and a note on the old names the code keeps until W2. Milestones A and B
  are renamed **Translation editor** and **Hierarchy editor** in the roadmap, TODO, the 0.8 plan and the
  functionality catalogue. The stale "non-default workspace detail gap" notes in PRODUCT, the product
  guide, user journeys, user stories and the functionality catalogue are corrected: 0.6 WP9 repaired
  the context handoff, and the WP9 navigation runner opens detail, children, relationships and
  history in a non-default workspace.
- Base 0.8 S8: a draft list's total counts its base, less the rows the draft replaces, plus its own
  rows, instead of the union (a total at full volume in 19–31 ms, was 45–56 ms); a first or
  position page that reaches the end of its list returns its total without a count.
- Base 0.8 S4R1: relation lists sort and search the related record through the object query
  builder, as object lists do. `sort` takes `name` (now the default in every context), any
  `sortable` attribute of the related type, `ancestor:<type>`, and live only the related record's
  `createdAt`/`updatedAt`; relation creation order is no longer a sort. Attribute and ancestor sorts
  need the listed relations to reach one object type (`422 invalid_sort` otherwise), and
  `relationTypeKey` repeats to list several relation types. Search covers the related types'
  searchable fields instead of every searchable attribute type. Draft and history object and
  relation pages return each record's `path` (it was empty, so ancestor columns were blank), and a
  relation page for a record the context does not hold answers `404` as it does live. Migration
  `20260926_01` rebuilds the draft and history relation endpoint indexes to cover the relation type
  and the other end. Relation cursors issued before the change are refused with `422 invalid_cursor`.
- Base 0.8 S4R2: schema 0.7. The engine accepts `schemaVersion: "0.7"` beside 0.5 and 0.6 in
  validation, the registry, releases, `model_schema_upgrade` and the startup message. Relations
  panels may declare `sortFields` and `defaultSort` (D21), validated against what the relation list
  accepts: `name`, a sortable attribute of the one related type, or an ancestor it can sit under;
  a 0.5 or 0.6 model declaring them is refused at the field's path, and absent fields stay out of the
  canonical document so earlier releases keep their hash. The starter model moves to schema 0.7,
  content release 0.8.0: its system panels sort by system, value code and name, its translation
  panels by language, translated name and name, and `translated-name` becomes sortable.
- Base 0.8 S4R3: one sort element for table-shaped lists (`ui/TableSort`), and one rule: every data
  column sorts. Column headers sort: a quiet sort icon on hover and focus (drawn in the header's
  padding, so columns never widen), an accent up or down arrow on the sorted column, activation toggling
  the direction, `aria-sort`, an accessible name stating the order and a polite announcement. Every
  list with sort fields shows the same icon-only **Sort** menu in its toolbar (radio items per field
  plus the direction, with a tooltip), which also reaches columns collapsed at 390px or hidden through
  Display and fields a view or panel declares without a column. The collection lens, record panels and
  relation panels use it. Removed: the lens toolbar's **Sort** popover and the relation panel's inline
  **Sort** select with its fixed name and creation-time options. `ui/ActionMenu` gains radio sections,
  a trigger icon and a tooltip.
- Sorting no longer depends on the attribute type's `sortable` flag: object and relation lists sort by
  any non-JSON attribute, and a relation list over several related types sorts by an attribute with
  records whose type lacks it last. `objectType` sorts by the type's model name and, on relation
  lists, `relationship` by the label each row shows, both then by name. The only data columns that do
  not sort are the computed path, JSON attributes and, outside live data, the unrecorded timestamps.
  Model validation follows: view and relations-panel sort fields accept any non-JSON attribute plus
  `objectType` and (panels) `relationship`, and a relations panel may declare `defaultSort` alone.
  The OpenAPI lock is re-baselined for the two `sort` descriptions.
- Collection URLs hold one `anchor` cursor for the page at the top of the list instead of a
  `cursor` trail, written as the user scrolls without adding history entries. Older links with
  `cursor` parameters open at the start. Previous/Next page buttons and **Load more** in panels,
  relation lists and pickers are removed.
- Page responses carry the new navigation fields beside `items` and `nextCursor`, so a client that
  compared a whole page body must allow them. Live relation pages build their related records in one
  batch instead of two statements per row.
- Draft and history `search` matches the record name and `searchable` fields, as live search does,
  instead of every attribute's text. Draft and history cursors issued before the upgrade are refused
  with `422 invalid_cursor`; restart from the first page.

- Base 0.8 S4R4: object lists without `sort` order by name in live, draft and history (live used
  creation order, drafts and history record ID), so the object picker and Explorer search results
  list by name and an unsorted list accepts `seek` by name. Mapping coverage and candidates list by
  name, and coverage `seek` takes a source name instead of an ID. Cursors issued for the former
  default orders are refused with `422 invalid_cursor`; reload from the first page.
- Base 0.8 S4R5: every page lists `items` first, then its navigation fields. `totalCount` and
  `startIndex` are omitted unless `includeTotal=true` instead of returned as `null`, and OpenAPI
  documents them as optional integers. Clients that tested them for `null` should test for absence.
- Base 0.8 S4R6: a draft position read resolves in its base's index and corrects for the draft's
  own rows, instead of skipping every earlier row through the base-plus-overlay union. Three quarters
  into a whole 100,000-record type it takes 60 ms (was 175 ms; about 40 ms of it is the total count), and
  its cost no longer grows with the position.

### Fixed

- Base 0.8 C5: change set validation, which publishing also runs, rescanned every record or relation
  for each record or relation in its uniqueness, parent-edge, cardinality, scoped-uniqueness and
  required-relation checks. Over the generated model at 2% volume (about 5,400 records) it took 125 s
  for an unchanged change set; it now reads indexes built once and takes about 1.4 s, with the same
  diagnostics in the same order.
- Base 0.8 C5: a record whose type changed and which was then removed in the same change set was
  listed in `object-changes` with `objectType` among its changed fields although it has no after side,
  and the review showed it as **<type> → Unknown type**. A removed record now names only the fields its
  source holds, in its source type's order, and the review names it by the type its source holds.
- Base 0.8 C5: after a restructuring, the tree lens moved focus to the restructured record once its
  reveal read returned, even when the user had gone on to the lens search meanwhile, so the rest of
  what they typed went to the tree. The record now becomes the tree's tab stop without taking focus
  unless focus is still in the tree.
- Base 0.8 C5: the restructuring preview's needs-input status began its second sentence in lower case,
  and values without a place showed booleans as `true`/`false` instead of Yes/No.

- Base 0.8 R1 review: the change lists (`object-changes`, `relation-changes`) read their page, then
  its paths and relation ends in further statements without holding one snapshot, so a change set
  write committed in between could mix two states in one page (a renamed parent in paths beside its
  own entry under the old name; after a concurrent publish, parent links without their end's type).
  Both routes now read one snapshot, as the relation matrix and parent candidates do.
- Base 0.8 R1: two browser runners no 0.8 package selected had drifted from the 0.8.0 starter model.
  `test:browser:sc15`'s incompatible candidate (a newly required `external-id`) was refused as a model
  because the `codelists-by-system` matrix offers `create` without it; the candidate now also asks for
  the field there, so it is refused for its data again. `test:browser:wp13c` asserted that RDM Systems
  offers no Codelist parent for a new master value, which the 0.8.0 model changes by adding codelists
  to RDM Systems; it now expects exactly the parent types the application contains, read from the model.
- Base 0.8 A review: when a relation matrix cell's edit or unlink was refused as stale and the re-read
  cell no longer held that record, the cell dialog went blank with no way on but Escape. It now shows
  the cell again with its actions and says the record is no longer in it. Starting another action
  from the cell clears the earlier notice.
- Base 0.8 A review: a relation matrix kept showing cells re-read after earlier saves over a page it
  had reloaded, so a cell changed elsewhere since could stay stale. The reloaded rows now replace
  them.
- Base 0.8 A1: a duplicate `mappingGrid` `sourceColumns`, `targetDisplayColumns` or
  `candidateSearchFields` entry was reported at `…/config/config/<field>`, a pointer to no node in
  the model; it is now `…/config/<field>`.
- Base 0.8 W6 review: on the Workspaces screen, creating a workspace after deleting one no longer
  leaves the "was deleted" notice above the new workspace.
- Base 0.8 W6: a live write that resolved its workspace before the workspace was retired, or deleted,
  could still commit into it. It now rereads the workspace inside its transaction and returns
  `409 workspace_retired` or `404 workspace_not_found`, saving nothing.
- Base 0.8 W5: a live write validated under one model release could commit after another release
  was activated, storing data the new release does not allow. The write now rereads the active
  release inside its transaction and returns `409 model_release_changed`, saving nothing; activation
  reserves the database writer before its compatibility check, and returns
  `409 model_activation_retry` if live writes keep it busy. Holds in one process and across
  instances sharing a SQLite database.
- Base 0.8 S8 review: the trigram search index is SQLite-only. Migration `20260926_03` changes
  nothing on another dialect (it stopped a PostgreSQL upgrade), and a search there reads each
  record's values as before S8 instead of naming the missing index table.
- Base 0.8 S2b: a draft write no longer loads the whole draft. Object, attribute, relation and
  mapping writes check only the records and relations they touch: the parent and its ancestors, the
  relations at each end, the draft-wide holders of a unique value through the typed value index, and
  for a deletion the subtree it removes. Renaming one record in a 100,000-record draft takes 7.5 ms
  (was 4.9 s). Migration `20260926_02` adds a value lookup index on `snapshot_attribute_values`. A
  unique attribute without a value no longer conflicts with records that lack it.
- A draft or history single-record read returned an empty `path`, so the record page showed no
  ancestors and the sidebar tree could not open the record's branch in those contexts. It now returns
  the ancestor path, as live reads and draft and history pages do.
- In the dark theme, a list footer's page field and **Go to** field kept the browser's light field
  colours and failed contrast; they now use the shared text-input treatment.
- Paging a list sorted by a boolean field past its first page returned a server error; keyset cursor
  positions are now bound as typed values. Keyset pages also seek to the cursor through the first sort
  key's index instead of scanning every earlier row.

## [0.7.0] - 2026-09-25

### Added

- Base 0.7 WP-9: composed acceptance for SC-07 and SC-15. `test:browser:sc07` resolves unmapped,
  differently mapped and 25-target ambiguous rows (candidates beyond page one, bounded previews with
  continuation), survives a racing generic relation write with the attempted choice kept, proves an
  independent binding with a typed relation attribute is untouched, and refuses draft activation when
  live changed the draft's mapping set. `test:browser:sc15` prepares one draft on an installed candidate
  release while another stays on the active one, refuses incompatible and unavailable releases without
  touching live data, history or another workspace, then publishes the prepared draft after the
  candidate is activated and discards the other. `test_build07_wp9_acceptance.py` adds corrupt and
  unsupported releases at the HTTP boundary. The browser harness accepts a model variant
  (`transformModel`).

- Base 0.7 WP-13C: `docs/testing/UI_ACCEPTANCE.md` names the existing reference pattern for each kind
  of UI element and inventories the states of every 0.7 surface with its evidence. The new browser
  runner `test:browser:wp13c` checks mapping and draft states against a real backend: outages with
  Retry, empty and no-match results, conflict review, the inverse mapping in a draft, a draft on a
  non-active model release, keyboard focus and phone width. UI changes now report functional,
  accessibility and visual evidence separately. Found and scoped WP-10F and WP-10G.

- Base 0.7 WP-13B: `docs/testing/EXECUTION_GUIDE.md` maps each changed production boundary to its
  focused checks and shared-boundary expansion, lists the WP-9 comprehensive command set and records
  measured before/after costs. Backend tests carry contract-group markers (`pytest -m mapping`, …) from
  one manifest in `conftest.py`; an unclassified test module or unknown marker fails collection.
  Vitest runs pure `.test.ts` files in a `unit` project without jsdom and components in `dom`. The
  gate-helper check (now in CI) refuses an unlisted browser runner, and the browser harness prints
  its setup phase timings.

- Base 0.7 WP-13A: `docs/testing/COVERAGE_MAP.md` links product invariants and capability contracts
  to their test evidence, boundary and cost tier, ranks risk and records audit status, residual risk
  and consolidation decisions. New regression evidence: mapping replacement refuses foreign-workspace
  drafts, unknown workspaces, a revision context and retired workspaces without changing data; draft
  relation update/delete advance both draft anchors' set versions only; runtime sources contain no
  starter-model key literal; live `date` values keep their type through write, boundary filters and
  sort; the mapping conflict retry sends the user's attempted target. Two confirmed defects are
  reproduced and fixed as WP-10C and WP-10D, and a third as WP-10E (see Fixed). One relation-set test duplicating stronger evidence was removed.

- Base 0.7 WP-12: `GET /api/v1/model-releases/{releaseId}/activations` reads a release's recorded
  activations (oldest first, with the release each replaced). Models release details move the
  Release ID and content hash into an explained, copyable **Technical details** disclosure; release
  history compares an earlier baseline (Before) with the selected release (After), including the
  active release, defaulting to the recorded predecessor, otherwise the labelled preceding installed
  release of the same key, with an explicit **Compare with** selector and truthful first-release,
  identical-content and unsupported-baseline states. Activation readiness is shown separately and
  always checks the current active release against the candidate.

- Dark mode: a complete dark token set that follows the system preference by default, with an
  explicit System / Light / Dark choice saved per browser and applied before first paint.
- Settings control at the bottom of the navigation rail with the appearance choice and an
  Account placeholder (local single-user session, disabled Sign in) for the planned multi-user
  authentication.
- Dark accessibility scenarios (core pages and the settings menu) and four dark visual baselines.

- Build 0.7 WP-7 browser draft version selection (ADR-028 frontend). Draft creation offers an
  optional model-release selector when multiple releases are installed; default is the active release.
  Draft list cards and detail header show each draft's model release key and version. An informational
  banner explains the state when a draft's version differs from the active release, and activation is
  disabled with a tooltip. A "Change model version" action in secondary draft actions loads available
  releases, attempts the pin change via the WP-6 PATCH endpoint, shows incompatibility diagnostics
  on failure and reloads the model context on success. Dirty-input protection via the existing
  `allowNavigation()` guard before applying version changes. Model-context refresh after pin change
  reloads the draft, pinned model and active release state; external pin change detection via
  `useEffect` + `useRef` in `LoadedDraft`. `WorkspaceDraft` type extended with `modelReleaseKey` and
  `modelReleaseVersion`. 169 frontend tests (5 new), zero lint errors, production build passes.

- Build 0.7 WP-5 atomic mapping replacement API: `PUT /api/v1/workspaces/{workspaceKey}/mappings`
  atomically creates, replaces or removes a mapping for one source in a configured relation binding.
  Supports live and draft contexts with optimistic concurrency via `expectedMappingVersion` and
  `expectedWorkspaceDraftVersion`. Direction-aware cross-cardinality enforcement (one-to-one always,
  one-to-many outgoing only). Retained relation identity when resolving ambiguous→mapped. Typed
  attribute semantics: omitted preserves retained edge values, explicit replaces, `{}` clears. Null
  target with non-empty attributes rejected. Idempotent no-ops with valid tokens produce no version
  increment or audit event. Stale tokens return `409 mapping_version_conflict` with bounded preview.
  Single-direction set version increments avoid double counting. Containment and required-ownership
  bindings rejected. Mapping-transition audit events with old/new targets and relation identities.
  After acceptance follow-up: 73 replacement/activation integration tests; 486 backend tests pass
  on SQLite.

- Build 0.7 mapping list API: `GET /api/v1/workspaces/{workspaceKey}/mappings` returns cursor-paged
  live/draft edges with optional binding, direction and name filters, directional set tokens, stored
  typed relation attributes and optional view-specific projections. Omitting direction returns both
  orientations of each edge; this supplements source-grouped coverage for integration reads.

- Build 0.7 WP-4 mapping query APIs: workspace-scoped coverage, candidate search and version-bound
  target details resolve the selected `mappingGrid` view under the live or draft-pinned model.
  SQL pagination and batched reads return typed projections, mapped/unmapped/ambiguous states,
  exact counts and at most 20 target summaries with explicit continuation. Cursors bind workspace,
  context, model release, view, direction and query configuration.

- Schema 0.6 `mappingGrid` view contract (Build 0.7 WP-2). The model language now accepts
  `schemaVersion: "0.6"` alongside `"0.5"`. `MappingGridViewDefinition` joins `TableViewDefinition`
  in a Pydantic discriminated union on `ViewDefinition.type`. Backend validation checks relation
  binding existence, rejects containment (`parentOf`) and required-ownership bindings, validates
  source/target columns against attached attributes, and verifies candidate search fields are
  searchable target-type attributes. The starter model advances to schema 0.6 / content release 0.7.0
  with two mapping grid views: `system-to-master-mapping` (outgoing) in RDM Systems and
  `master-to-system-mapping` (incoming) in RDM Master. Frontend `ViewDefinition` is a TypeScript
  discriminated union with type-safe narrowing; its initial placeholder was subsequently replaced by
  the WP-8/WP-14 contextual lens. 11 new backend tests cover parse, activation, backward compatibility
  and all validation rejection paths.

- Relation-set version persistence and generic participation (Build 0.7 WP-3). Every generic relation
  write (create, update, delete) now atomically maintains exact-binding set versions in both the
  outgoing and incoming directions. The `relation_set_versions` table tracks the optimistic version
  of each (workspace, optional draft, relation type, from/to object-type pair, anchor object,
  direction) combination. Rows are created lazily on first touch with version 1; untouched sets have
  implicit version 0. Draft-scoped and live-scoped versions are independent. Draft deletion cascades
  set-version rows; draft activation merges draft mutation counts into live set versions. A partial
  unique index protects live-context uniqueness where `workspace_draft_id IS NULL`. 9 focused tests
  cover all mutation paths, independent bindings, draft/live isolation, cascade and activation merge.
  All 379 backend tests pass.

- UI-07 automated accessibility and visual-regression gates (WP-1). `npm run test:a11y` runs
  axe-core WCAG 2.1 AA checks on 9 core page types across two object types; `npm run test:visual`
  compares viewport screenshots against committed baselines using pixelmatch. ~16 color-contrast
  violations fixed, definition-list structure corrected, sidebar landmark added. Two known violations
  allowlisted with tracked references. Light-theme baselines committed; dark baselines followed with
  dark mode.

### Changed

- Backend tests that need a private database copy a once-migrated template instead of running every
  Alembic migration per test; startup and migration tests still migrate for real. The sampled backend
  selection runs in 22.7 s instead of 46.8 s with the same cases. A pagination test that failed when run
  alone now owns its database.

- Models page aligned with the rest of the UI: the release/draft catalogue is now sidebar
  navigation, and the main column uses the shared context bar, page header and surfaces.

- Base 0.7 UX pass over the generic frontend, with routes, data contexts and API contracts unchanged:
  applications as header tabs with model icons; a segmented Live / Drafts / History control;
  collection list plus a collapsed-by-default record tree that opens toward the active record;
  one Filter popover with an applied count; lens tabs, scope banner and page count beside
  pagination; whole-row open; a record header with one breadcrumb line and a visible Edit record
  action; readable record activity without identifiers or concurrency tokens; a compact draft bar;
  and a rewritten design-token stylesheet with a 12–14px minimum text scale.
- Mapping lenses: segmented coverage filter, row-click to map, a searchable radio list of
  candidates, **Save and next**, and an explicit **Remove mapping** action. Selecting nothing no
  longer turns the primary button into a clear operation.

- Build 0.7 WP-14 composes model-defined table and mapping views as lenses of one contextual
  collection. One application browser now presents virtual collection groups alongside runtime
  hierarchy records, replacing the separate Browse hierarchy / Views modes. Direct-parent scope,
  typed field facets and mapping coverage state are visible and URL-backed. Mapping coverage applies
  parent/state filters before cursor pagination in live, draft and immutable-revision contexts, and
  cursor fingerprints bind both values. This remains generic over configured applications, object
  types, relations and renderers; Master, Systems and Translations remain starter examples.

- The WP-8A/WP-8B review retained atomic mapping actions while removing duplicate configured name
  columns and requiring explicit review before retrying after a mapping-version conflict. Historical
  mapping reads now use revision projections and expose no mutation controls. Focused package evidence
  covers both configured mapping directions, direct-parent scope, visible mapping-state filtering,
  live replacement, narrow layout and the composed page's accessibility.

- Extended the planned 0.7 design and delivery documentation after plan review: WP-1–WP-3 remain
  frozen; later packages specify bounded view-based mapping reads, stable retained relation identities,
  typed attributes, direction-aware constraints and atomic whole-candidate draft compatibility.
  Mapping UI is split into WP-8A coverage and WP-8B actions; WP-9 expands integration/a11y/visual
  evidence, with conditional WP-10 for confirmed foundation gaps.

### Fixed

- Base 0.7 WP-10K: records and relations read in a draft or from history no longer show the current
  time as their created and updated times. These are not recorded there, so the API returns `null`
  (the fields are now nullable), filtering or sorting by them is refused with an explanation instead
  of matching nothing, and collection views neither offer nor send them outside live data.
- Base 0.7 WP-10H: the mapping dialog no longer offers **Remove mapping** for a required
  relationship, which the server refuses; it asks for a replacement instead.
- Base 0.7 WP-10I: starting a draft on an incompatible model release lists the records that do not
  fit, as a version change already did, and draft error messages no longer run two sentences together.
- Base 0.7 WP-10J: missing-required and read-only field errors name the fields (“Required fields are
  missing: External ID”) instead of printing a list of keys; the keys are in `details.attributeTypeKeys`.
- Test reliability: the WP-12 and WP-13C browser runners waited too little for clipboard feedback
  and focus restore; a current-live base test read another test's draft from the shared database. The
  Models page visual baselines now show the WP-12 layout.
- Base 0.7 WP-10E: a live `dateTime` write keeps its instant. Values are stored in UTC and every
  context returns them with an explicit offset; decimals read back in one form without trailing
  zeros (live reads were padded to `12.5000000000`), so draft uniqueness compares equal decimals as
  equal. All server timestamps (`createdAt`, `updatedAt`, `occurredAt`, …) now carry an offset on
  SQLite too, and the browser no longer appends one to zone-less times.
- Base 0.7 WP-10F: **Create new …** in a mapping lens asks which application the new target
  belongs to, listing every application that contains its type and defaulting to the lens's own.
  Parent choices are limited to types in that application, and a notice explains when it has none.
  The starter can now create a target in both mapping directions.
- Base 0.7 WP-10G: the mapping dialog's search box keeps its height at phone width, and the draft
  model-mismatch and historical-revision notices name releases by key and version instead of UUID.
- Base 0.7 WP-10C: `date`, `dateTime` and `decimal` values can be written in a workspace draft
  (create, update and the field endpoint returned 500) and are published to live on activation,
  including values captured from live. Draft and revision lists filter and sort these fields and
  integers by their declared type: numbers no longer sort as text (`10` before `5`), date-times sort
  by instant, and a zone-less `dateTime` filter value is read as UTC.
- Base 0.7 WP-10D: renaming or moving a contained record inherited by a draft no longer adds a
  second containment relation with a new ID. An unchanged parent keeps its relation; a move replaces
  it with exactly one. Such drafts now activate instead of refusing with `duplicate_edge` or
  `relation_cardinality_violation`.

- WP1-001: the navigation resize separator is inside the navigation landmark, so its accessibility
  exception is removed. Collection and settings popovers render inside a landmark (or the open
  dialog), and zone-less server timestamps are read as UTC.

- Build 0.7 WP-5 review: enforce ancestor-scoped constraints against the final replacement graph,
  and reject missing required ancestors in generic draft relation writes as in live writes. Reject
  required-ownership replacement irrespective of relation orientation. Explicit empty application/view
  keys fail validation instead of selecting unconfigured reads. Twelve HTTP regressions cover these
  boundaries, preserved tokens and valid replacements within one ancestor scope.

- Build 0.7 WP-10B: draft activation now refuses new, removed or updated live relations in exact
  mutable binding sets the draft touched, including previously unmapped sets. It compares the
  immutable source/live edge identities and versions before applying any rows. Refusals preserve
  the draft, live data and revision designation and include bounded mapping-set diagnostics with
  recovery instructions. Unrelated live mapping work and existing containment/ownership merge
  behavior remain covered. WP-5 acceptance adds independent-binding isolation, required-ownership
  and clearing refusals, and overlapping generic create/update/delete versus mapping saves.

- Build 0.7 WP-10A, found in WP-4 review: confirmed live/draft object cascades now advance both
  directional relation-set versions for removed edges. Stale mapping target continuations return
  `409 mapping_version_conflict` with refresh guidance; previews and rejected deletes leave versions
  unchanged. Regression coverage exercises both directions and contexts.

- Build 0.7 WP-1/WP-2 review fixes: scope accessibility exceptions to known targets and node counts,
  fail visual comparisons on missing baselines outside explicit update mode, reject `mappingGrid`
  under schema 0.5, and allow the documented offline schema 0.4 recovery to select a compatible
  schema 0.5 or 0.6 candidate. The CLI reports expected refusals without a traceback, and the draft
  context regression now checks the current named-draft and version presentation. Visual capture
  waits for loaded panels, and the model-workbench baseline now covers the loaded release detail.

## [0.6.0] - 2026-09-11

### Changed

- Implemented WP8.1-A model authority boundaries. Compatibility now examines all authoritative live
  objects, attributes and relations, including catalogue-retired workspaces. Draft and historical
  reads resolve their pinned supported model before filters, typed responses and relation expansion;
  missing, corrupt or unsupported pins and workspace-context mismatches return structured errors.

- WP8.1-B captures an immutable current-live draft base including post-publication edits, model and
  record versions, with live data that has no prior publication. Historical source remains separate.

- WP8.1-C delivers newest-first revision history with deterministic cursor retry. Designation
  retirement preserves live access and history; catalogue retirement rejects writes.

- Reviewed the uncommitted WP8 implementation against the live/draft API contracts. Corrected
  activation and cascade deletion ordering, association confirmation and ownership checks, atomic
  draft version claims, public relation UUID reads, retired-workspace publication guards, and
  read-only attribute handling, draft containment validation and cross-workspace ID collisions.
  Added request-boundary and audit-migration regression coverage. Cascade confirmation now requires
  the signed token from the exact displayed preview and rejects any intervening hierarchy change with
  no deletion or audit side effects. Missing tokens are rejected before stale-version checks, draft
  deletion verifies the route object type, live deletion serializes against workspace retirement and
  inconsistent cross-workspace graph edges are refused. The frontend adapter carries both live and
  draft confirmation context.

- Reconciled technical documentation and delivery planning with the accepted product stories and
  GAP-01–GAP-08 answers. ADR-027 consolidates live data, optional copied drafts, immutable history,
  truthful publication retirement and newest-first history. Corrected API documentation against
  current payloads and cursor behavior.

- Implemented ADR-026 live active data writes: the active workspace is live-writable for **data**.
  `workspaceDraftId` is optional on record writes — present stages into the design draft; absent
  writes directly to the live active object store (record `expectedVersion` claim + audit, no
  workspace revision). Active reads resolve the live projection; activation is a delta-merge of the
  draft onto current live content with per-record version conflict detection (`version_mismatch` /
  `id_collision` / `duplicate_edge`), merged-graph validation and a merged revision snapshot that
  preserves live-only records. Restored `services/objects.py` CRUD functions, `services/relations.py`
  helpers and `services/deletion.py` as the live write path basis; added the workspace-audit seam and
  a corrective migration widening the audit `aggregate_id` column to host live object/relation ids.
  Amends ADR-024/ADR-025 write-context clauses for data content.

- Corrective Base 0.6 WP6 persistence: workspace drafts and immutable workspace revisions own the
  staged/historical graph; ADR-026 subsequently restores live-row current-data authority. The migration
  converts only unambiguous Base 0.5/rejected-WP4 workspace graphs,
  preserves public object and relation UUIDs, and removes per-object lifecycle persistence.

- The backend now requires Python 3.14. The local version pin, package metadata, Ruff target, CI
  runtime, container base image and development documentation all use 3.14; Python 3.12
  compatibility is no longer maintained.

- Frontend structure refactor, phases 0–4 of `docs/FRONTEND_STRUCTURE_REFACTOR.md`. No API
  contract, model contract or architectural change. `frontend/src` is reorganized into `app/`,
  `features/`, `ui/`, `model/`, `routing/`, `lib/`, `types/` and `styles/`, with every internal
  import going through an `@/` alias. `types.ts` and `utils/model.ts` are split by concern behind a
  barrel, the four overloaded components are split into 28 modules, and `styles.css` becomes four
  layers whose built output is byte-identical.

- The generic view and panel registries are rendered as elements rather than called as functions.
  Nothing was broken, but a panel component gaining state would have made `ObjectDetail`'s hook
  order depend on which panels a model declares as visible. The panel registry is keyed by the
  `PanelDefinition` discriminant, removing its per-entry casts, and both registries now live in
  their own modules.

- Client error handling is consolidated in `api/errors`. `isApiError` replaces five untyped casts
  used to detect optimistic-concurrency conflicts, and `errorMessage` replaces 36 inline
  expressions. Seven messages that reached the UI as `Error: …` now read like every other message.

- Cursor paging and search debouncing are consolidated into `useCursorPages`, `useCursorFeed` and
  `useDebouncedValue`, replacing two incompatible paging implementations across seven components.

- Every dialog shares one modal shell, `ui/Modal`. Five dialogs previously rebuilt the same backdrop
  and disagreed about its behavior. `ObjectFormDialog`, `AttributeValueDialog` and
  `RelationFormDialog` now close on Escape and return focus to whatever opened them; Tab is trapped
  inside an open dialog; the page no longer scrolls behind one; and two dialogs that carried
  hardcoded `aria-labelledby` ids now generate them, so opening two cannot produce duplicate ids.

- Frontend redesign (UI-01–UI-06). Compact neutral sidebar with workspace/application/view
  navigation; Browse hierarchy default with browser-local expand/collapse persistence; accessible
  mobile navigation drawer. Focused collections with search, typed filter popover, sort, display
  controls, sticky headings, comfortable/compact density and mobile-aware column prioritisation.
  Full-width record inspector with collection-origin preservation through reload/Back/Forward,
  contextual action menus, dirty-edit navigation guards and cross-application related-record return.
  Inline typed field editing with explicit save/cancel, null/removal distinction, saved/error
  feedback and retained coherent multi-field forms. Pointer and keyboard resizable navigation rail,
  inspector and table columns with browser-local display preferences. Refined draft catalogue,
  named-draft strip, consistent error/loading/empty/confirmation treatment and composed
  desktop/mobile visual review. UI-07 (automated accessibility and visual-regression gates) is
  deferred to 0.7.

### Added

- WP9 complete generic browser tasks in live, draft and history contexts. Slice A implements live
  workspace navigation with cursor-position restoration and retry/content preservation. Slice B
  implements direct live Add/Edit/Delete with typed fields, ordinary relationships and translations,
  conflict reconciliation and signed deletion confirmation. Slice C implements optional current-live
  drafts, shared draft authoring, validation, activation and discard with aggregate concurrency and
  conflict feedback. Slice D implements newest-first immutable history, pinned-model reads, historical
  draft sources and truthful publication retirement. SC-01–SC-06 and SC-08 have isolated real-backend
  browser evidence with two configured object types at desktop and 390px mobile widths.

- WP10 composed release validation: product scenarios exercised against a real browser and backend,
  including live CRUD without a draft, optional staging, current-live draft bases, concurrency and
  delta merge, whole-graph atomic failure, live-only compatibility and pinned historical typing.
  Keyboard/focus/narrow-layout journeys, migration/lifespan, packaging and public-contract checks.
  Automated accessibility and visual-regression tooling (UI-07) is deferred; manual keyboard and
  focus checks are recorded.

- Base 0.6 WP7 corrective CRUD restoration: the established generic object, attribute, relation and
  translation CRUD contract is restored over WP6 workspace storage. Originally draft-scoped, it was
  extended by ADR-026 to direct live writes plus optional drafts. No per-record lifecycle or nested
  public CRUD resources are introduced, and the
  original CRUD, attribute, cascade and translation suites are restored and enabled.

- Base 0.6 WP8 workspace lifecycle orchestration. Root and
  history-derived workspace drafts, whole-graph validation, atomic activation that writes one immutable
  workspace revision of the merged live graph and applies authored changes in one transaction after the
  ADR-026 correction,
  cursor-paged immutable revision history, and publication retirement under an expected active-revision
  claim. Draft/revision/validation/activation/retirement events use dedicated workspace aggregates with
  bounded identity payloads, kept separate from record-level `object-draft` and `relation` audit
  events. Objects, typed attributes, containment and relations remain ordinary records through the
  canonical generic CRUD routers; no per-object lifecycle or nested workspace-draft CRUD resources
  exist.

- Database migration failures now produce a credential-safe operator message with the current and
  target revisions, recovery command, backup requirement and escalation details. Startup enters
  maintenance mode without a traceback, and the WP4 migration safely retries recognized empty SQLite
  DDL left by an interrupted attempt. Real-database startup, restart and interruption regression tests
  cover the failure that previously left the development application unable to boot.

- Base 0.6 authoritative runtime-object revisions. Stable logical objects now own model-pinned,
  optimistic drafts and immutable active/retired snapshots with separate derivation and supersession
  lineage. Root and historical drafts, explicit activation, cursor-paged history, retired discovery,
  direct retirement and ownership-cascade retirement are public API contracts. Activation publishes
  core fields, typed attributes, containment and required relationships atomically; independent
  associations and published identity survive retirement. The Alembic transition preserves object
  UUIDs, migrates known active/draft/retired rows and rejects unknown legacy states with counts.
  Post-implementation hardening conditionally claims the final draft version during activation,
  prevents compatibility adapters from drifting the lifecycle projection and rejects corrupt
  cross-workspace retirement graphs.
  This pre-release design was subsequently rejected as the wrong publication boundary. ADR-024 and
  corrective WP5 froze workspace-level journeys, fixtures and API design; WP6 supplied the corrected
  persistence, WP7 restored generic CRUD and WP8 completed workspace orchestration, with WP9-WP10
  delivering the UI and release validation. These object-lifecycle APIs are not a compatibility
  commitment.

- Frontend lint and format tooling: ESLint 10 with `typescript-eslint` and
  `eslint-plugin-react-hooks`, and Prettier. `AGENTS.md` listed "linting passes" in the definition
  of done, but the frontend had no linter. Dependencies are pinned instead of `"latest"`, build
  tooling moves to `devDependencies`, and the Dockerfile uses `npm ci`; TypeScript is pinned to 6.x
  because `typescript-eslint` cannot yet parse with the TypeScript 7 native compiler.

- An application-level smoke test covering the extracted router: model-driven shell rendering, deep
  collection URLs, fallback when a URL names a retired application, and returning from an object to
  the collection and workspace it was opened from.

### Fixed

- A detail panel naming an object type that a later release retired now reports it instead of
  crashing the detail screen through a non-null assertion.
- Modals restore focus to their opener even when a form field uses `autoFocus`; cursor feeds ignore
  late load-more responses after their query changes or reloads; and cancelling a failed relationship
  deletion clears its action-specific error without blocking relation paging.

## [0.5.0] - 2026-09-05

### Added

- A global model workbench with always-readable installed releases and capability-gated JSON draft
  creation/import/editing, validation diagnostics, canonical compilation, semantic comparison,
  browser export, immutable installation and guarded activation. Optimistic conflicts preserve local
  input, and mutation controls remain absent by default.

- Base 0.5 generic object-management UI. Workspace context is explicit in the app shell and URLs;
  collection search, repeatable state filters, built-in sorting and page size survive browser
  navigation; generic rows expose existing edit/delete semantics; failed collections, panels and
  lookups are retryable; and object details show bounded, incrementally loaded audit history.

- Base 0.5 object and relation query foundations. Object collections now support repeatable state
  filters and stable built-in sorting through signed, filter-bound keyset cursors. Relation expansion
  is a bounded workspace-checked page, and object history uses an indexed audit-subject projection to
  include object, attribute and connected-relation events without exposing internal sequences or full
  before/after payloads.

- Base 0.5 guarded model activation. Compatible installed releases can be selected with both expected
  runtime version and active-release tokens; incompatible runtime data and stale selections return
  structured conflicts. Activation commits before refreshing the process registry, records old/new
  release IDs and hashes, marks health unhealthy on refresh failure, and rejects mutation enablement
  when `WEB_CONCURRENCY` configures multiple workers.

- Base 0.5 persisted model drafts and immutable installation. Mutation-gated draft APIs support
  optimistic version claims, side-effect-free compilation and atomic content-addressed installation;
  lifecycle audit events retain hashes and identities without copying complete model JSON. The
  capabilities endpoint reports the effective read, draft, installation and activation surface.

- Base 0.5 model compilation and comparison: inline validation returns stable diagnostic codes and
  JSON Pointer paths; installed releases can be compared by semantic, key-based paths; and bounded
  runtime-data checks classify candidates as compatible or migration-required without persisting or
  activating content.

- Base 0.5 model runtime authority: a singleton, versioned database row selects the active immutable
  release; source JSON is bootstrap input only. Requests resolve one cached model/release snapshot,
  `GET /api/v1/model` exposes its hash and release UUID in response headers, and cursor-paged release
  catalogue/detail APIs expose installed snapshots without enabling mutations.

- Complete model-driven Translation CRUD. Translations contain optional translated name, description
  and value fields (with at least one required), belong to a Translation Group, and atomically bind to
  exactly one configured target object. Domain, Codelist and Master Value targets are enabled in the
  starter model; future target types require only another JSON allowed pair. Duplicate active
  target/Language translations are rejected, inactive historical records may coexist, required
  bindings cannot be unlinked, and owner cascade deletes the Translation.

- Optional, model-driven Domain/Codelist-to-System Value representation relationships. Domain and
  Codelist details expose outgoing representations, while System Value details expose their incoming
  reference structures. These associations do not alter system containment and cascade deletion only
  unlinks them. System Value relation tables show the containing System through a generic ancestor
  column and can omit their constant relationship-label column.

- Optional transactional cascade deletion for runtime objects. A non-cascade delete with dependencies
  now returns a structured, non-mutating impact report; the UI renders the affected child objects,
  PK/FK dependents and relationships before allowing explicit cascade confirmation. Cascades delete
  containment descendants, unlink independent relationships and follow directed, required
  single-valued bindings from owner to dependent.

- Model-driven runtime CRUD in the React UI: object create/edit/delete, individual attribute-value
  add/edit/remove, and direction-aware relationship create/edit/delete. Relationship choices come from
  configured panels and allowed object-type triples; candidate lookup is server-side and can cross
  application boundaries within a workspace. Engine-maintained containment edges remain visible but
  immutable.
- A structured frontend `ApiError`, shared typed field renderer, paged object lookup and accessible
  destructive confirmation dialog. Optimistic-concurrency, dependency, uniqueness and cardinality
  failures remain recoverable in their active UI context.

- Standalone object-scoped CRUD for attribute values:
  `GET`/`POST`/`PATCH`/`DELETE /api/v1/objects/{objectTypeKey}/{objectId}/attributes/{attributeTypeKey}`.
  A single stored value can now be read, set, updated or removed without rewriting the whole object.
  Mutations require the object's `expectedVersion`, return the full object response, and enforce the
  same validation, read-only/required and workspace-uniqueness rules as object writes. Deleting a value
  on a required or read-only attribute is rejected (`422 cannot_delete_required_attribute` /
  `read_only_attributes`).
- Read-one, update and delete for relation instances:
  `GET`/`PATCH`/`DELETE /api/v1/relations/{relationId}`. `PATCH` replaces relation `attributes`
  (relation identity is immutable) and, like `DELETE`, claims an atomic `expectedVersion`
  (`409 version_conflict` on a stale claim). Engine-maintained parent-containment and hierarchy
  relations — those named in the target object type's `behavior.parentRelationTypeKeys` — are rejected
  for direct create/update/delete with `422 immutable_relation`; they stay atomic through object parent
  operations.
- Workspace-scoped attribute uniqueness for attribute types that declare `features.unique`. Create and
  update now reject a colliding value with `409 duplicate_attribute_value`. Uniqueness is enforced per
  attribute type within a workspace, and declaring `unique` on a `json` value type is rejected at model
  load.
- Frontend unit-test setup (Vitest + Testing Library) covering the model helpers and the generic
  renderers with two object types, run locally and in CI via `npm test`.

### Changed

- The bundled starter content release is now `0.5.0`; its model-language `schemaVersion` remains
  `0.4` because Base 0.5 did not change the declarative schema contract. Existing databases retain
  their database-selected active release until an administrator deliberately activates another
  installed release.
- Release operations now have documented backup and rollback boundaries: back up before migrations,
  use activation for compatible model-content rollback, and restore the matching database backup for
  application/schema rollback rather than editing immutable releases or relying on Alembic downgrade.

- Hardened the Base 0.5 WP2/WP3 lifecycle foundation after review: compatibility checks now include
  numeric relation attributes and enforce cardinality across every allowed pair sharing a relation
  type; compiler diagnostics retain stable paths for top-level validation failures; semantic diffs
  preserve real JSON `null` values and ignore ordering in set-like key collections; and concurrent
  installations are serialized in the supported single-process administration topology.

- Metadata collection endpoints now use opaque cursor pagination with a documented page-size limit.
- Attribute-value response items now include their stable public UUID `id`.
- Relation `fromObjectId`/`toObjectId` and object `parentObjectId` are now validated as UUID v4,
  returning `422 request_validation_error` for non-UUID values.
- Alembic migrations are now the single source of schema truth: the initial migration provisions a new
  database and upgrades an existing one, and startup no longer runs `create_all`.
- Object ancestor paths are resolved in level order (one query per depth level) instead of one query per
  object, removing the N+1 traversal on collections.
- Developer tooling: `.python-version` pins Python 3.12, and generated `*.egg-info`/`*.tsbuildinfo`
  artifacts are removed from version control.

### Fixed

- Model release snapshots are recursively immutable, metadata and release cursors are signed and
  filter-bound, model ETags use valid quoted entity-tag syntax, and release timestamps are normalized
  to UTC even when SQLite returns naive datetimes.
- Relation create and update now reject attributes not declared by the matched allowed pair and
  validate declared values through their global attribute types before persistence.
- Duplicate many-to-many edges supplied through atomic object `initialRelations` now return
  `409 duplicate_relation` and roll back the new object instead of escaping as an internal error.
- The initial Alembic revision now owns a frozen schema snapshot rather than importing live ORM
  metadata, keeping fresh-database upgrades reproducible as later revisions are added.
- Object creation preserves `false` for optional boolean attributes without a configured default
  instead of treating that value as absent.
- Object and standalone attribute-value writes now share an atomic expected-version claim, preventing
  concurrent requests from accepting the same object version and silently overwriting one another.
- Standalone attribute-value `GET` responses now include `objectVersion`, allowing clients to obtain
  the concurrency token required by `POST`, `PATCH` and `DELETE` without fetching the full object.
- Objects that have a parent can now be deleted. Deleting such an object removes its parent containment
  relation atomically, while objects with child objects or non-parent relations (mappings, translations)
  still return `409 object_has_dependents`.
- Partial updates no longer let a required attribute be cleared. Providing a required attribute as
  `null` or empty in a `PATCH` returns `422 missing_required_attributes`; omitting it remains allowed.
- `validation.minimum`/`maximum` on a non-numeric attribute type no longer causes a server error. These
  bounds now apply only to `integer`/`decimal`; non-numeric, non-finite, inverted or misplaced bounds
  are rejected at model load.
- The object form's parent picker now pages through all candidate parents instead of truncating at the
  first page, so a parent beyond the first page is no longer silently lost when editing.

## [0.3.0] - 2026-09-02

Baseline executable vertical slice of the generic reference-data engine: the versioned JSON model
(schema 0.3) as the source of truth for applications, object types, global attribute types, relation
types, allowed object-type triples and UI views, with a FastAPI backend, immutable model releases,
typed attribute storage, cursor-paginated APIs and a generic React UI.
