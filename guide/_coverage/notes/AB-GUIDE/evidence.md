# AB guide working evidence

Read guide/AGENTS.md and the full wave brief first; top-level instructions excluded by assignment. No memory used.

- DesignLoad.tsx: exact figures and type table; three examples/type in items_summary.py; repeated-name findings and folded file-part ranges. No sheet profile for items.
- ModelProposal.tsx: load proposals use Accept and load unless whole-type moves; Accept for unchanged words-only; Accept the model otherwise.
- items_load.py: rechecks superseded draft before install; _install commits separately; atomic record batch refusal discards change set, _fail clears result; an installed release can remain. No profile fields on successful result.
- design_job.py _queue_words: itemsLoad corrections return stage model, so loaded correction requires a new proposal and acceptance.
- agent.py _ITEMS and _QUESTIONS (agent/15): workbook and records read by assistant; no profile; only questions left open by file/words. Words-only path and moves keep their endings.
- API.md dry-run and task-operation sections read; API result prose still claims all session loads save profiles, contradicting its AB accept entry and items_load.py. Report this, do not edit outside assignment.
- BASE_0_13_IMPLEMENTATION_PLAN.md Built AB paragraph and CHANGELOG.md Unreleased AB confirm changed path; real acceptance-file runs explicitly not yet done in build record.

## Pages finished

- guide/use/load-a-workbook-with-the-assistant: retained access/sending, startup, saved-layout activation and publication; changed check, accept, profile and correction wording. Screenshot use-assistant-loaded.png needs new capture; workbook dialog unchanged.

- guide/model/review-an-assistants-workbook-design: retained access, sending, draft ownership, moves link, publication and destructive-discard warning. Screens inspected: model-assistant-workbook-proposal.png shows old row check/Accept the model; model-assistant-workbook-loaded.png and use-assistant-loaded.png show saved-profile claim; use-assistant-proposal.png shows Accept the model plus old technical assistant notes and questions.

- guide/use/continue-an-assistant-task: retained Stop effects, failed/stopped buttons, destructive-discard confirmation, saved-layout and migration recovery, post-publication and permission/expiry rules. No new picture requested.

- guide/use/change-records-with-the-assistant: words-only proposal/Accept, absence of draft, entry points, limits, sending and publication checked and kept; record-model changes linked to their separate ending. Existing words-only screenshot remains appropriate.

- guide/model/change-a-model-with-the-assistant: model-only ending verified in agent._ACCEPTED and _migration_result (empty mappings); preserved whole/partial moves, permissions, disclosure and recovery. Existing dialog and move pictures are outside the changed workbook-load surface.

- guide/model/load-a-workbook-into-a-change-set: kept manual profile/model activation, partial refusals, review, draft deletion and wbload pictures; added explicit manual scope. Need verify manual implementation before final checks.

- integrate/assistant-tasks: kept task permissions, retention, optimistic versions, question answers, origin, move result handling, saved-layout activation and refusal catalogue. Changed loading state, proposal/check shape, accept, repeated-file and correction sequence. No pictures on page.

- use/loading-with-the-assistant: retained access/disclosure, file/instruction constraints, queue/timeout, words-only model state, questions, saved-layout activation and reuse rules, whole/partial/model-only endings and task lifecycle. Changed only workbook item path and scoped retained-failure caveat. use-assistant-proposal.png needs recapture.

- model/ai-model-changes: kept availability, permissions, costs, retention, draft ownership, whole/partial move semantics and lifecycle. Clarified workbook items and model-only migration. No pictures.

- journeys/work-with-an-assistant: kept mapping suggestions, Search/Ask, history explanation, MCP setup/reads/writes and limits, availability, disclosure and disable behavior; corrected only built-in workbook and model-only flow plus profile reuse scope. use-assistant-proposal.png needs recapture.

## Final review findings

Manual route verified in frontend/src/features/model-editor/LoadDialog.tsx: install saves profile, activate before independent profile import; stages and buttons match retained page.

Product discrepancies (left untouched, outside assigned files):
- frontend/src/features/ai-tasks/aiTaskJourney.ts:166 still uses Accept the model for all model-draft proposals, including items, while ModelProposal.tsx uses Accept and load for the main proposal. The task bar does not match the new button.
- frontend/src/features/ai-tasks/LoadedView.tsx: result.releaseId displays "installed and activated" without checking task kind. items_load.py returns releaseId for a changed model but never activates it. This is a misleading claim for workbook batches.
- LoadedView.tsx correction hint and confirmation promise the same assistant "loads again"; design_job.py _queue_words instead returns itemsLoad corrections to stage model for a fresh proposal/acceptance.
- docs/API.md:7263 onward says the engine saves a profile whichever session route was taken; the items_load.py result contains no profile. API AB operation paragraph already says accepting loads items without a turn.

Pictures inspected and outdated (keep existing references, no new pictures or image edits):
- use-assistant-loaded.png in guide/use/load-a-workbook-with-the-assistant.md: saved-profile claim and Open the profile. Replacement needs loaded counts/change-set review and correction actions without profile claim.
- model-assistant-workbook-proposal.png in guide/model/review-an-assistants-workbook-design.md: old row-check card and Accept the model. Replacement needs What the load does, expanded type examples/source cells, findings/file parts and Accept and load, alongside model changes.
- model-assistant-workbook-loaded.png in guide/model/review-an-assistants-workbook-design.md: saved-profile claim and Open the profile. Replacement needs loaded counts/change-set review and correction actions without profile claim.
- use-assistant-proposal.png in use/loading-with-the-assistant.md and journeys/work-with-an-assistant.md: Accept the model; old assistant notes/questions about loading. Replacement needs current workbook proposal, What the load does and Accept and load.

No live assistant task or browser flow was run. Evidence is code and docs inspection plus the documentation build and link/static checks. Original application acceptance-file runs were not executed by this documentation wave.

- Additional picture inspected: use-assistant-reload.png in guide/use/continue-an-assistant-task.md. Its background shows the removed saved-profile claim, and its confirmation says the assistant then loads again. Recapture after the UI text is corrected; retain the warning about removal of manual edits and the confirmation actions.

## Final validation

- GUIDE_OUT=_build/AB-GUIDE npm run build: passed, 253 pages, 3.99 s (final content).
- npm run check: passed terms and brand, 253 pages.
- GUIDE_OUT=_build/AB-GUIDE npm run check:links: passed, 73,495 links and sources across 253 built pages.
- No coverage audit run: its command writes outside the assigned files.
- No code, images or other content pages edited; no commit or state-changing git command used. Build output is the explicitly requested isolated output. Notes and bounded check logs are under this wave's notes directory.
