# Second external capture review

Reviewed all eight attached images directly. The supplied log reports eight successful entries and two failures. No live instance call was made in this review.

| Image | Visible state and page correspondence |
| --- | --- |
| replace-related-records | Served by mode for Chur Wiesental; search Tr; Train ticked, Metro/Tram unticked; 1 selected; Save disabled. Caption corrected to the unchanged selection. |
| hierarchy-restructure-plan | Insert a level above Road; Mode; one move, one record created; Some answers are needed; By record (2), By type (0); required Mode code empty; Apply disabled. Caption and steps corrected: Records in the plan is an accessible region name, not a visible tab; no values-without-a-place example is shown. |
| admin-api-reference | Sources contains Management API v1 (engine 0.12.0) and Stops API v1, both with document links. Existing page/caption match. |
| admin-consumer-apis | Reference model 1.0.0, Stops API v1, address copy controls, ten operations, Change feed kept 30 days. Existing page/caption match. Tall image contains spare space but all requested details are legible. |
| admin-about | About introduction, Engine version 0.12.0, schema 0.10, active reference model 1.0.0 and Open release. Existing caption matches. |
| admin-grant-consumer-api | Existing Stops reader client, Consumer APIs grid; Stops API already granted in Graubünden, unchecked in Guide workbook test; incompatible cells marked not in this model; no new selection, Grant disabled. Caption matches the grid; the permission sentence is conditional on a new choice. |
| admin-grant-narrowed | Data steward, only Graubünden, only Stop; Reading is never narrowed and permission sentence visible; Grant enabled but not submitted. Caption and instructions match. |
| admin-mail-settings | Mail is not set up; empty server/login/from fields, port 587 and STARTTLS; application address; disabled Send test message; empty Messages. Both existing corrected mail captions match. |

## Failure evidence

- admin-webhook-new failed before opening any dialog: New webhook button was not found. Source renders it only when consumerSubscriptions.manageSubscriptions is true. Reference configuration has no explicit enabled flag; the engine default is false. Revised recipe captures Webhooks are off in this deployment and Open Deployment rather than inventing a creation dialog. This is a source/configuration inference awaiting the next external image.
- admin-mail-messages failed locating/selecting State with an exact wrapping-label locator. The label encloses the select and all option text. Revised recipe targets the filter select directly and uses keyboard selection of the first non-All option (Waiting), independent of the count. It still expects the actual empty state seen on Mail; no messages are created.

## Final handoff

Retake only `admin-webhook-new,admin-mail-messages`. Both recipes now read existing states; no setup, creation, mail send or security change is requested. The off-state webhook image remains an inference until captured.

Removed all fifteen deferred references from fifteen pages, including run-jobs.png; `_waves/screens-wanted/C10-LATER.md` is their complete future fixture list. This supersedes the previous second-round-report.md inventory: the 15 omitted names are no longer referenced by any page.

Validation: scanned 296 page-image references across Markdown/MDX; none points to a deferred name. Only the two pending retakes are missing. All 32 recipes parse and use supported actions. `GUIDE_OUT=_build/C10-SCREENS npm run build` passed, 224 pages in 3.21 seconds, with the existing /404 route-conflict warning. No live capture or instance mutation ran during review; no product defect was confirmed from the two locator failures.

Wave-tool status currently records 2,892,979 tokens for the previous turn of the newer run (2,880,533 input, 12,446 output); it does not yet include this in-progress review turn. The older four-turn run remains 22,855,727 tokens.
