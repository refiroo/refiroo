## Assistant tasks, durations and usage

Task notes show whole seconds and cumulative cost across turns. Calls shows a duration and cost per call. These are different measurements; the figures below preserve both rather than adding cumulative notes as separate charges. Token figures are the screens' reported input/output counts, not independently verified billing. `—` means not reported, never assumed free. All times are 2026-11-09 CET.

| Task ID | Path and final state | Task-note durations/costs | Calls tokens in / out; cost; duration |
| --- | --- | --- | --- |
| `4dbadbb9-08ee-4c9d-a1d0-b7b40d8d6d48` | Original workbook, published in reader-ai | 147 s, $0.55 | 1,144,568 / 17,628; $0.55; 151,239 ms |
| `6dc50190-2954-4c4e-a137-45b9b759d9c3` | Original words task, stopped, continued, loaded; correction failed; discarded | Continuation 9 s, $0.08; load 12 s, cumulative $0.12 | Initial failure: 26,019 / 56; —; 6,089 ms. Continuation: 45,131 / 1,017; $0.08; 12,308 ms. Acceptance/load: 95,385 / 1,240; $0.04; 14,212 ms. Failed correction has no identifiable separate Calls row. |
| `bbcd67f9-1af9-46db-af8b-ec945a17c6f1` | Extra table view, model migrated to 1.4.2 | Proposal 24 s, $0.10 | Proposal: 130,432 / 2,504; $0.10; 26,397 ms. Acceptance: 139,537 / 1,456; $0.04; 18,213 ms. |
| `a3e9769e-988f-4623-bb98-5565d8d5f9bb` | Whole-type move Line → Route, migrated to 1.5.0 | Proposal 67 s, $0.26 | Proposal: 458,267 / 8,270; $0.26; 68,902 ms. Acceptance: 205,207 / 1,340; $0.05; 16,264 ms. |
| `fffee11a-95a3-4bcd-a2b2-2aeb3fe73a96` | Original partial move, both attempts failed, discarded | First job 121 s; retry about 1 s from Created/Finished timestamps | No matching Calls entry at those job times; tokens/cost unreported. Jobs `c3017381-68d8-4ba9-bcf5-f2b2fa74255a` (11:29:25–11:31:26) and `72ac65f6-7581-475a-937c-c9907320e04b` (11:33:42–11:33:43), both 0/0 processed and failed. |
| `7f000a69-7475-4905-9744-0f7242bdb5bb` | Resumed Stop/continue, intentional Stop correct, continuation failed, discarded | Failed continuation note only `(0 s)` | Stop: — tokens; — cost; 2,989 ms, Cancelled by a person. Continuation: — tokens; $0.00; 4,194 ms, The session ended without an answer. |
| `d47b220a-c8fd-4209-9ccc-6bcce560f223` | New workbook load and correction, replacement reviewed, discarded | Proposal 48 s, $0.22; correction 13 s, cumulative $0.26 | Proposal: 377,704 / 4,545; $0.22; 51,295 ms. Correction: 168,510 / 1,076; $0.04; 16,371 ms. Engine acceptance needs no extra AI call. |
| `280d6684-0d73-470f-9c94-1a483d5977c1` | New partial move plus one correction, no staged move, discarded | Proposal 38 s, $0.16; correction 50 s, cumulative $0.31 | Proposal: 232,469 / 3,895; $0.16; 40,354 ms. Correction: 391,800 / 5,647; $0.15; 52,450 ms. |

The older proposal/acceptance Calls rows are associated by time and recorded task sequence; Calls does not expose a task ID in its visible columns. No row is invented for failed work which did not log a call. `task-<id>.txt` captures current task screens; published/installed task screens no longer show all earlier notes, so the original screenshots and written notes remain the evidence for those earlier durations.

### Other AI calls

| Time | Action | Outcome | Input / output tokens | Reported cost | Duration |
| --- | --- | --- | --- | --- | --- |
| 11:08 | Provider test | Answered | 898 / 52 | — | 4,354 ms |
| 11:35 | Ask a list in words | Answered | 3,781 / 171 | — | 5,216 ms |
| 11:36 | Explain a period | Answered | 4,116 / 720 | — | 5,962 ms |
| 11:40 | Mapping, no likely target | Answered | 3,740 / 120 | — | 3,305 ms |
| 15:25 | Provider recheck | Answered | 898 / 52 | — | 5,280 ms |
| 15:35 | Mapping, replace variant | Answered | 3,783 / 125 | — | 4,510 ms |
| 15:39 | Mapping, keep/publish origin variant | Answered | 3,778 / 118 | — | 3,843 ms |

The empty history period made no call. MCP requests use no refiroo AI provider; this reader used its terminal as the outside assistant, so there is no additional external-model bill for those calls. Known per-call costs of this wave total **$1.69**; this excludes every `—` cost and is not a total provider bill. Final instance-wide 30-day screen: **66 calls, 10 failed; 60,138,833 input / 355,339 output tokens; $13.35**. It includes other work and is not this wave's usage. In particular the 14:04–14:07 ALXP-TRY6/8/10 tasks were already present and were not started by this resumed reader; their calls are not attributed to this wave. Evidence: `ai-calls-before-retest.txt`, `ai-calls-final.txt`, `51-ai-calls-final.png`, `original-partial-jobs.txt`.

## Created objects and retained changes

All application writes were in **reader-ai**. No publication, model activation, install or deletion was performed in graubuenden. No installation AI setting was changed.

- Workspace **reader-ai**, initially empty on the default model; now runs `guide-reference-swiss` **1.5.0**. It retains the original workbook's **213 records**, the Line → Route move of **four** existing records, the **Stops review** table and **two** extra System codes created in the continuation (215 records expected from those recorded writes; no final whole-workspace recount claimed).
- Original workbook draft **Busbetrieb Nord stops workbook (reader-ai)**, `e3a30976-336d-427d-a26d-23d361a16ab4`; installed release **1.4.1**, loaded set `e745fd00-f71d-4892-baf0-da1beb8252fb`, migration `82ac4083-000b-4078-be87-ff34c9935f0c`, published **Publication 1** `da6ae356-32c7-42f0-b645-307003ca6dc3`.
- Model-only task installed **1.4.2**, migration `a7d52081-754b-4555-b4fd-19986f00e00e`; whole-type task installed **1.5.0**, migration `cb7c4338-6788-44a5-bb2f-b7073f054f3a`. Their draft/release labels and task IDs locate that work; draft IDs were not recorded by the earlier run. The original and new partial-move proposals were discarded; no partial-move release was accepted.
- Original words change set **Set abbreviation of Chur, Alexanderplatz**, `dcd34a72-63aa-4c80-bdbb-08957d28f993`, and an empty replacement from its failed correction. The earlier notes did not record the empty replacement's ID. The resumed home screen already showed these abbreviation sets discarded before this reader resumed; no open set was retained by the new correction.
- New workbook task's first load `f6fa2582-02f0-4068-bdcb-99d715235b2e` discarded by correction; replacement `e857de70-edb8-4f48-a905-506ef57baaa6` explicitly discarded after review, ending task `d47b220a-c8fd-4209-9ccc-6bcce560f223`. The assistant's temporary draft was discarded with its task; its ID was not displayed in the saved screen. No corrected abbreviation was published.
- Original mapping exercise temporarily unmapped BN-103 and restored it manually; empty proposal set **reader-ai mapping proposals**, `e069ad2d-0931-47e8-9a4e-94ef20cca9af`, discarded. Job `5a6028bd-bb27-4e8b-ac23-bafd7c254341` retained as evidence.
- New System code **Chur, Alexanderplatz**, external code **READER-AI-8595591**, ID `b6528e7d-3a12-4dbe-a9f9-bd94022874e4`, under busbetrieb-nord. Final mapping to Chur, Alexanderplatz was manually reviewed/replaced, then published in **reader-ai likely mapping review**, set `daf3d4b0-a72a-4f61-a13e-83219f920c19`, **Publication 3** `122c6a11-455f-4658-8ad3-5a6cf5049db0`. Job `4b514fba-970a-4f12-8e3a-411afe695bce`.
- New System code **Chur Albula**, external code **READER-AI-8571924**, ID `b00327c7-76a7-4182-9882-ebdb630f02eb`, under busbetrieb-nord. Unchanged AI proposal published in **reader-ai keep AI mapping origin**, set `f9bc67a5-f60a-4a3d-9715-52c57a1ecb6c`, **Publication 4** `6a3a273a-ccbf-47a0-8c05-fa99d464d7ab` (current). Job `291a980c-d889-47b5-a57d-bdfc66034a13`.
- System agent client **reader-ai outside assistant**, `76cd8526-7447-4fd4-8732-576fcae1ca1a`, Agent role in reader-ai only, **deactivated**. Its next request was checked and returned 401 TOKEN_INVALID / The client is not active. Set **reader-ai external assistant review**, `eeb9021f-4521-4017-8975-1a005a5a0f5f`, submitted `46556b56-157d-4f1b-90c7-1fa252c2daa1`, sent back, corrected/resubmitted `5e822ed4-b31b-4cf3-bb7b-1c9055ad2f56`, then published **Publication 2** `a510759c-6905-473a-b09a-4c350a40fd28`. Live Abbreviation of Chur, Alexanderplatz is **ALXP-MCP-REVISED**.
- Personal registration **reader-ai personal assistant** from the earlier run (ID not in its saved notes) and resumed registration **reader-ai personal assistant resumed**, `7fd5a77f-e447-44d5-b236-4867357b935f`: **both blocked**, zero signed-in people. No usable resumed personal token/session was obtained. Registration records remain for audit as documented; no delete control exists.
- Eight known wave task IDs are listed above, with their retained notes/jobs. New stopped/failed and partial tasks are discarded; no AI job was intentionally left running. Other pre-existing ALXP-TRY tasks and the broken saved import profile were left untouched.
- Downloaded reference workbook **Haltestellen_Busbetrieb_Nord.xlsx** and all browser scripts, visible-text captures and screenshots are under this wave's notes folder. No credentials or tokens were written there. The only generated output elsewhere is the specifically requested isolated build at `guide/_build/C11-READER2-AI/`.
