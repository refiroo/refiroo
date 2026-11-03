# Third-round preparation

Applied third-round steering: the existing Contributor account now supports `contributor-propose-change`; restored its image reference in `guide/use/propose-a-change.md`. The recipe uses the read-only record route and labels checked in `frontend/src/features/workspaces/Proposal.tsx`, `frontend/src/features/objects/ObjectDetail.tsx`, `frontend/src/app/App.tsx`, and the established PILOT record navigation. Cancellation leaves the suggested name unchanged and avoids a discard confirmation.

Only this deferred entry depended solely on a Contributor or approver. The other fourteen entries in `screens-wanted/C10-LATER.md` still need the listed state/provider/job fixtures and remain deferred.

Handoff: remove the `contributor-propose-change.png` row from `screens-wanted/C10-LATER.md` and change its count to fourteen. That file is outside the user's explicit allowed files, so it was left untouched. This note supersedes its Contributor deferral.

External capture: `node guide/tools/screens.mjs --file C10.screens.json --only contributor-propose-change`. Confirm the dialog, explanatory text, Live band and absence of live edit controls in the image. The runner can assert visible text, but cannot assert missing controls with its supported actions; that check requires image review. No image has been captured or visually verified in this preparation turn. If an existing personal change set bypasses the dialog, report the prerequisite; never alter it to force the picture.

## Validation

All 33 retained/appended recipes pass unique-name, action and required-field checks. All referenced images exist except the newly restored `contributor-propose-change.png`, which has its new recipe. `GUIDE_OUT=_build/C10-SCREENS npm run build` passed: 225 pages, 3.84 seconds. Build warnings: unsupported `caddyfile` highlighting in `run/https.md` falls back to text; `/404` route conflict. Those surfaces were not changed. Full build log: `build-third-round.log`. External capture and visual review are still pending; no product defect was established by this preparation.
