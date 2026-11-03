# C13-AI-ADMIN progress

## 2026-11-03T22:57+01:00

Finished `src/content/docs/administer/ai.md`: separates the assistant and provider, explains data sent, permissions, human review, costs and retention. Applied steering dated 2026-11-03: the reference instance now has both features on; requested enabled-provider screenshots instead of assuming they cannot be captured. Code disagrees with the Values limit shown in the UI; documented the actual policy and will report the discrepancy. Cross-links will be checked after the remaining units.

## 2026-11-03T22:58+01:00

Finished `src/content/docs/administer/agent-access.md`: person sign-in, agent clients, readable data, preparation limits, human approval, registration, revocation and call records. Rechecked and applied the 2026-11-03 steering: screenshots for enabled states remain requested for later capture. Protocol paths and credential details are linked to Integrate, keeping administrator instructions on the screens.

## 2026-11-03T22:59+01:00

Finished `src/content/docs/guide/administer/check-the-ai-provider.md`: explains the read-only settings, feature availability, data-free test, success and failure, recovery and cost interpretation. No live provider call was made by this writing wave. Rechecked the 2026-11-03 steering; enabled-provider screenshots are requested for later capture.

## 2026-11-03T22:59+01:00

Finished `src/content/docs/guide/administer/manage-agent-access.md`: covers person connections, one-session sign-out, agent-client creation and grants, registration, blocking and restoration, and investigating calls. Credentials are only described at the one-time handover dialog; protocol formats remain in Integrate. Rechecked the 2026-11-03 steering; enabled-provider screenshots are requested for later capture.

## 2026-11-03T23:00+01:00

Finished `src/content/docs/administer/roles-and-grants.md`: added AI and agent cross-links and the access or approval rule at the point administrators need it. Applied current steering; no reference instance configuration was changed.

## 2026-11-03T23:00+01:00

Finished `src/content/docs/administer/approval-policies.md`: added AI and agent cross-links and the access or approval rule at the point administrators need it. Applied current steering; no reference instance configuration was changed.

## 2026-11-03T23:00+01:00

Finished `src/content/docs/administer/clients.md`: added AI and agent cross-links and the access or approval rule at the point administrators need it. Applied current steering; no reference instance configuration was changed.

## 2026-11-03T23:00+01:00

Finished `sidebar/administer.mjs` and `_waves/screens-wanted/C13-AI-ADMIN.md`: both documentation pages and task guides are navigable; nine enabled, test and management screenshots requested. Existing disabled Agent access image was inspected and reused.

## 2026-11-03T23:07+01:00

Finished `_waves/coverage/administer.md`: reconciled all 42 deferred rows, 41 with reader-facing destinations and one test-design row classified not for readers. Counts are 279 covered, 10 not for readers, zero deferred or open; the 2026-11-03 steering remains applied. Source ledger and scoped build verification are being completed.

## 2026-11-03T23:08+01:00

Finished final content review of `administer/ai.md`, `administer/agent-access.md` and `guide/administer/manage-agent-access.md`: added supported provider names, explicit workbook-check review and registration limits. The first scoped verify built 246 pages and passed terms/brand; links failed only on 33 not-yet-captured screenshots (nine for this wave). Steering remains applied; no missing page or anchor was reported.

## 2026-11-03T23:09+01:00

Finished final validation and report notes. `GUIDE_OUT=_build/C13-AI-ADMIN npm run verify` built 247 pages successfully and passed terms/brand; link checking reported 36 missing-image references across concurrently written waves, nine belonging to this wave, with no missing page or anchor. Coverage independently counted: 279 covered, 10 not for readers, 289 total, zero deferred/open. Required screenshot placeholders remain because capture happens later; no screenshots fabricated, no live AI calls or access changes made. Build warnings are the existing caddyfile highlighter fallback and duplicate 404 route. Final limitation: screenshots and browser behavior were not newly exercised; the existing disabled Agent access image was visually inspected. The Values send-level UI wording disagrees with the actual uncapped policy, recorded in working findings. No commit or state-changing git command was run.
