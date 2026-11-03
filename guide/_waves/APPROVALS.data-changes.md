# APPROVALS wave: data changes on the reference instance

Made as the reference administrator (API and user interface) and as the approver (user interface), 2026-11-02. Instance http://localhost:8480.

## People, grants, policy

1. **Person `rita.approver` ("Rita Approver")**, id `e63f4689-4c63-4628-a5a5-ec63f4570d68`, local account. Created through `POST /users`; password set through the one-time reset link (`POST /oauth/password`). Credentials appended to `guide/reference/.env` as `GUIDE_APPROVER_USERNAME` and `GUIDE_APPROVER_PASSWORD`.
2. **Grant** `f8fadbb3-cac0-4ea2-8206-fa25b44a80aa`: role Data owner (`owner`, holds Approve publications) for Rita Approver, scope workspace Graubünden only.
3. **Approval policy of Graubünden** (`approval-policy`): the user had switched approval on (version 1: requireApproval on, secondPerson off). Set to **second person on** (version 2) so the submitter's restriction could be captured, then **set back to second person off** (version 3). Approval is still on, as the user left it.

## Change set and publication (Graubünden)

4. **Change set `Guide approval example`**, id `93b863fb-d82b-4faa-b0c7-778377fa448a` (Network, model guide-reference-swiss 1.0.0): the stop **Davos Platz** (UIC 8509073), attribute Height changed from `1540.192` to `1540.2`. Validated, then: submitted (comment "Height of Davos Platz rounded to one decimal, as in the national register."), sent back by Rita Approver (reason "Please name the source of the new height before this is published."), submitted again (comment "Source added: the height is taken from the national survey."), approved by Rita Approver.
5. **Publication 2** of Graubünden, id `4abc5741-fe28-45a7-b4ee-8505c99b7c36`, published by Rita Approver 2026-11-02 10:27 PM (approval of request `61db0999-f1b8-47fb-85cf-8ae03835dfb6`). It replaced Publication 1 as current (Publication 1 now reads Withdrawn). Live data holds Davos Platz height `1540.2`, not reverted. The change set no longer exists (an approved change set is consumed).
6. 'December 2026 timetable change' was not touched.
7. **Notices**: Rita Approver received one "waiting for your approval" notice per submission (read by her review visits); Guide Admin received "Sent back" and "Approved" notices (left unread).

## Test workspace and workbook load

8. **Workspace `Guide workbook test`** (key `guide-workbook-test`), created through `POST /workspaces`, started on the instance's active release guide-reference-swiss 1.0.0. Not default, no approval policy.
9. **Model draft `Haltestellen Busbetrieb Nord`**, id `5ff78a6f-4353-4a3d-8929-47f6bb14b5c7`, from `guide/samples/Haltestellen_Busbetrieb_Nord.xlsx` through 'New from a workbook' (proposal 'A new application', compared with Guide workbook test, base release guide-reference-swiss 1.0.0). Left in place (it holds the stored workbook and saved profile).
10. **Model release guide-reference-swiss 1.0.1** (id `7b9d9306-0e4a-4422-80ac-f7bed01bb9f2`, application 'Haltestellen Busbetrieb Nord' added) installed from the draft and **activated in Guide workbook test only** ('Install, activate and load'). Graubünden still runs 1.0.0. The release exists instance-wide (Settings, Model).
11. **Change set `Load Haltestellen_Busbetrieb_Nord.xlsx (2026-11-02)`**, id `96a3e4df-358c-4461-8c93-1801f0a27842` in Guide workbook test: 258 created, 108 updated, 45 unchanged, 9 refused. Left open, validated not, **not published**; the workspace's live data is empty.
12. **Jobs**: the proposal's inference jobs, a dry run (9 refused) and the load job, in Settings, Jobs (removed by the service after a few days); the person's change history holds the draft entries.
13. **Sessions**: every capture signs in, so the accounts' session lists grew.

## Tool change

`guide/tools/screens.mjs`: a screen may carry `"as": "approver"` and then signs in with `GUIDE_APPROVER_*` instead of the administrator (default unchanged).

## Not changed

Graubünden's model, other workspaces, roles, other people, existing images and other `*.screens.json` files.
