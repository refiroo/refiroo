
## 2026-11-09T16:55:29+01:00 — workbook load

Finished `guide/src/content/docs/guide/use/load-a-workbook-with-the-assistant.md`: direct example download, exact acceptance label, parent-link counts and combined migration/publication. Checked the item-load path, count summary and migration controls in code. No steer file existed; no uncertainty in these changes.

## 2026-11-09T16:55:49+01:00 — workbook design review

Finished `guide/src/content/docs/guide/model/review-an-assistants-workbook-design.md`: aligned acceptance and publication with the screen, explained parent-link totals and the model-summary distinction for drafts and words-only proposals. No steer file existed; no uncertainty in these changes.

## 2026-11-09T16:56:07+01:00 — recurring workbook

Finished `guide/src/content/docs/guide/use/load-the-next-version-of-a-workbook.md`: removed the claim that a checked-items assistant load saves a profile, while keeping the separately saved-layout route. Verified `items_load.run` returns counts/change-set/release without saving a profile; older session-driven load code has a separate profile-saving path, which is not this checked-items workflow. No steer file existed. The reader’s existing broken profile is setup data, not evidence of another product defect.

## 2026-11-09T16:56:39+01:00 — records from words

Finished `guide/src/content/docs/guide/use/change-records-with-the-assistant.md`: explained the neutral name before a proposal and the record/model names after it, plus view/layout changes despite an empty structural summary. Aligned the workbook acceptance label. Verified `wordsTaskName`, `ModelProposal` and `DesignModel`. No steer file existed; no uncertainty in these edits.

## 2026-11-09T16:57:03+01:00 — model changes and partial moves

Finished `guide/src/content/docs/guide/model/change-a-model-with-the-assistant.md`: explained proposal review before acceptance, the prepared releases/move set, preservation in the removal note, task names, view/layout summaries and the journey-bar acceptance shortcut. Checked the assistant’s partial-move instructions, removal statements, final-release discovery and focus target. No steer file existed. Preparation is checked in code and was completed in the reader’s latest run; no new live task was started.

## 2026-11-09T16:57:28+01:00 — continuation and correction

Finished `guide/src/content/docs/guide/use/continue-an-assistant-task.md`: exact acceptance labels, early-Stop restart with the person’s words, and use of the displayed correlation ID. Existing Stop/failure and revised-proposal review steps already match the fixed behavior. Verified stop handling, transcript detection, empty-set cleanup and failure synchronization in code. No steer file existed; no live recovery test repeated.

## 2026-11-09T16:57:42+01:00 — external assistant sign-in

Finished `guide/src/content/docs/guide/integrate/connect-an-assistant.md`: stated that the assistant must listen on its registered return address during sign-in, including a local listener for loopback. The OAuth handler redirects to that address; the reader’s latest listener-backed run completed. Finding 12 was incomplete setup, not an established product defect. No steer file existed.

## 2026-11-09T16:58:08+01:00 — linked-page consistency

Finished label alignment in `guide/src/content/docs/use/loading-with-the-assistant.md`, `model/ai-model-changes.md`, `journeys/work-with-an-assistant.md`, `integrate/assistant-tasks.md` and `guide/model/load-a-workbook-into-a-change-set.md` (all under the same docs root). Removed the separate-activation requirement from the capability and journey pages, and explained partial-move preparation on the model capability page. No steer file existed; no unrelated behavior changed.

## 2026-11-09T17:00:16+01:00 — final report and validation

Finished `guide/_coverage/notes/C11-FIX3/report.md`: all 15 findings, each named product/guide correction, source evidence, twelve edited pages and six outdated screenshot files. Visually checked eight existing pictures. Isolated build passed (253 pages, 3.81 s; existing duplicate `/404` warning) and isolated link check passed (73,550 local links/sources). No steer file existed; runtime behavior was source-checked against the latest reader report, not retested with live AI tasks.
