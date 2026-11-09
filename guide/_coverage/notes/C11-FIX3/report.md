# C11-FIX3 report

Completed 2026-11-09. Applied `guide/AGENTS.md` and this wave only; the repository's top-level instructions were excluded as requested. No steer file existed at any unit boundary. No commits, Git mutations, product edits, new pages or picture changes. Twelve existing guide pages were edited. The required generated site is under `guide/_build/C11-FIX3/`.

## Reader findings 1–15

Page paths in this report are relative to `guide/src/content/docs/`.

| Finding | Disposition and page change or evidence |
| --- | --- |
| 1. Publication handoff | Fixed in `guide/use/load-a-workbook-with-the-assistant.md` and `guide/model/review-an-assistants-workbook-design.md`: follow the review's workspace move and publication action into the migration preview, inspect blockers/approval, then confirm **Migrate and publish**. Separate activation is not required. Removed the same contradictory instruction in `use/loading-with-the-assistant.md` and `journeys/work-with-an-assistant.md`. Verified `features/workspaces/ChangeSets.tsx` and `features/model-admin/MigrationPage.tsx` in the frontend. |
| 2. Relationship counts | Fixed in both workbook task guides: new relationships include new records' parent links, and checked/loaded totals count those same links. Verified `backend/app/engine/sources/items_summary.py` adds `parent_links` to `relationshipsNew` and serves `parentLinksNew`; frontend `DesignLoad.tsx` labels and explains them. No new-record load was repeated. |
| 3. Acceptance label | Fixed every remaining guide occurrence of **Accept and load** to **Accept and load to change set**, across ten existing pages. Verified the acceptance label in `DesignLoad.tsx`/its direct component test and `aiTaskJourney.ts`. |
| 4. Internal model wording and proposal filename | No guide workaround. Product fix checked: `aiTaskDesign.ts` describes the attribute that names records; `agent._VOICE`, `_without_files` and `_said` avoid/filter file vocabulary in closing notes. The reader's bounded retest did not reproduce it. Old pictures still show it; see below. |
| 5. Example workbook download | Fixed in step 2 of `guide/use/load-a-workbook-with-the-assistant.md`: direct download of the existing fictional operator workbook, explicitly an example from the reference data. The existing download target passes the built-site link check. |
| 6. Stop reported as failure | Existing **You stopped the assistant** / **Go on as it was** guidance remains correct. Expanded `guide/use/continue-an-assistant-task.md` to tell the reader to copy a displayed correlation ID when asked. Product checks: `agent._command_of` uses `/proc` before `ps`; `_stop_earlier` requests termination then kills if necessary; `store.stopped` distinguishes intentional Stop, and `store.sync` appends an available correlation ID. Latest reader evidence confirms intentional Stop. |
| 7. Records task named as model work | Fixed explanation in `guide/use/change-records-with-the-assistant.md` and `guide/model/change-a-model-with-the-assistant.md`: **Change with the assistant** before a proposal, then **Change records** or **Change this model**. Verified `aiTaskText.wordsTaskName`; latest reader run reached **Change records**. |
| 8. Correction failed / empty replacement left behind | No guide workaround. Existing correction → revised check → acceptance → replacement review matches the fixed behavior; acceptance label corrected in `guide/use/continue-an-assistant-task.md` and linked pages. `agent._run` handles failed turns and `_discard_empty_sets` discards empty replacements; `items_load.run` discards refused atomic loads. Reader's workbook correction retest completed and reviewed the replacement. This wave did not repeat a words-only correction. |
| 9. View-only draft called unchanged | Fixed in `guide/use/change-records-with-the-assistant.md`, `guide/model/review-an-assistants-workbook-design.md` and `guide/model/change-a-model-with-the-assistant.md`: **No type, attribute or relationship changes** still requires editor review of views/layout. A words-only proposal without a draft says **No change to the model.** without a workbook claim. Verified `ModelProposal.tsx` passes workbook/draft flags into `DesignModel.tsx`. |
| 10. Failed job leaves working task | No guide workaround. Failure/recovery guidance already matches product. `backend/app/engine/jobs/worker.py` synchronizes the associated task when finishing its job; `tasks/store.sync` ends failed tasks with the cause/correlation ID. `jobs/store._finish` no longer treats a zero-item failed job as all applied. Latest reader attempts did not reproduce the stale state. |
| 11. Saved-profile contradiction | Fixed `guide/use/load-the-next-version-of-a-workbook.md`: current checked-items assistant loads save no profile; separately saved profiles can still be reused through Import. `items_load.run` loads a batch and returns counts/change-set/release, without saving a profile; `agent._ITEMS` expressly sends items, not a profile. The older session-driven `agent._landing` can save an import profile, but is not the current documented checked-items workbook path. The existing profile with broken bindings remains setup data, not a newly established engine defect. |
| 12. Blank return after personal sign-in | Setup issue, not an established product defect: latest reader run completed with a real listening loopback return address. Added one sentence in `guide/integrate/connect-an-assistant.md`: assistant must listen at its registered return address during sign-in, locally for loopback. OAuth handler redirects the code/state to the registered return. |
| 13. Early-Stop continuation failed without explanation | Fixed the early-Stop explanation in `guide/use/continue-an-assistant-task.md`: restart on the same task with the person's words/file when nothing can be resumed. `agent.resumable` checks for a transcript; `_run` records **The session ended without an answer.** for an empty result. Latest reader continuation completed. No runtime retest here. |
| 14. Partial move described as manual work | Fixed `guide/model/change-a-model-with-the-assistant.md` and `model/ai-model-changes.md`: review what acceptance prepares, then complete the prepared releases/move set, without manual preparation. Removal text describes moves and destinations, preserving records. Verified `agent._PARTIAL`, `_removal_account`, `_final_release_found` and `_then_release`. Latest reader run completed all three steps; this wave did not repeat a move. |
| 15. Internal proposal vocabulary | No guide workaround or new definition of internal terms. Current code explicitly prohibits those terms in `_VOICE`; `_INTERNAL` and `_without_files` filter closing-note sentences naming draft/move/removal fields. Historical reader screenshot 55 is evidence of the earlier wording, not proof this current fix still fails. No fresh assistant turn was purchased to retest the filter. |

No finding remains established as a still-open product defect after these source checks. This does not claim that every runtime branch passed; no live assistant tasks or product tests were run in this documentation wave.

## Each named product fix / guide sentence

| Named change | Guide treatment and source check |
| --- | --- |
| Stop, continuation and correlation ID | Continuation guide now covers early restart and reporting the shown ID; intentional-stop labels were already correct. Checked process stopping, resumability and task-state handling. |
| Corrections and empty failed change sets | Retained revised-proposal/reacceptance instructions, corrected the acceptance label. Checked failed-turn cleanup and the atomic item-load refusal path. |
| Failed jobs reach their tasks | No additional page edit needed: the continuation and failure sections already describe the fixed behavior. Checked worker finish synchronization. |
| Workbook counts list and loaded totals | Both workbook task guides explicitly include parent links and compare checked/loaded totals. |
| Words-task heading | Both words-task guides explain the neutral heading and record/model headings; the workspace menu/dialog label **Change this model…** is still correct and retained. |
| No-workbook model summary | Records, workbook-design review and model-change task guides explain the unchanged-model and views/layout cases. |
| Finish a partial move | Model-change guide now explains the proposal before acceptance, prepared old/new release, move change set and final release, and records moving instead of being deleted. The engine's final-release discovery is checked in code; no internal session marker is taught to browser readers. |
| Journey-bar **Accept the model** | Model-change guide says it takes the person to the page's acceptance button, which confirms. Verified `AiTaskJourneyBar` targets `journey-accept` and `ModelProposal` marks the acceptance controls. |

## Edited pages

- `guide/use/load-a-workbook-with-the-assistant.md`
- `guide/model/review-an-assistants-workbook-design.md`
- `guide/use/load-the-next-version-of-a-workbook.md`
- `guide/use/change-records-with-the-assistant.md`
- `guide/model/change-a-model-with-the-assistant.md`
- `guide/use/continue-an-assistant-task.md`
- `guide/integrate/connect-an-assistant.md`
- `use/loading-with-the-assistant.md`
- `model/ai-model-changes.md`
- `journeys/work-with-an-assistant.md`
- `integrate/assistant-tasks.md`
- `guide/model/load-a-workbook-into-a-change-set.md`

## Existing pictures that no longer illustrate this flow correctly

Visually inspected the eight existing pictures listed here and below. No image was created, edited or removed.

| Picture under `guide/public/screens/` | Mismatch / retake requirements |
| --- | --- |
| `use-assistant-proposal.png` | Workbook proposal uses the earlier **Accept the model** step and shows proposal-file/internal vocabulary. Retake the checked-items proposal with **Accept and load to change set** and plain notes. |
| `model-assistant-workbook-proposal.png` | Same older acceptance/check layout: **Accept the model** and **The check of every row**, rather than the current checked-items **What the load does**. Retake with the model summary expanded and current acceptance/counts, including parent links where present. |
| `use-assistant-loaded.png` | Says a profile was saved and offers **Open the profile**, unlike the current checked-items load. Retake with actual record/relationship counts, no saved-profile claim and change-set review/correction controls. |
| `model-assistant-workbook-loaded.png` | Same old saved-profile claim and controls. Retake the current checked-items loaded result. |
| `use-assistant-words.png` | Breadcrumb **Change this model** despite **No change to the model**, plus proposal filename and internal fields in the note. Retake with **Change records**, plain notes and **Accept**. |
| `use-assistant-reload.png` | Confirmation says the assistant then loads again, omitting revised check/reacceptance; background also shows the old saved-profile result. Retake the current checked-items reload confirmation, including revised-proposal review and acceptance before loading. |

`use-assistant-stopped.png` still shows the correct intentional-stop labels. `model-assistant-partial-move.png` still shows the prepared three-step handoff with the first Done and review Next; no mismatch from these fixes was found in that image. No new picture is requested.

## Validation and limits

- `GUIDE_OUT=_build/C11-FIX3 npm run build` in `guide/`: passed, 253 pages, 3.81 s. Existing non-fatal duplicate `/404` route warning.
- `GUIDE_OUT=_build/C11-FIX3 npm run check:links`: passed, 73,550 local links/sources across 253 built pages, including the example workbook download.
- Targeted text search found no remaining old **Accept and load** label, saved-profile heading/claim, or separate compatible-release activation instruction in the documentation.
- Product behavior was checked against code and the reader's latest, superseding report. No fresh browser run, AI call, migration, publication or application test suite was started. No background service was started.
