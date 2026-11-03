# C1b delivery record

Changed only the three assigned inventories and this notes folder. No guide page, screenshot, application code or test was edited. No commit or state-changing git command was run.

## Release reconciliation

Added columns count new primary promises / rule entries before semantic rule merges. Other columns count dispositions of the original release leads. Alpha records are included in their release. Each `*-resolution.json` names every lead, target, source and reason.

| Release | Added promises / rules | Merged | Superseded | Dropped |
| --- | --- | --- | --- | --- |
| 0.3 | 0 / 0 | 0 | 0 | 0 |
| 0.5 | 0 / 0 | 20 | 1 | 3 |
| 0.6 | 0 / 0 | 14 | 1 | 3 |
| 0.7 | 8 / 2 | 13 | 1 | 4 |
| 0.8 | 10 / 4 | 45 | 2 | 9 |
| 0.9 | 20 / 8 | 162 | 5 | 32 |
| 0.10 | 14 / 4 | 156 | 5 | 17 |
| 0.11 | 17 / 5 | 138 | 1 | 29 |
| 0.12 | 28 / 11 | 315 | 11 | 26 |
| 0.16 ordinary features | 13 / 3 | 40 | 1 | 0 |
| 0.13–0.15 / 0.17 status | 0 / 0 | 1 | 0 | 8 |
| Total | 110 / 37 | 904 | 28 | 131 |

The status-only plans add no release: the one merged 0.17 lead refers to workspace-model work delivered in 0.16. The other eight leads are unbuilt. Another 183 AI/agent release leads remain unchanged. Together 904 + 28 + 131 + 183 accounts for all 1,246 original leads.

Saved C1 notes, packets and record extracts were reused, with release-sized changelog and delivered-decision review and targeted amendment checks. This is not a claim to have reread every line of every historical plan or to have audited all current code. The final direct code checks confirmed password bounds, refresh-token recovery and the change-set rename API. Earlier code citations remain inherited evidence.

## Final inventory

- PROMISES: 1,095 primary records: 971 ordinary and 124 deferred AI/agent records. Added R055–R164; removed the unbuilt reusable-model-module story from current promises while retaining its excluded coverage/source identity.
- BEHAVIOUR-RULES: 149 distinct rules. Added 37, then merged eight aliases into existing rules; the alias trail remains in the document.
- COVERAGE: 3,106 rows after 904 release-lead merges and 57 additional semantic merges. Stable IDs were retained. Every removed semantic ID is recorded in `semantic-merges.json`; release merges are in `ledger-release-merges.json`.

| Section | Covered | Partly | Uncovered | After 0.16 | Not for readers |
| --- | --- | --- | --- | --- | --- |
| About | 0 | 0 | 43 | 1 | 1 |
| Use | 304 | 104 | 298 | 139 | 72 |
| Model | 174 | 119 | 481 | 27 | 18 |
| Administer | 123 | 65 | 61 | 31 | 9 |
| Run | 125 | 23 | 13 | 58 | 35 |
| Integrate | 0 | 1 | 645 | 43 | 30 |
| Examples | 4 | 1 | 1 | 0 | 0 |
| Journeys | 18 | 0 | 29 | 9 | 1 |
| Total | 748 | 313 | 1,571 | 308 | 166 |

The existing 82 non-AI page homes referenced by generic partly judgments were read in full. Ordinary partly rows name an actual remaining clause, task or screen wording; uncovered rows point to settled outline homes. AI rows retain their original judgments under the explicit deferral. Counts use the least complete reader judgment. No prose pages or screenshots are part of this assignment.

## Checks and limitations

`python3 guide/_coverage/notes/C1b-RELEASES/validate_inventory.py` passed: table widths, stable unique IDs, release arithmetic, existing page targets, planned outline homes and unchanged after-0.16 rows. `final-counts.json` contains the machine-readable results.

In `guide/`, `GUIDE_OUT=_coverage/notes/C1b-RELEASES/build npm run verify` ran:

- `npm run build`: passed, 86 pages, 2.03 seconds. Astro warned that its 404 content entry is absent.
- Terminology and brand: passed, 85 source pages.
- Links: failed, eight existing targets missing in pages outside this wave’s editable files:
  - `run/background-jobs`: `/docs/use/jobs/` and `/docs/screens/run-jobs.png`.
  - `run/backup-and-restore`: `/docs/screens/run-backup-rehearsal.png`.
  - `run/configure`: `/docs/screens/run-deployment.png`.
  - `run/monitoring`: `/docs/screens/run-operations.png`.
  - `run/sign-in-and-mail-setup`: `/docs/guide/administer/set-up-mail/`.
  - `run/webhook-delivery`: `/docs/guide/administer/create-a-webhook/` and `/docs/integrate/consumer-events-and-webhooks/`.

Generated build/cache output was removed from this notes folder after recording the result. No server or database was started. No application runtime or browser acceptance claim is made.

## Findings

No new runtime defect was verified. Inventory defects corrected include collapsed cross-release D-number provenance, unconditional refresh-reuse wording, blanket “blank cells clear nothing”, the obsolete host allowlist/suspension wording, the old schema window, own-model impact scope and nine-versus-ten predefined-role wording. One journey said rename/discard without distinguishing clients: the API supports rename; the normal browser change-set controls offer discard and no general rename action. That distinction is now explicit. The eight missing documentation targets above remain outside this wave’s authority.
