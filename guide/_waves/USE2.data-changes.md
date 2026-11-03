# USE2 wave: data changes on the reference instance

Made through the user interface as the reference administrator, workspace Graubünden, 2026-11-02.

1. **Model draft created and deleted.** 'New from a workbook' with `guide/samples/Haltestellen_Busbetrieb_Nord.xlsx` (draft name `Haltestellen Busbetrieb Nord`, id `23ef12bf-85a8-4a2a-993c-a5c8b93572d0`, proposal 'A new application', compared with the default workspace). The engine applied 16 proposals (one step each) and ran a dry run (94 rows, nothing written). Nothing was installed, activated or loaded. The draft was deleted through 'Delete draft' (use-wb-delete-draft), which also deletes the uploaded workbook. The model list is back to its earlier state (draft count of guide-reference-swiss 1, one draft without an installed model).
   - Remains: a finished job of kind 'Dry run' (`70330b1d-dbd0-47af-8534-88de7df81548`, 411 applied, 9 rejected, nothing written) and the 'Inference' jobs of the proposal, both in Settings, Jobs (kept for a few days, then removed by the service); the 'Changed/Deleted model draft' entries in the person's change history.
2. **Change set created and published.** Change set `Correct Thusis Süd abbreviation` (id `ae6d8306-7f41-4404-b269-bcd50efc13f1`, Network, model guide-reference-swiss 1.0.0) from current live data, in which the stop **Thusis Süd** (UIC 8516936) had its Abbreviation changed from `THSS` to `THSD`. Validated twice, then published: **Publication 1** of Graubünden (id `829b8a3f-f9f0-470c-adf2-04781ca198be`, 2026-11-02 9:37 PM). Live data now holds `THSD` (the one record change; nothing else was in this change set). Not reverted: the stop keeps `THSD`, and its history shows the change. 'December 2026 timetable change' was not touched or published.
3. **Notice read.** Opening the first 'Batch finished' notice (use-notification-job) marked it read: 8 of 9 unread.
4. **Sessions.** Every capture signs in, so the account's 'Where you're signed in' list grew by about 140 browsers during the wave (use-account-sessions shows 'N browsers').

Not changed: no model release installed or activated, no approval policy or other security setting, no workspace, no role. Every other dialog was cancelled.

Side effects on other waves: with two change sets now, the first 'Open change set' button of the Change sets page may no longer be 'December 2026 timetable change' (PILOT change-set-open, change-set-review, change-set-publish-confirm use that first button). While 'Correct Thusis Süd abbreviation' is gone (published), only December remains, so they work again.
