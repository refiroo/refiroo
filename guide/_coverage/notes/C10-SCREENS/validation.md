# Validation — 2026-11-03T10:53:37+01:00

- Passed structural validation: 24 unique capture recipes, 21 missing page images and 3 setup entries; every action is supported by `tools/screens.mjs`, every upload path exists and every navigation path is local.
- All 28 currently missing page-image names accounted for: 21 recipes and 7 explicit exclusions. No existing image is scheduled for recapture.
- Workbook variant ZIP integrity and all XML parts parse successfully.
- `node guide/tools/screens.mjs --file C10.screens.json --list` passed without signing in (before the final added consumer-documents recipe, which passed the same structural validation).
- `GUIDE_OUT=_build/C10-SCREENS npm run build` in `guide/` passed: 200 pages, 2.15 seconds, exit 0. It warned that the docs 404 content entry was not found. No unrelated guide source was changed for that warning.
- No browser capture, image inspection, reference-instance mutation, application test suite or git command ran. Build success does not establish live locator success or image correspondence.
- Source review corrected the placeholder-only Go to expectation to wait for its input, added the selected-record count, and expanded migration-review framing. No page text was changed.
- Final scan caught one concurrent new page-image reference and incorporated it. This is source verification only. Existing draft/profile, default-model API, mail and job states remain unverified against the instance.

## First capture correction turn — 2026-11-03T11:09:28+01:00

- Read the supplied capture log and inspected all 14 distinct attached images, plus four local files produced by failed expectation/cleanup entries. Two older screenshots were supplementary source evidence only.
- Corrected all 10 failed entries without changing application code or confirming data mutations. Also reduced the oversized successful migration-review viewport for recapture.
- Parsed and structurally checked all 24 unique recipes and supported action names. Setup entries now reopen state; none uploads again.
- Checked changed model-guide image references on disk. The earlier stale-migration image remains an uncaptured request, not claimed as verified.
- `GUIDE_OUT=_build/C10-SCREENS npm run build` passed, exit 0: 209 pages in 3.46 seconds. Warning: `/404` conflicts with a higher-priority `/404` route. Bounded static-build log is `build-turn-2.log` in this notes folder.
- Page edits restricted to four files in model/ and guide/model/. No page in use/, guide/use/, integrate/, run/ or administer/ was edited. Their needed changes are in recapture-report.md.
- No live recapture or reference-instance call ran. This is not proof the revised locators pass; external recapture and image review remain required.

## Second-round preparation validation

- 32 unique recipes (24 preserved, two revised, eight added); supported actions, local routes and existing uploads checked. All 25 missing page-image names accounted for: ten recipes, fifteen explicit exclusions. Final picker review uses partial accessible-name matching where React Aria includes option descriptions.
- `GUIDE_OUT=_build/C10-SCREENS npm run build` passed, exit 0: 220 pages, 3.38 seconds. Log: `build-second-round.log`. Existing warning: `/404` conflicts with a higher-priority `/404` route. This build validates page edits; no application test suite or browser capture ran.
- Existing screenshot/caption evidence reused from the first capture review. Eight new Administer recipes and two revised failed recipes require external capture and image review. Mail settings and empty outbox are the previously observed reference state, not a live read this round.
- Only the permitted recipe/data-change files, five documentation pages, progress and wave notes were edited. No git mutation, instance call, access/security confirmation, deletion, publication or release activation was performed.
- Wave-tool status reports historical run totals of 22,855,727 tokens (22,783,485 input, including 22,284,160 cached; 72,242 output). The new run had zero recorded turns/tokens when checked, so current-turn usage is not available from that report.

## Second external capture review validation

- Reviewed all eight supplied images, corrected two Use guides and the two webhook pages, and removed fifteen deferred references from fifteen pages. The new C10-LATER.md is explicitly authorised by this turn's user instructions.
- Scanned 296 page-image references; no deferred names remain. Only admin-webhook-new.png and admin-mail-messages.png await external capture. All 32 recipes parse and use supported actions.
- `GUIDE_OUT=_build/C10-SCREENS npm run build` passed, exit 0: 224 pages in 3.21 seconds. Existing /404 route-conflict warning remains; log: build-second-capture-review.log.
- No browser capture or instance write ran here. Two revised read-only recipes still need their external execution/image review; webhook off-state is inferred from source/configuration and the missing button.
