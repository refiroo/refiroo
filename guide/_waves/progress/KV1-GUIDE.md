## 2026-11-16T01:31:45+01:00 — Consumer API task guide

Finished `guide/src/content/docs/guide/model/define-a-consumer-api.md`: explains raising for a planned change, keeping for an agreed correction, and the dialog-only choice with its permission and earlier-version limits. Checked the shared dialog code and contract refusal logic; no steering file exists and no uncertainty remains for this unit.

## 2026-11-16T01:32:27+01:00 — Installation and workspace application

Finished `guide/src/content/docs/guide/model/install-and-activate-a-release.md`: added shared raise-or-keep steps, all four supplied screenshots and captions, permission and webhook limits, migration handoff and recorded results. Preserved older pictures and updated the refusal caption and result table; no steering file exists and no uncertainty remains for this unit.

## 2026-11-16T01:33:00+01:00 — Consumer API concepts

Finished `guide/src/content/docs/model/consumer-apis.md`: explains the effects on consumers and webhooks, absence of a deprecation notice or preserved old shape, recording and assistant behavior, and the frozen earlier-version boundary. Added the requested single integrator sentence linking the API reference; no steering file exists. Source checks found no uncertainty affecting the text.

## 2026-11-16T01:34:22+01:00 — Final review and checks

Reviewed the three page diffs and the four supplied screenshots; all four are referenced with state-specific captions, and the older dialog pictures remain. No additional screenshots are needed. No steering file exists; no corrections were pending.

Passed `GUIDE_OUT=_build/KV1-GUIDE npm run build` in `guide/` (259 pages, 9.70 seconds), `npm run check` (terms, brand and sidebar), `GUIDE_OUT=_build/KV1-GUIDE npm run check:links` (77,235 local links and sources), and read-only `git diff --check` for the three assigned pages. Logs are under `guide/_coverage/notes/KV1-GUIDE/`. The successful build emitted a non-fatal `/404` route-conflict warning; no configuration was changed. A small final wording edit initially used a path relative to the repository while running from `guide/`; it wrote nothing, was corrected, and the final build covers the corrected page.

No uncertain product behavior or application defect was identified from the inspected paths; this was documentation work, with no live activation or application tests. Only assigned pages, this progress file, working logs and the explicitly requested isolated build output were written. No commits or state-changing git commands were run.

Screenshots used: `model-install-contracts-break` (undecided break and disabled install), `model-install-contracts-kept` (red warning and enabled install), `model-apply-contracts-break` (undecided break and disabled Apply), `model-apply-contracts-kept` (red warning and enabled Apply). Each shows the version-choice buttons described beside it.
